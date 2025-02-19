# Python scripts for use with uv run

These Python scripts can be run directly from their URLs using `uv run`.

## highlight.py

Given input text to stdin and search/highlight terms, outputs matches plus context with colors to highlight them.

Example usage:
```bash
cat myfile.py | uv run http://tools.simonwillison.net/python/highlight.py re search
```
## debug_s3_access.py

Use this with a URL to an object in an S3 bucket to try and debug why that object cannot be accessed via its public URL.

Example usage:

```bash
uv run http://tools.simonwillison.net/python/debug_s3_access.py \
  https://test-public-bucket-simonw.s3.us-east-1.amazonaws.com/0f550b7b28264d7ea2b3d360e3381a95.jpg
```
Output:
```
Reading inline script metadata from remote URL

Analyzing S3 access for:
Bucket: test-public-bucket-simonw
Key: 0f550b7b28264d7ea2b3d360e3381a95.jpg

                                   S3 Access Analysis Results                                   
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                         ┃ Result                                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Bucket Exists                 │ Yes                                                          │
│ Bucket Region                 │ default                                                      │
│ Key exists                    │ Yes                                                          │
│ Bucket Policy                 │ {                                                            │
│                               │   "Version": "2012-10-17",                                   │
│                               │   "Statement": [                                             │
│                               │     {                                                        │
│                               │       "Sid": "AllowAllGetObject",                            │
│                               │       "Effect": "Allow",                                     │
│                               │       "Principal": "*",                                      │
│                               │       "Action": "s3:GetObject",                              │
│                               │       "Resource": "arn:aws:s3:::test-public-bucket-simonw/*" │
│                               │     }                                                        │
│                               │   ]                                                          │
│                               │ }                                                            │
│ Bucket Owner                  │ swillison                                                    │
│ Bucket ACL Grant to swillison │ FULL_CONTROL                                                 │
│ Default Encryption            │ [                                                            │
│                               │   {                                                          │
│                               │     "ApplyServerSideEncryptionByDefault": {                  │
│                               │       "SSEAlgorithm": "AES256"                               │
│                               │     },                                                       │
│                               │     "BucketKeyEnabled": false                                │
│                               │   }                                                          │
│                               │ ]                                                            │
│ Bucket Versioning             │ Not enabled                                                  │
│ Object exists                 │ Yes                                                          │
│ Content Type                  │ image/jpeg                                                   │
│ Size                          │ 71683 bytes                                                  │
│ Last Modified                 │ 2024-12-19 03:43:30+00:00                                    │
│ Storage Class                 │ Unknown                                                      │
│ Object Owner                  │ swillison                                                    │
│ ACL Grant to swillison        │ FULL_CONTROL                                                 │
└───────────────────────────────┴──────────────────────────────────────────────────────────────┘

Public Access Settings:
BlockPublicAcls: False
IgnorePublicAcls: False
BlockPublicPolicy: False
RestrictPublicBuckets: False
```
