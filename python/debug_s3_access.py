# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "boto3",
#     "urllib3",
#     "rich",
# ]
# ///

import click
import boto3
import re
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from botocore.exceptions import ClientError
import json


def parse_s3_url(url):
    """Extract bucket and key from either URL format."""
    if "s3.amazonaws.com" in url:
        # Format: https://s3.amazonaws.com/bucket-name/key
        path_parts = urlparse(url).path.lstrip("/").split("/", 1)
        return path_parts[0], path_parts[1]
    else:
        # Format: https://bucket-name.s3.region.amazonaws.com/key
        bucket = urlparse(url).netloc.split(".")[0]
        key = urlparse(url).path.lstrip("/")
        return bucket, key


def check_bucket_exists(s3_client, bucket):
    """Verify if bucket exists and check its region."""
    try:
        response = s3_client.head_bucket(Bucket=bucket)
        region = s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
        return True, region
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "404":
            return False, "Bucket does not exist"
        elif error_code == "403":
            return False, "Access denied to bucket"
        return False, f"Error: {error_code}"


def check_key_exists(s3_client, bucket, key):
    """Verify if key exists and check its properties."""
    results = []
    try:
        # List objects with prefix to check for similar keys
        paginator = s3_client.get_paginator("list_objects_v2")
        similar_keys = []
        for page in paginator.paginate(Bucket=bucket, Prefix=key.split("/")[0]):
            for obj in page.get("Contents", []):
                if obj["Key"] != key and key in obj["Key"]:
                    similar_keys.append(obj["Key"])

        if similar_keys:
            results.append(("Similar keys found", "\n".join(similar_keys[:5])))

        # Try to get the specific key
        s3_client.head_object(Bucket=bucket, Key=key)
        results.append(("Key exists", "Yes"))
    except ClientError as e:
        print("error", e)
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        results.append(("Key exists", f"No - {error_code}"))

        # If not found, check if it's in a different case
        try:
            for page in paginator.paginate(Bucket=bucket, Prefix=key.split("/")[0]):
                for obj in page.get("Contents", []):
                    if obj["Key"].lower() == key.lower():
                        results.append(("Case mismatch found", obj["Key"]))
                        break
        except ClientError:
            pass

    return results


def check_object_metadata(s3_client, bucket, key):
    """Try to get object metadata, versions, and ACL information."""
    results = []
    try:
        # Check if versioning is enabled
        versioning = s3_client.get_bucket_versioning(Bucket=bucket)
        results.append(("Bucket Versioning", versioning.get("Status", "Not enabled")))

        # Try to get object metadata
        response = s3_client.head_object(Bucket=bucket, Key=key)
        results.append(("Object exists", "Yes"))
        results.append(("Content Type", response.get("ContentType", "Unknown")))
        results.append(("Size", f"{response.get('ContentLength', 0)} bytes"))
        results.append(("Last Modified", str(response.get("LastModified", "Unknown"))))
        results.append(("Storage Class", response.get("StorageClass", "Unknown")))

        # Check object ACL
        try:
            acl = s3_client.get_object_acl(Bucket=bucket, Key=key)
            results.append(("Object Owner", acl["Owner"].get("DisplayName", "Unknown")))
            for grant in acl.get("Grants", []):
                grantee = grant["Grantee"].get(
                    "DisplayName",
                    grant["Grantee"].get("URI", grant["Grantee"].get("ID", "Unknown")),
                )
                results.append((f"ACL Grant to {grantee}", grant["Permission"]))
        except ClientError as e:
            results.append(("Object ACL", f"Error: {e.response['Error']['Message']}"))

        # Check for object versions
        if versioning.get("Status") == "Enabled":
            versions = s3_client.list_object_versions(Bucket=bucket, Prefix=key)
            for version in versions.get("Versions", []):
                results.append(
                    (
                        f"Version {version['VersionId']}",
                        f"Last Modified: {version['LastModified']}",
                    )
                )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        results.append(("Error", f"{error_code}: {e.response['Error']['Message']}"))

        # Check if object was deleted recently
        try:
            deleted = s3_client.list_object_versions(Bucket=bucket, Prefix=key).get(
                "DeleteMarkers", []
            )
            if deleted:
                results.append(("Delete Markers Found", "Yes"))
                for marker in deleted:
                    results.append(
                        (
                            "Deleted on",
                            f"{marker['LastModified']} (Version: {marker['VersionId']})",
                        )
                    )
        except ClientError:
            pass

    return results


def check_bucket_policy(s3_client, bucket):
    """Check bucket policy, ACLs, and encryption settings."""
    results = []

    # Check bucket policy
    try:
        policy = s3_client.get_bucket_policy(Bucket=bucket)
        results.append(
            ("Bucket Policy", json.dumps(json.loads(policy["Policy"]), indent=2))
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucketPolicy":
            results.append(("Bucket Policy", "No bucket policy found"))
        else:
            results.append(
                ("Bucket Policy", f"Error: {e.response['Error']['Message']}")
            )

    # Check bucket ACL
    try:
        acl = s3_client.get_bucket_acl(Bucket=bucket)
        results.append(("Bucket Owner", acl["Owner"].get("DisplayName", "Unknown")))
        for grant in acl.get("Grants", []):
            grantee = grant["Grantee"].get(
                "DisplayName",
                grant["Grantee"].get("URI", grant["Grantee"].get("ID", "Unknown")),
            )
            results.append((f"Bucket ACL Grant to {grantee}", grant["Permission"]))
    except ClientError as e:
        results.append(("Bucket ACL", f"Error: {e.response['Error']['Message']}"))

    # Check encryption
    try:
        encryption = s3_client.get_bucket_encryption(Bucket=bucket)
        results.append(
            (
                "Default Encryption",
                json.dumps(
                    encryption["ServerSideEncryptionConfiguration"]["Rules"], indent=2
                ),
            )
        )
    except ClientError as e:
        if (
            e.response["Error"]["Code"]
            == "ServerSideEncryptionConfigurationNotFoundError"
        ):
            results.append(("Default Encryption", "Not configured"))
        else:
            results.append(
                ("Default Encryption", f"Error: {e.response['Error']['Message']}")
            )

    return results


@click.command()
@click.argument("url")
@click.option("--region", help="AWS region override")
@click.option("--profile", help="AWS profile name")
def debug_s3_access(url, region, profile):
    """Debug S3 access issues for a given URL."""
    console = Console()

    bucket, key = parse_s3_url(url)
    console.print(f"\n[bold]Analyzing S3 access for:[/bold]")
    console.print(f"Bucket: {bucket}")
    console.print(f"Key: {key}\n")

    # Initialize boto3 session
    session = boto3.Session(profile_name=profile)
    s3_client = session.client("s3", region_name=region)

    # Check bucket existence and region
    bucket_exists, bucket_region = check_bucket_exists(s3_client, bucket)

    if not bucket_exists:
        console.print(f"[red]Bucket check failed: {bucket_region}[/red]")
        return

    if bucket_region and bucket_region != region:
        console.print(
            f"[yellow]Note: Bucket is in {bucket_region}, retrying with correct region[/yellow]\n"
        )
        s3_client = session.client("s3", region_name=bucket_region)

    # Create results table
    table = Table(title="S3 Access Analysis Results")
    table.add_column("Check", style="cyan")
    table.add_column("Result", style="green")

    # Add bucket info
    table.add_row("Bucket Exists", "Yes")
    table.add_row("Bucket Region", bucket_region or "default")

    # Check key existence and similar keys
    for check, result in check_key_exists(s3_client, bucket, key):
        table.add_row(check, str(result))

    # Check bucket policies and ACLs
    for check, result in check_bucket_policy(s3_client, bucket):
        table.add_row(check, str(result))

    # Check object metadata, versions, and ACLs
    for check, result in check_object_metadata(s3_client, bucket, key):
        table.add_row(check, str(result))

    console.print(table)

    # Additional checks for public access
    try:
        public_access = s3_client.get_public_access_block(Bucket=bucket)
        console.print("\n[bold]Public Access Settings:[/bold]")
        for setting, value in public_access["PublicAccessBlockConfiguration"].items():
            console.print(f"{setting}: {value}")
    except ClientError:
        console.print(
            "\n[yellow]Could not retrieve public access block settings[/yellow]"
        )


if __name__ == "__main__":
    debug_s3_access()
