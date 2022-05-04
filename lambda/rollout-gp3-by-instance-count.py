import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def lambda_handler(event, context):
    region_name = 'xxxxxxxx'
    account_name = 'xxxxxxxxx'
    support_email = 'xxxxxxxxx'
    devops_email = 'xxxxxxxxx'
    instance_count = 5 # replace with an integer

    ec2 = boto3.resource('ec2', region_name=region_name)
    region_client = boto3.client('ec2', region_name=region_name)

    dict_report = {}
    instance_ids = []

    if instance_count > 0:
        for instance in ec2.instances.all():
            instance_ids.append(instance.id)
            if len(instance_ids) >= instance_count:
                break
        if len(instance_ids) == 0:
            return print('EC2 instances not found')

    search_list = ec2.instances.filter(Filters = [{'Name': 'instance-id', 'Values': instance_ids}])

    if len(instance_ids) > 0:
        for item in search_list:
            item_id = item.id
            dict_report[item_id] = {}
            instance_volumes = []
            volume_states = []
            volume_sizes = []
            gp2_volumes = []
            gp3_volumes = []

            for volume in item.volumes.all():
                dict_report[item_id]['Instance ID'] = item_id
                if item.tags:
                    for tag in item.tags:
                        if tag['Key'] == 'Name':
                            dict_report[item_id]['Instance Name'] = tag['Value']
                            break
                        else:
                            dict_report[item_id]['Instance Name'] = 'N/A'
                else:
                    dict_report[item_id]['Instance Name'] = 'N/A'

                if volume.volume_type == 'gp2':
                    iops = ''
                    if volume.iops > 3000:
                        iops = volume.iops
                    else:
                        iops = 3000

                    instance_volumes.append(volume.id)
                    volume_states.append(volume.state)
                    volume_sizes.append(volume.size)
                    gp2_volumes.append(volume.iops)
                    gp3_volumes.append(iops)

                    dict_report[item_id]['Volume ID'] = instance_volumes
                    dict_report[item_id]['State'] = volume_states
                    dict_report[item_id]['Size'] = volume_sizes
                    dict_report[item_id]['GP2 IOPS'] = gp2_volumes
                    dict_report[item_id]['GP3 IOPS'] = gp3_volumes

                    region_client.modify_volume(VolumeId=volume.id,VolumeType='gp3',Iops=iops)
    else:
        print('EC2 instances not found')

    format_dict_report = []

    format_dict_report.append(
        '<table border=1><tr><th>Instance Name</th><th>Instance ID</th><th>Volume ID</th><th>State</th><th>Size</th><th>GP2 IOPS</th><th>GP3 IOPS</th></tr>'
    )
    for d in dict_report:
        if 'Volume ID' in dict_report[d]:
            for k in range(len(dict_report[d]['Volume ID'])):
                if k == 0:
                    format_dict_report.append('<tr>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Instance Name'])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Instance ID'])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Volume ID'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['State'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Size'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['GP2 IOPS'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['GP3 IOPS'][k])+'</td>')
                    format_dict_report.append('</tr>')
                else:
                    format_dict_report.append('<tr>')
                    format_dict_report.append('<td>'+'</td>')
                    format_dict_report.append('<td>'+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Volume ID'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['State'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['Size'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['GP2 IOPS'][k])+'</td>')
                    format_dict_report.append('<td>'+str(dict_report[d]['GP3 IOPS'][k])+'</td>')
                    format_dict_report.append('</tr>')
        else:
            print('Volumes not found for the instances provided')
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
            <p><b>GP2 VOLUMES CONVERTED TO GP3 IN {account_name} ACCOUNT {region_name} </b></p>
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
