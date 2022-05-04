import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def lambda_handler(event, context):
    region_name = 'xxxxxxxx'
    account_name = 'xxxxxxxx'
    support_email = 'xxxxxxxxx'
    devops_email = 'xxxxxxxxx'
    volume_ids = ['vol-xxxxxx', 'vol-xxxxxxx'] # a list of strings of volume ids

    ec2 = boto3.resource('ec2', region_name=region_name)
    region_client = boto3.client('ec2', region_name=region_name)
    search_list = ec2.volumes.filter(
        Filters = [
            {
                'Name': 'volume-id',
                'Values': volume_ids
            }
        ]
    )

    dict_report = {}

    if len(volume_ids) > 0:
        for item in search_list:
            item_id = item.id
            dict_report[item_id] = {}
            dict_report[item_id]['Instance ID'] = item.attachments[0]['InstanceId'] if item.attachments else 'N/A'

            if item.volume_type == 'gp2':
                iops = ''
                if item.iops > 3000:
                    iops = item.iops
                else:
                    iops = 3000
                dict_report[item_id]['Volume ID'] = item.id
                dict_report[item_id]['State'] = item.state
                dict_report[item_id]['Size'] = item.size
                dict_report[item_id]['GP2 IOPS'] = item.iops
                dict_report[item_id]['GP3 IOPS'] = iops

                if item.tags:
                    for tag in item.tags:
                        if tag['Key'] == 'Name':
                            dict_report[item_id]['Volume Name'] = tag['Value']
                            break
                        else:
                            dict_report[item_id]['Volume Name'] = 'N/A'
                else:
                    dict_report[item_id]['Volume Name'] = 'N/A'

                region_client.modify_volume(VolumeId=item.id,VolumeType='gp3',Iops=iops)
    else:
        print('Please provide a list of volume_ids')


    format_dict_report = []

    format_dict_report.append(
        '<table border=1><tr><th>Instance ID</th><th>Volume ID</th><th>Volume Name</th><th>State</th><th>Size</th><th>GP2 IOPS</th><th>GP3 IOPS</th></tr>'
    )
    for d in dict_report:
        if 'Volume ID' in dict_report[d]:
            format_dict_report.append('<tr>')
            format_dict_report.append('<td>'+str(dict_report[d]['Instance ID'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['Volume ID'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['Volume Name'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['State'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['Size'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['GP2 IOPS'])+'</td>')
            format_dict_report.append('<td>'+str(dict_report[d]['GP3 IOPS'])+'</td>')
            format_dict_report.append('</tr>')
        else:
            print('Volumes not found')
    format_dict_report.append('</table>')

    # SEND EMAIL USING SES
    ses_client = boto3.client("ses")
    msg = MIMEMultipart()
    msg["Subject"] = account_name + " GP2 to GP3 Volumes Conversion"
    msg["From"] = devops_email
    recipients = [devops_email, support_email]
    msg["To"] = ', '.join(recipients)

    html = ''
    if len(format_dict_report) > 2:
        html = """\
        <html>
        <head></head>
        <body>
            <p><b>GP2 VOLUMES CONVERTED TO GP3 IN {account_name} ACCOUNT {region_name}</b></p>
            {html_report}
        </body>
        </html>
        """.format(account_name = account_name, region_name = region_name, html_report = '\n'.join(format_dict_report))
    else:
        html = 'GP2 volumes not found {region_name}'.format(region_name = region_name)


    # Set message body
    body = MIMEText(html, "html")
    msg.attach(body)

    # Convert message to string and send
    ses_client.send_raw_email(
        Source = devops_email,
        Destinations=recipients,
        RawMessage={"Data": msg.as_string()}
    )
