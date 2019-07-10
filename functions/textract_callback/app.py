import json
import boto3
import os

ATTACHMENTS_DYNAMO_TABLE = os.environ['ATTACHMENTS_DYNAMO_TABLE']

def lambda_handler(sns_payload, context):
    print(json.dumps(sns_payload))

    if 'Records' not in sns_payload:
        raise Exception('No Records section')

    if len(sns_payload['Records']) != 1:
        raise Exception('Expected only 1 record')

    sns_message = sns_payload['Records'][0]['Sns']['Message']
    event = json.loads(sns_message)
    job_tag = event['JobTag']
    split_job_tag = job_tag.split('_')

    if len(split_job_tag) != 2:
        raise Exception('Invalid job tag, expected [email_id]/[attachment_id], got: ' + job_tag)

    email_id = split_job_tag[0]
    attachment_id = split_job_tag[1]

    textract = boto3.client('textract')

    if event['API'] != 'StartDocumentTextDetection':
        raise Exception('Expected API to be StartDocumentTextDetection')

    if event['Status'] != 'SUCCEEDED':
        raise Exception('Content detection failed, got status: ' + event['Status'])

    response = textract.get_document_text_detection(
        JobId=event['JobId'],
        MaxResults=1000
    )

    lines = []
    for block in response['Blocks']:
        if block['BlockType'] == 'LINE':
            lines.append(block['Text'])

    text = "\n".join(lines)

    dynamodb = boto3.client('dynamodb')

    item = {
        "email_id": {
            "S": email_id
        },
        "attachment_id": {
            "S": attachment_id
        },
        "content": {
            "S": text
        }
    }

    dynamodb.put_item(
        TableName=ATTACHMENTS_DYNAMO_TABLE,
        Item=item,
        ReturnValues='NONE'
    )

    return {
        'text': text
    }