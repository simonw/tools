#!/usr/bin/env python3
"""Generate a JSON file mapping HTML files to their most recent commit dates."""
import json


def build_dates():
    # Load the gathered_links.json file
    try:
        with open("gathered_links.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: gathered_links.json not found. Run gather_links.py first.")
        return

    pages = data.get("pages", {})
    dates = {}

    for page_name, page_data in pages.items():
        commits = page_data.get("commits", [])
        if commits:
            # Find the most recent commit date
            most_recent = max(
                commits, key=lambda c: c.get("date", "0000-00-00T00:00:00")
            )
            date_str = most_recent.get("date", "")
            if date_str:
                # Extract just the date part (YYYY-MM-DD)
                dates[page_name] = date_str[:10]

    # Write the dates to a JSON file
    with open("dates.json", "w") as f:
        json.dump(dates, f)

    print(f"Generated dates.json with {len(dates)} entries")


if __name__ == "__main__":
    build_dates()
