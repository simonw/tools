# Python scripts for use with uv run

These Python scripts can be run directly from their URLs using `uv run`.

## whitespace_cleaner.py

Replace any lines that are entirely whitespace with blank lines in specified files or folders:

```bash
uv run http://tools.simonwillison.net/python/whitespace_cleaner.py \
  my-file.txt my-folder
```
Has a `--dry-run` option for seeing how many files it would modify.

## all_gcp_buckets.py

View the size of the files in all of your Google Cloud buckets. You'll need to have [gcloud installed](https://cloud.google.com/sdk/docs/install) and do the `gcloud auth` dance first.

```bash
uv run http://tools.simonwillison.net/python/all_gcp_buckets.py
```
This will leave `.txt` files for each bucket containing a file listing, in a directory called `bucket_listings_DATE`.

## mistral_ocr.py

Run PDF files through the [Mistral OCR](https://mistral.ai/fr/news/mistral-ocr) API:

```bash
uv run http://tools.simonwillison.net/python/mistral_ocr.py \
  my-file.pdf > output.md
```
Or to generate HTML and save images and HTML to a directory:
```bash
uv run http://tools.simonwillison.net/python/mistral_ocr.py \
  my-file.pdf -d output-dir -he
```
`-he` is short for `--html --extract-images`.

Or to create HTML with images inlined as base64 URIs:
```bash
uv run http://tools.simonwillison.net/python/mistral_ocr.py \
  my-file.pdf -hi > output.html
```
`-hi` is short for `--html --inline-images`.

Full `--help`:

```
Usage: mistral_ocr.py [OPTIONS] FILE_PATH

  Process a PDF file using Mistral's OCR API and output the results.

  FILE_PATH is the path to the PDF file to process.

  Output Formats:
    - Markdown (default): Plain text markdown from the OCR results
    - HTML (--html): Converts markdown to HTML with proper formatting
    - JSON (--json): Raw JSON response from the Mistral OCR API

  Output Destinations:
    - stdout (default): Prints results to standard output
    - Single file (-o/--output): Writes to specified file
    - Directory (-d/--output-dir): Creates directory structure with main file and images
      * For HTML: Creates index.html in the directory
      * For Markdown: Creates README.md in the directory

  Image Handling:
    - No images (default): Images are excluded
    - Inline (-i/--inline-images): Images included as data URIs in the output
    - Extract (-e/--extract-images): Images saved as separate files in the output directory

Options:
  --api-key TEXT         Mistral API key. If not provided, will use
                         MISTRAL_API_KEY environment variable.
  -o, --output PATH      Output file path for the result. If not provided,
                         prints to stdout.
  -d, --output-dir PATH  Save output to a directory. For HTML creates
                         index.html, for markdown creates README.md, with
                         images in same directory.
  --model TEXT           Mistral OCR model to use.
  -j, --json             Return raw JSON instead of markdown text.
  -h, --html             Convert markdown to HTML.
  -i, --inline-images    Include images inline as data URIs (for HTML) or
                         base64 (for JSON).
  -e, --extract-images   Extract images as separate files (requires --output-
                         dir).
  -s, --silent           Suppress all output except for the requested data.
  --help                 Show this message and exit.
```

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
