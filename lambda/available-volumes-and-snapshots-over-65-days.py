import boto3
import datetime
import csv
import os
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def lambda_handler(event, context):
    account_id = 'xxxxxxxxxxx'
    account_name = 'xxxxxxxx'
    email_address = "xxxxxxx"

    report_file = "/tmp/volumes_and_snapshots_report.csv"
    dict_report = {}

    if os.path.exists(report_file):
        os.remove(report_file)

    client_info = boto3.client('ec2')
    region_details = client_info.describe_regions()

    for region in region_details['Regions']:
        region_name = region['RegionName']
        ec2 = boto3.resource('ec2', region_name = region_name)
        client = boto3.client('ec2', region_name = region_name)
        dict_report[region_name] = {}

        # LIST AVAILABLE VOLUMES
        availableVolumeList = []
        for volume in ec2.volumes.all():
            if volume.state == 'available':
                availableVolumeList.append(volume.id)

        availableVolumes = len(availableVolumeList)

        # LIST SNAPSHOTS OLDER THAN 65 DAYS
        snapshots = client.describe_snapshots(OwnerIds=[account_id])
        snapshotList = []
        for snapshot in snapshots['Snapshots']:
           startTime = snapshot['StartTime']
           startDate = startTime.date()
           currentDate = datetime.datetime.now().date()
           numOfDays = currentDate - startDate

           if numOfDays.days > 65:
               snapshotList.append(snapshot['SnapshotId'])

        numberOfSnapshots = len(snapshotList)

        if numberOfSnapshots > 0 or availableVolumes > 0:
            dict_report[region_name]['volumes'] = availableVolumeList
            dict_report[region_name]['snapshots'] = snapshotList

            # Generate Report File
            header = open(report_file, 'a', newline="")
            write_header = csv.writer(header)
            write_header.writerow(('REGION', 'DESCRIPTION', 'ID'))
            # write_header.writerow((region_name.upper(), 'ID'))
            header.close()

            for vol in availableVolumeList:
                vol_info = ''
                if vol == availableVolumeList[0]:
                    vol_info = (region_name.upper(), 'Available Volume', vol)
                else:
                    vol_info = ('', 'Available Volume', vol)
                report = open(report_file, 'a', newline="")
                writer = csv.writer(report)
                writer.writerow(vol_info)
                report.close()
            for snap in snapshotList:
                snap_info = ''
                if availableVolumes == 0 and snap == snapshotList[0]:
                    snap_info = (region_name.upper(), 'Snapshot over 65 days', snap)
                else:
                    snap_info = ('', 'Snapshot over 65 days', snap)
                report = open(report_file, 'a', newline="")
                writer = csv.writer(report)
                writer.writerow(snap_info)
                report.close()
        else:
            dict_report.pop(region_name, None)

    # print(dict_report)
    format_dict_report = []
    for d in dict_report:
        format_dict_report.append('<p><b>'+'REGION: ' +d.upper()+'</b></p>')
        for item in dict_report[d]:
            format_dict_report.append('<p><span>'+str(len(dict_report[d][item]))+'</span> '+item+'</p>')
            for i in dict_report[d][item]:
                format_dict_report.append(i+'<br>')

    # SEND EMAIL USING SES
    ses_client = boto3.client("ses")
    msg = MIMEMultipart()
    msg["Subject"] = account_name + " Weekly Report: Volumes and Snapshots"
    msg["From"] = email_address
    msg["To"] = email_address

    html = """\
    <html>
      <head></head>
      <body>
        <p><b>SNAPSHOTS THAT HAVE EXISTED OVER 65 DAYS AND AVAILABLE VOLUMES IN {account_name} ACCOUNT</b></p>
        {html_report}
      </body>
    </html>
    """.format(account_name = account_name, html_report = '\n'.join(format_dict_report))


    # Set message body
    body = MIMEText(html, "html")
    msg.attach(body)

    part = MIMEApplication(open(report_file, 'rb').read())
    # part.add_header('Content-Disposition', 'attachment', filename=report_file)
    part.add_header('Content-Disposition', 'attachment', filename = account_name +' volumes_and_snapshots.csv')
    msg.attach(part)

    # Convert message to string and send
    ses_client.send_raw_email(
        Source = email_address,
        Destinations=[email_address],
        RawMessage={"Data": msg.as_string()}
    )
