import email
import json
import os
from email import policy

import boto3

EMAILS_DYNAMO_TABLE = os.environ['EMAILS_DYNAMO_TABLE']
ATTACHMENTS_BUCKET = os.environ['ATTACHMENTS_BUCKET']
TEXTRACT_NOTIFICATION_TOPIC_ARN = os.environ['TEXTRACT_NOTIFICATION_TOPIC_ARN']
TEXTRACT_NOTIFICATION_ROLE_ARN = os.environ['TEXTRACT_NOTIFICATION_ROLE_ARN']

def lambda_handler(sns_payload, context):
    print(json.dumps(sns_payload))

    if 'Records' not in sns_payload:
        raise Exception('No Records section')

    if len(sns_payload['Records']) != 1:
        raise Exception('Expected only 1 record')

    sns_message = sns_payload['Records'][0]['Sns']['Message']
    event = json.loads(sns_message)

    if 'action' not in event['receipt']:
        raise Exception("Invalid event, expected action section")


    action = event['receipt']['action']

    actionType = action['type']
    if actionType != 'S3':
        raise Exception("Expected action type to be S3, got: " + actionType)

    bucket_name = action['bucketName']
    object_key = action['objectKey']
    email_id = object_key

    print("Bucket name: " + bucket_name)
    print("Object key: " + object_key)

    s3 = boto3.client('s3')

    s3_raw_email = s3.get_object(Bucket=bucket_name, Key=object_key)

    raw_email_str = s3_raw_email['Body'].read().decode('utf-8')
    raw_email = email.parser.Parser(policy=policy.strict).parsestr(raw_email_str)

    dynamodb = boto3.client('dynamodb')

    item = {
        "email_id": {
            "S": email_id
        },
        "subject": {
            "S": raw_email['subject']
        }
    }

    dynamodb.put_item(
        TableName=EMAILS_DYNAMO_TABLE,
        Item=item,
        ReturnValues='NONE'
    )

    textract = boto3.client('textract')

    attachment_index = 0
    attachments = []
    for part in raw_email.walk():
        if part.is_attachment():
            attachment_id = str(attachment_index)
            attachment_index += 1

            job_tag = email_id + "_" + attachment_id
            print("Job tag: " + job_tag)

            attachment_key = object_key + "/attachments/" + attachment_id
            s3.put_object(Bucket=ATTACHMENTS_BUCKET, Key=attachment_key, Body=part.get_content())

            response = textract.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': ATTACHMENTS_BUCKET,
                        'Name': attachment_key
                    }
                },
                JobTag=job_tag,
                NotificationChannel={
                    'SNSTopicArn': TEXTRACT_NOTIFICATION_TOPIC_ARN,
                    'RoleArn': TEXTRACT_NOTIFICATION_ROLE_ARN
                }
            )

            attachments.append({
                'attachment_id': attachment_id,
                'content_type': part.get_content_type(),
                'key': attachment_key,
                'textract_job_id': response['JobId']
            })

    response = {
        'email_id': email_id,
        'attachments': attachments
    }

    print(str(response))

    return response