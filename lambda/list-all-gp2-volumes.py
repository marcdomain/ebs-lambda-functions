import os
import csv
import boto3
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def lambda_handler(event, context):
    account_name = 'xxxxxxxxxx'
    devops_email = 'xxxxxxxxxxx'
    support_email = 'xxxxxxxxxxx'

    client = boto3.client('ec2')
    region_details = client.describe_regions()
    report_file = "/tmp/gp2_volumes_report.csv"
    dict_report = {}

    if os.path.exists(report_file):
        os.remove(report_file)

    for region in region_details['Regions']:
        volumeID = []
        volumeSize = []
        GP2Iops = []
        GP3Iops = []
        instanceID = []
        state = []
        region_name = region['RegionName']
        ec2 = boto3.resource('ec2', region_name=region_name)
        dict_report[region_name] = {}

        for volume in ec2.volumes.all():
            if volume.volume_type == 'gp2':
                iops = ''
                if volume.iops > 3000:
                    iops = volume.iops
                else:
                    iops = 3000
                volumeID.append(volume.id)
                volumeSize.append(volume.size)
                GP2Iops.append(volume.iops)
                GP3Iops.append(iops)
                state.append(volume.state)

                if volume.state != 'available':
                    instanceID.append(volume.attachments[0]['InstanceId'])

                else:
                    instanceID.append('N/A')


        if len(volumeID) > 0:
            dict_report[region_name]['Instance ID'] = instanceID
            dict_report[region_name]['Volume ID'] = volumeID
            dict_report[region_name]['State'] = state
            dict_report[region_name]['Size'] = volumeSize
            dict_report[region_name]['GP2 IOPS'] = GP2Iops
            dict_report[region_name]['GP3 IOPS'] = GP3Iops
        else:
            dict_report.pop(region_name, None)

    format_dict_report = []
    for d in dict_report:
        format_dict_report.append('<p><b>'+'REGION: ' +d.upper()+'</b></p>')
        format_dict_report.append('<b>'+'NUMBER OF GP2s: ' +str(len(dict_report[d]['Instance ID']))+'</b></br>')
        format_dict_report.append(
            '<table border=1><tr><th>Instance ID</th><th>Volume ID</th><th>State</th><th>Size</th><th>GP2 IOPS</th><th>GP3 IOPS</th></tr>'
        )
        for i in range(len(dict_report[d]['Volume ID'])):
            format_dict_report.append('<tr>')
            format_dict_report.append('<td>'+str(dict_report[d]['Instance ID'][i])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['Volume ID'][i])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['State'][i])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['Size'][i])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['GP2 IOPS'][i])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['GP3 IOPS'][i])+'</td>')
            format_dict_report.append('</tr>')
        format_dict_report.append('</table>')


    # Generate Report File

    for d in dict_report:
        header = open(report_file, 'a', newline="")
        write_header = csv.writer(header)
        write_header.writerow((''))
        write_header.writerow(('REGION', 'INSTANCE ID', 'VOLUME ID', 'STATE', 'SIZE', 'GP2 IOPS', 'GP3 IOPS'))
        header.close()
        for i in range(len(dict_report[d]['Volume ID'])):
            vol_info = (
                d,
                dict_report[d]['Instance ID'][i],
                dict_report[d]['Volume ID'][i],
                dict_report[d]['State'][i],
                dict_report[d]['Size'][i],
                dict_report[d]['GP2 IOPS'][i],
                dict_report[d]['GP3 IOPS'][i]
            )
            report = open(report_file, 'a', newline="")
            writer = csv.writer(report)
            writer.writerow(vol_info)
            report.close()


    # SEND EMAIL USING SES
    ses_client = boto3.client("ses")
    msg = MIMEMultipart()
    msg["Subject"] = account_name + " GP2 Volumes"
    msg["From"] = devops_email
    recipients = [devops_email, support_email]
    msg["To"] = ', '.join(recipients)

    html = ''
    if len(format_dict_report) > 0:
        html = """\
        <html>
        <head></head>
        <body>
            <p><b>GP2 VOLUMES AND THE EXPECTED GP3 EQUIVALENT IN {account_name} ACCOUNT</b></p>
            {html_report}
        </body>
        </html>
        """.format(account_name = account_name, html_report = '\n'.join(format_dict_report))
    else:
        html = 'GP2 VOLUMES NOT FOUND'


    # Set message body
    body = MIMEText(html, "html")
    msg.attach(body)

    part = MIMEApplication(open(report_file, 'rb').read())
    part.add_header('Content-Disposition', 'attachment', filename = account_name +' GP2_Volumes.csv')
    msg.attach(part)

    # Convert message to string and send
    ses_client.send_raw_email(
        Source = devops_email,
        Destinations=recipients,
        RawMessage={"Data": msg.as_string()}
    )
