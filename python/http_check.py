#!/usr/bin/env python3

import argparse
import sys
import urllib.request
import urllib.parse
import urllib.error
from http.client import HTTPMessage  # For type hinting response.info()

# --- Configuration ---
USER_AGENT = "Python-StdLib-HeaderCheck/1.1"  # Version bump


def check_url_features(url: str):
    """
    Performs checks on a given URL for Gzip, ETag, and Last-Modified support.

    Args:
        url: The URL string to test.

    Returns:
        None. Prints results to stdout. Exits with code 1 on critical errors.
    """
    print(f"[*] Testing URL: {url}")

    # --- State Variables ---
    supports_gzip = False
    etag = None
    last_modified = None
    etag_conditional_worked = None  # None = N/A, False = Failed, True = Worked (304)
    last_modified_conditional_worked = (
        None  # None = N/A, False = Failed, True = Worked (304)
    )

    # --- Initial Request (Check for Gzip, ETag, Last-Modified) ---
    print("[*] Performing initial GET request...")
    initial_headers = {
        "Accept-Encoding": "gzip",
        "User-Agent": USER_AGENT,
    }
    req_initial = urllib.request.Request(url, headers=initial_headers, method="GET")

    try:
        with urllib.request.urlopen(
            req_initial, timeout=15
        ) as response:  # Increased timeout slightly
            initial_info = response.info()  # Headers object
            status_code = response.getcode()
            print(f"[+] Initial request successful (Status: {status_code})")

            # Check for Gzip support in response
            content_encoding = initial_info.get("Content-Encoding", "").lower()
            if "gzip" in content_encoding:
                supports_gzip = True
                print("[+] Gzip: Supported (Server sent 'Content-Encoding: gzip')")
            else:
                print("[-] Gzip: Not detected in response headers.")

            # Extract ETag and Last-Modified for conditional requests
            etag = initial_info.get("ETag")
            last_modified = initial_info.get("Last-Modified")

            if etag:
                print(f"[+] ETag: Found ('{etag}')")
            else:
                print("[-] ETag: Header not found.")

            if last_modified:
                print(f"[+] Last-Modified: Found ('{last_modified}')")
            else:
                print("[-] Last-Modified: Header not found.")

            # Ensure response body is read and connection potentially closed/reused
            response.read()

    except urllib.error.HTTPError as e:
        print(
            f"[!] Initial Request Failed: HTTP Error {e.code} - {e.reason}",
            file=sys.stderr,
        )
        if e.headers:
            print("[!] Server response headers (on error):")
            print(e.headers)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[!] Initial Request Failed: URL Error - {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(
            f"[!] Initial Request Failed: An unexpected error occurred - {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Conditional GET Request (ETag) ---
    if etag:
        print("\n[*] Performing conditional GET request using ETag...")
        etag_conditional_worked = False  # Assume failure unless we get 304
        conditional_headers_etag = {
            "User-Agent": USER_AGENT,
            "If-None-Match": etag,
            "Accept-Encoding": "gzip",
        }
        req_conditional_etag = urllib.request.Request(
            url, headers=conditional_headers_etag, method="GET"
        )

        try:
            with urllib.request.urlopen(req_conditional_etag, timeout=10) as response:
                status_code = response.getcode()
                # If we get here without a 304, the conditional GET didn't work as expected
                print(
                    f"[-] ETag Conditional GET: Did not work as expected. Received Status {status_code} (expected 304). Server sent full response."
                )
                response.read()  # Consume body

        except urllib.error.HTTPError as e:
            if e.code == 304:
                print(
                    "[+] ETag Conditional GET: Worked! Received Status 304 (Not Modified)."
                )
                etag_conditional_worked = True
            else:
                print(
                    f"[!] ETag Conditional GET: Failed. Server responded with HTTP Error {e.code} - {e.reason}",
                    file=sys.stderr,
                )
        except urllib.error.URLError as e:
            print(
                f"[!] ETag Conditional GET: Request failed. URL Error - {e.reason}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"[!] ETag Conditional GET: Request failed. An unexpected error occurred - {e}",
                file=sys.stderr,
            )
    else:
        print(
            "\n[*] Skipping ETag conditional GET (No ETag found in initial response)."
        )
        # etag_conditional_worked remains None

    # --- Conditional GET Request (Last-Modified) ---
    if last_modified:
        print("\n[*] Performing conditional GET request using Last-Modified...")
        last_modified_conditional_worked = False  # Assume failure unless we get 304
        conditional_headers_lm = {
            "User-Agent": USER_AGENT,
            "If-Modified-Since": last_modified,
            "Accept-Encoding": "gzip",
        }
        req_conditional_lm = urllib.request.Request(
            url, headers=conditional_headers_lm, method="GET"
        )

        try:
            with urllib.request.urlopen(req_conditional_lm, timeout=10) as response:
                status_code = response.getcode()
                # If we get here without a 304, the conditional GET didn't work as expected
                print(
                    f"[-] Last-Modified Conditional GET: Did not work as expected. Received Status {status_code} (expected 304). Server sent full response."
                )
                response.read()  # Consume body

        except urllib.error.HTTPError as e:
            if e.code == 304:
                print(
                    "[+] Last-Modified Conditional GET: Worked! Received Status 304 (Not Modified)."
                )
                last_modified_conditional_worked = True
            else:
                print(
                    f"[!] Last-Modified Conditional GET: Failed. Server responded with HTTP Error {e.code} - {e.reason}",
                    file=sys.stderr,
                )
        except urllib.error.URLError as e:
            print(
                f"[!] Last-Modified Conditional GET: Request failed. URL Error - {e.reason}",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"[!] Last-Modified Conditional GET: Request failed. An unexpected error occurred - {e}",
                file=sys.stderr,
            )
    else:
        print(
            "\n[*] Skipping Last-Modified conditional GET (No Last-Modified header found)."
        )
        # last_modified_conditional_worked remains None

    # --- Final Summary ---
    print("\n--- Summary ---")
    print(f"URL: {url}")
    print(f"Gzip Supported by Server: {'Yes' if supports_gzip else 'No'}")
    print(f"ETag Header Present: {'Yes' if etag else 'No'}")
    if etag:
        print(
            f"ETag Conditional GET Works (Returns 304): {'Yes' if etag_conditional_worked else 'No'}"
        )
    else:
        print(f"ETag Conditional GET Works (Returns 304): N/A")

    print(f"Last-Modified Header Present: {'Yes' if last_modified else 'No'}")
    if last_modified:
        print(
            f"Last-Modified Conditional GET Works (Returns 304): {'Yes' if last_modified_conditional_worked else 'No'}"
        )
    else:
        print(f"Last-Modified Conditional GET Works (Returns 304): N/A")
    print("-------------\n")


def main():
    """Parses arguments and runs the check."""
    parser = argparse.ArgumentParser(
        description="Check a URL for Gzip, ETag, and Last-Modified support using only Python's standard library.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", help="The URL to test (e.g., https://www.example.com)")

    args = parser.parse_args()

    # Basic URL validation and scheme addition
    parsed_url = urllib.parse.urlparse(args.url)
    if not parsed_url.scheme:
        # Try https first if no scheme provided, fall back to http if needed?
        # For simplicity now, just default to http and warn.
        print(
            f"[!] URL '{args.url}' is missing a scheme (e.g., http:// or https://). Assuming 'http://'.",
            file=sys.stderr,
        )
        url_to_test = f"http://{args.url}"
        parsed_url = urllib.parse.urlparse(url_to_test)  # Re-parse
        if not parsed_url.netloc:
            print(
                f"[!] Invalid URL structure even after adding http://: '{url_to_test}'",
                file=sys.stderr,
            )
            sys.exit(1)

    else:
        url_to_test = args.url
        if not parsed_url.netloc:
            print(f"[!] Invalid URL structure: '{url_to_test}'", file=sys.stderr)
            sys.exit(1)

    check_url_features(url_to_test)


if __name__ == "__main__":
    main()
