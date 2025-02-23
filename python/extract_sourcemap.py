# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

import re
import base64
import sys
import click


@click.command()
@click.argument("file_path", type=click.Path(exists=True))
def extract_sourcemap(file_path):
    """
    Extract and decode a base64-encoded source map from a JavaScript file.

    This tool searches for sourceMappingURL with base64-encoded data and outputs
    the decoded content to stdout.
    """
    try:
        # Read the JavaScript file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regular expression to find the sourceMappingURL with base64 data
        pattern = r"//# sourceMappingURL=data:application/json;base64,([a-zA-Z0-9+/=]+)"
        match = re.search(pattern, content)

        if match:
            # Extract the base64 encoded part
            base64_data = match.group(1)

            # Decode the base64 data
            decoded_data = base64.b64decode(base64_data).decode("utf-8")

            # Print the decoded content to stdout
            click.echo(decoded_data)

            return 0
        else:
            click.echo("No source map data found in the file.", err=True)
            return 1

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(extract_sourcemap())
