textract-email-attachments-demo
===============================

Overview
-----------------------
This project is a simple Textract and Lambda demo. Incoming email messages are received by SES, persisted to S3 and any 
PDF PNG or JPG attachments have their text content extracted and stored to DynamoDB.
 
It uses: 
- [SES](https://aws.amazon.com/ses/) for incoming emails
- [SNS](https://aws.amazon.com/sns/) for notifications
- [S3](https://aws.amazon.com/s3/) for storage of raw emails as well as attachments
- [Textract](https://aws.amazon.com/textract/) to extract text from PDFs, PNGs and JPGs
- [DynamoDB](https://aws.amazon.com/dynamodb/) for processed attachment
- [Lambda](https://aws.amazon.com/lambda/) for processing
- [CloudFormation](https://aws.amazon.com/cloudformation/) and [SAM](https://aws.amazon.com/serverless/sam/) to define the infrastructure

#### Availability
Due to service availability limitations, this project can only be deployed in the following regions:
- `us-east-1`
- `us-west-2`
- `eu-west-1`

Architecture
-----------------------
The demo is deployed using 3 CloudFormation stacks:
- `cf/incoming-emails.yaml`: Sets up an SES rule set and rule to forward incoming emails from the specified domain to S3 and SNS
- `cf/compute-environment.yaml`: Sets up a compute environment including a VPC, subnets and VPC endpoints for the required services
- `cf/functions.yaml`: SAM template that sets up the Lambda functions and other dependencies needed for processing

In order to receive emails using SES, the domain must be verified and the proper MX record must be installed on the hosted zone. 
The `utilities/verify_domain.py` script can be used if your domain is hosted on Route 53.

Installation
-----------------------
#### Prerequisites
- Python 3.7
- pipenv (`pip install --user pipenv`) for development
- AWS CLI (`pip install --user awscli` or see [documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html))
- SAM CLI (`pip install --user aws-sam-cli` or see [documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html))
- Configured AWS credentials (`aws configure`)
- Access to add DNS records to the desired domain name
- Access to an S3 bucket to deploy the SAM template. The S3 bucket **must** be in the same region as the stacks you are deploying.

#### Deployment
From the project root (replace values enclosed in brackets with appropriate values):
```
pipenv shell
# Warning: this will modify any existing MX record on the domain name!
python3 utilities/verify_domain.py --domain [domain-name] --region [region]
aws cloudformation deploy --stack-name textract-demo-incoming --template-file cf/incoming-emails.yaml --region [region] --parameter DomainName=[domain-name]
aws cloudformation deploy --stack-name textract-demo-vpc --template-file cf/compute-environment.yaml --region [region]
sam package --output-template-file /tmp/packaged.yaml --template-file cf/functions.yaml --s3-bucket [deployment-bucket]
sam deploy --template-file /tmp/packaged.yaml --capabilities CAPABILITY_NAMED_IAM --parameter IncomingEmailStack=textract-demo-incoming ComputeEnvStack=textract-demo-vpc --stack-name textract-demo-functions --region [region]
```