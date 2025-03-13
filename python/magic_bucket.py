# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "boto3",
# ]
# ///

import json
import click
import boto3
import io
import zipfile
from typing import Optional
import time

# IAM is global since it is a global service
iam = boto3.client("iam")


def create_lambda_role(role_name: str) -> str:
    """Create IAM role for Lambda function with necessary permissions."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        response = iam.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )

        # Attach necessary policies
        policy_arns = [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
            "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
        ]

        for policy_arn in policy_arns:
            iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        return response["Role"]["Arn"]
    except iam.exceptions.EntityAlreadyExistsException:
        return iam.get_role(RoleName=role_name)["Role"]["Arn"]


def create_lambda_function(
    function_name: str, role_arn: str, table_name: str, region: str
) -> str:
    """Create Lambda function to process S3 events and update DynamoDB."""
    # Note the use of double braces to escape inner curly braces so that the final code has proper f-string syntax.
    lambda_code = f"""
import json
import boto3
import urllib.parse
from datetime import datetime

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'])
        size = record['s3']['object'].get('size', 0)
        event_time = record.get('eventTime', '')
        event_name = record.get('eventName', '')

        if event_name.startswith('ObjectCreated'):
            # Get additional metadata from S3
            response = s3.head_object(Bucket=bucket, Key=key)
            content_type = response.get('ContentType', 'unknown')

            # Store in DynamoDB
            dynamodb.put_item(
                TableName='{table_name}',
                Item={{
                    'bucket_key': {{'S': f'{{bucket}}/{{key}}'}},
                    'filename': {{'S': key}},
                    'bucket': {{'S': bucket}},
                    'size': {{'N': str(size)}},
                    'content_type': {{'S': content_type}},
                    'last_modified': {{'S': event_time}},
                    'timestamp': {{'S': datetime.utcnow().isoformat()}}
                }}
            )
        elif event_name.startswith('ObjectRemoved'):
            # Remove from DynamoDB
            dynamodb.delete_item(
                TableName='{table_name}',
                Key={{
                    'bucket_key': {{'S': f'{{bucket}}/{{key}}'}}
                }}
            )

    return {{
        'statusCode': 200,
        'body': json.dumps('Successfully processed S3 event')
    }}
"""
    # Package the lambda code as a ZIP archive in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("lambda_function.py", lambda_code)
    zip_buffer.seek(0)
    zip_bytes = zip_buffer.read()

    lambda_client = boto3.client("lambda", region_name=region)

    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30,
            MemorySize=128,
            Environment={"Variables": {"DYNAMODB_TABLE": table_name}},
        )
        return response["FunctionArn"]
    except lambda_client.exceptions.ResourceConflictException:
        return lambda_client.get_function(FunctionName=function_name)["Configuration"][
            "FunctionArn"
        ]


def create_dynamodb_table(table_name: str, region: str):
    """Create DynamoDB table for storing file metadata."""
    dynamodb = boto3.client("dynamodb", region_name=region)
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "bucket_key", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "bucket_key", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
    except dynamodb.exceptions.ResourceInUseException:
        pass


@click.group()
@click.option("--region", default="us-east-1", help="AWS region for the resources")
@click.pass_context
def cli(ctx, region):
    """Manage S3 buckets with DynamoDB metadata tracking."""
    ctx.ensure_object(dict)
    ctx.obj["REGION"] = region


@cli.command()
@click.argument("bucket_name")
@click.pass_context
def create_bucket(ctx, bucket_name: str):
    """Create a new S3 bucket with Lambda triggers and DynamoDB table."""
    region = ctx.obj["REGION"]
    s3 = boto3.client("s3", region_name=region)
    lambda_client = boto3.client("lambda", region_name=region)

    try:
        # Create S3 bucket
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        click.echo(f"Created bucket: {bucket_name}")

        # Create DynamoDB table
        table_name = f"{bucket_name}-metadata"
        create_dynamodb_table(table_name, region)
        click.echo(f"Created DynamoDB table: {table_name}")

        # Create Lambda function
        role_name = f"{bucket_name}-lambda-role"
        role_arn = create_lambda_role(role_name)
        click.echo(f"Created/using IAM role: {role_name} - wait 10s for it to be ready")
        time.sleep(10)

        function_name = f"{bucket_name}-processor"
        lambda_arn = create_lambda_function(function_name, role_arn, table_name, region)
        click.echo(f"Created Lambda function: {function_name}")

        # Grant S3 permission to invoke the Lambda function
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=f"{bucket_name}-s3invoke",
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=f"arn:aws:s3:::{bucket_name}",
            )
        except lambda_client.exceptions.ResourceConflictException:
            # Permission already exists
            pass
        time.sleep(10)

        # Add bucket notification configuration
        s3.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration={
                "LambdaFunctionConfigurations": [
                    {
                        "LambdaFunctionArn": lambda_arn,
                        "Events": ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"],
                    }
                ]
            },
        )
        click.echo("Configured S3 event notifications")

        click.echo("\nSetup completed successfully!")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("bucket_name")
@click.option("--prefix", help="Filter files by prefix")
@click.option("--region", default="us-east-1", help="AWS region for the resources")
def list_files(bucket_name: str, prefix: Optional[str], region: str):
    """List files in the bucket using DynamoDB metadata."""
    dynamodb = boto3.client("dynamodb", region_name=region)
    table_name = f"{bucket_name}-metadata"

    try:
        # Scan DynamoDB table
        scan_kwargs = {
            "TableName": table_name,
        }

        if prefix:
            scan_kwargs["FilterExpression"] = "begins_with(filename, :prefix)"
            scan_kwargs["ExpressionAttributeValues"] = {":prefix": {"S": prefix}}

        response = dynamodb.scan(**scan_kwargs)

        if not response.get("Items"):
            click.echo("No files found.")
            return

        # Print file information
        click.echo("\nFiles in bucket:")
        click.echo("-" * 80)
        format_str = "{:<40} {:>10} {:<20} {:<20}"
        click.echo(
            format_str.format("Filename", "Size (B)", "Content Type", "Last Modified")
        )
        click.echo("-" * 80)

        for item in response["Items"]:
            click.echo(
                format_str.format(
                    item["filename"]["S"],
                    item["size"]["N"],
                    item["content_type"]["S"],
                    item["last_modified"]["S"],
                )
            )

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
