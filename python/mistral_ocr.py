# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "mistralai",
#     "markdown",
# ]
# ///

import os
import json
import base64
import re
from pathlib import Path
import click
import markdown
from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk


@click.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--api-key",
    help="Mistral API key. If not provided, will use MISTRAL_API_KEY environment variable.",
    envvar="MISTRAL_API_KEY",
)
@click.option(
    "--output",
    "-o",
    help="Output file path for the result. If not provided, prints to stdout.",
    type=click.Path(),
)
@click.option(
    "--output-dir",
    "-d",
    help="Save output to a directory. For HTML creates index.html, for markdown creates README.md, with images in same directory.",
    type=click.Path(),
)
@click.option("--model", help="Mistral OCR model to use.", default="mistral-ocr-latest")
@click.option(
    "json_",
    "--json",
    "-j",
    is_flag=True,
    help="Return raw JSON instead of markdown text.",
)
@click.option(
    "--html",
    "-h",
    is_flag=True,
    help="Convert markdown to HTML.",
)
@click.option(
    "--inline-images",
    "-i",
    is_flag=True,
    help="Include images inline as data URIs (for HTML) or base64 (for JSON).",
)
@click.option(
    "--extract-images",
    "-e",
    is_flag=True,
    help="Extract images as separate files (requires --output-dir).",
)
@click.option(
    "--silent",
    "-s",
    is_flag=True,
    help="Suppress all output except for the requested data.",
)
def ocr_pdf(
    file_path,
    api_key,
    output,
    output_dir,
    model,
    json_,
    html,
    inline_images,
    extract_images,
    silent,
):
    """Process a PDF file using Mistral's OCR API and output the results.

    FILE_PATH is the path to the PDF file to process.

    \b
    Output Formats:
      - Markdown (default): Plain text markdown from the OCR results
      - HTML (--html): Converts markdown to HTML with proper formatting
      - JSON (--json): Raw JSON response from the Mistral OCR API

    \b
    Output Destinations:
      - stdout (default): Prints results to standard output
      - Single file (-o/--output): Writes to specified file
      - Directory (-d/--output-dir): Creates directory structure with main file and images
        * For HTML: Creates index.html in the directory
        * For Markdown: Creates README.md in the directory

    \b
    Image Handling:
      - No images (default): Images are excluded
      - Inline (-i/--inline-images): Images included as data URIs in the output
      - Extract (-e/--extract-images): Images saved as separate files in the output directory
    """
    # Validate options
    if not api_key:
        raise click.ClickException(
            "No API key provided and MISTRAL_API_KEY environment variable not set."
        )

    if output and output_dir:
        raise click.ClickException("Cannot specify both --output and --output-dir")

    if json_ and output_dir:
        raise click.ClickException("JSON output is not supported with --output-dir")

    if extract_images and not output_dir:
        raise click.ClickException("--extract-images requires --output-dir")

    if inline_images and extract_images:
        raise click.ClickException(
            "Cannot specify both --inline-images and --extract-images"
        )

    # Determine output format
    if json_:
        output_format = "json"
    elif html:
        output_format = "html"
    else:
        output_format = "markdown"

    pdf_file = Path(file_path)
    client = Mistral(api_key=api_key)
    uploaded_file = None

    try:
        if not silent:
            click.echo(f"Uploading file {pdf_file.name}...", err=True)
        uploaded_file = client.files.upload(
            file={
                "file_name": pdf_file.stem,
                "content": pdf_file.read_bytes(),
            },
            purpose="ocr",
        )

        signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)

        if not silent:
            click.echo(f"Processing with OCR model: {model}...", err=True)
        pdf_response = client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model=model,
            include_image_base64=inline_images or extract_images,
        )

        response_dict = json.loads(pdf_response.model_dump_json())

        # Create output directory if specified
        if output_dir:
            dir_path = Path(output_dir)
            dir_path.mkdir(parents=True, exist_ok=True)

        # Process images if needed
        image_map = {}
        if extract_images and output_dir:
            image_count = 0
            image_dir = Path(output_dir)

            for page in response_dict.get("pages", []):
                for img in page.get("images", []):
                    if "id" in img and "image_base64" in img:
                        image_data = img["image_base64"]
                        # Strip the prefix if it exists
                        if image_data.startswith("data:image/"):
                            image_data = image_data.split(",", 1)[1]

                        image_filename = img["id"]
                        image_path = image_dir / image_filename

                        with open(image_path, "wb") as img_file:
                            img_file.write(base64.b64decode(image_data))

                        # Map image_id to relative path for referencing in markdown/html
                        image_map[image_filename] = image_filename
                        image_count += 1

            if not silent:
                click.echo(f"Extracted {image_count} images to {image_dir}", err=True)

        # Create image map for inline images
        elif inline_images:
            for page in response_dict.get("pages", []):
                for img in page.get("images", []):
                    if "id" in img and "image_base64" in img:
                        image_id = img["id"]
                        image_data = img["image_base64"]
                        # Ensure it has the data URI prefix
                        if not image_data.startswith("data:"):
                            # Determine image type from filename or default to jpeg
                            ext = (
                                image_id.split(".")[-1].lower()
                                if "." in image_id
                                else "jpeg"
                            )
                            mime_type = f"image/{ext}"
                            image_data = f"data:{mime_type};base64,{image_data}"
                        image_map[image_id] = image_data

        # Generate output content based on format
        if output_format == "json":
            result = json.dumps(response_dict, indent=4)
        else:
            # Concatenate markdown content from all pages
            markdown_contents = [
                page.get("markdown", "") for page in response_dict.get("pages", [])
            ]
            markdown_text = "\n\n".join(markdown_contents)

            # Handle image references in markdown if needed
            for img_id, img_src in image_map.items():
                # Replace any markdown image references with the correct path/data URI
                markdown_text = re.sub(
                    r"!\[(.*?)\]\(" + re.escape(img_id) + r"\)",
                    r"![\1](" + img_src + r")",
                    markdown_text,
                )

            if output_format == "html":
                # Convert markdown to HTML
                md = markdown.Markdown(extensions=["tables"])
                html_content = md.convert(markdown_text)

                # Add minimal HTML wrapper with basic styling
                result = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Result</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0 auto;
            max-width: 800px;
            padding: 20px;
        }}
        img {{ max-width: 100%; height: auto; }}
        h1, h2, h3 {{ margin-top: 1.5em; }}
        p {{ margin: 1em 0; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
            else:  # markdown
                result = markdown_text

        # Output the result
        if output_dir:
            if output_format == "html":
                output_file = Path(output_dir) / "index.html"
            else:  # markdown
                output_file = Path(output_dir) / "README.md"

            output_file.write_text(result)
            if not silent:
                click.echo(f"Results saved to {output_file}", err=True)
        elif output:
            output_path = Path(output)
            output_path.write_text(result)
            if not silent:
                click.echo(f"Results saved to {output_path}", err=True)
        else:
            # Print directly to stdout without any error messaging
            click.echo(result)

    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")
    finally:
        # Clean up the uploaded file
        try:
            if uploaded_file:
                client.files.delete(file_id=uploaded_file.id)
                if not silent:
                    click.echo("Temporary file deleted.", err=True)
        except Exception as e:
            if not silent:
                click.echo(
                    f"Warning: Could not delete temporary file: {str(e)}", err=True
                )


if __name__ == "__main__":
    ocr_pdf()
