import argparse
import boto3


def main():
    parser = argparse.ArgumentParser(description='Utility to verify a domain with SES and add MX record for incoming '
                                                 'emails')

    parser.add_argument('--domain', dest='domain', type=str,
                        help='Domain name to verify', required=True)

    parser.add_argument('--region', dest='region', type=str,
                        help='AWS region', default="us-east-1", required=True)

    args = parser.parse_args()

    boto3.setup_default_session(region_name=args.region)

    domain = args.domain

    route53 = boto3.client('route53')

    hosted_zones = route53.list_hosted_zones_by_name(MaxItems="1000")['HostedZones']

    if domain[-1] != '.':
        search = domain + '.'
    else:
        search = domain

    filtered_hosted_zones = [zone for zone in hosted_zones if zone['Name'] == search]

    if len(filtered_hosted_zones) == 0:
        print(f'Could not find zone {domain} in Route53')
        exit(1)

    hosted_zone = filtered_hosted_zones[0]
    hosted_zone_id = hosted_zone['Id']

    ses = boto3.client('ses')

    try:
        response = ses.verify_domain_identity(Domain=domain)
    except Exception as e:
        print("Unable to get SES verification token")
        print(str(e))
        exit(1)
        raise e

    verification_token = response['VerificationToken']

    txt_record_name = '_amazonses.' + domain
    txt_record_value = '"' + verification_token + '"'
    region = ses.meta.region_name
    mx_record_name = domain
    mx_record_value = f'10 inbound-smtp.{region}.amazonaws.com'

    change_batch = {
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': mx_record_name,
                    'Type': 'MX',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': mx_record_value}]
                }
            },
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': txt_record_name,
                    'Type': 'TXT',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': txt_record_value}]
                }
            }
        ]
    }

    print(f"Adding record {txt_record_name} IN TXT {txt_record_value} to hosted zone {hosted_zone_id}")
    print(f"Adding record {mx_record_name} IN MX {mx_record_value} to hosted zone {hosted_zone_id}")

    try:
        route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch=change_batch
        )
    except Exception as e:
        print(f"Unable to add record to zone {domain} ({hosted_zone_id})")
        print(str(e))


if __name__ == "__main__":
    main()
