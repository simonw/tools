# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "PyMuPDF",
# ]
# ///
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple


def detect_invisible_text(pdf_path: str) -> Dict[str, List]:
    """
    Detect various types of invisible text in a PDF using PyMuPDF.

    Returns a dictionary with different categories of invisible text found.
    """
    doc = fitz.open(pdf_path)
    results = {
        "transparent_text": [],
        "off_page_text": [],
        "zero_size_text": [],
        "white_text_on_white": [],
        "hidden_text": [],
        "summary": {},
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_rect = page.rect

        # Get all text with detailed formatting information
        text_dict = page.get_text("dict")

        # Method 1: Check for transparent or nearly transparent text
        transparent_text = check_transparent_text(text_dict, page_num)
        results["transparent_text"].extend(transparent_text)

        # Method 2: Check for text positioned outside visible page area
        off_page_text = check_off_page_text(text_dict, page_rect, page_num)
        results["off_page_text"].extend(off_page_text)

        # Method 3: Check for zero or very small font sizes
        zero_size_text = check_zero_size_text(text_dict, page_num)
        results["zero_size_text"].extend(zero_size_text)

        # Method 4: Check for white text (often invisible on white backgrounds)
        white_text = check_white_text(text_dict, page_num)
        results["white_text_on_white"].extend(white_text)

        # Method 5: Compare extracted text vs visible text
        hidden_text = check_hidden_text(page, page_num)
        results["hidden_text"].extend(hidden_text)

    doc.close()

    # Generate summary
    total_invisible = sum(
        len(category) for category in results.values() if isinstance(category, list)
    )
    results["summary"] = {
        "total_invisible_text_instances": total_invisible,
        "pages_with_invisible_text": len(
            set(
                item["page"]
                for category in results.values()
                if isinstance(category, list)
                for item in category
            )
        ),
        "types_found": [
            key
            for key, value in results.items()
            if isinstance(value, list) and len(value) > 0
        ],
    }

    return results


def check_transparent_text(text_dict: Dict, page_num: int) -> List[Dict]:
    """Check for transparent or nearly transparent text."""
    transparent_texts = []

    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line.get("spans", []):
                    # Check text color for transparency
                    color = span.get("color", 0)
                    if color is not None:
                        # Extract RGB values (PyMuPDF uses integer color values)
                        r = (color >> 16) & 255
                        g = (color >> 8) & 255
                        b = color & 255

                        # Check for very light colors (near white) or specific transparency indicators
                        if (r > 250 and g > 250 and b > 250) or color == 0xFFFFFF:
                            text_content = span.get("text", "").strip()
                            if text_content:
                                transparent_texts.append(
                                    {
                                        "page": page_num,
                                        "text": text_content,
                                        "color": f"RGB({r}, {g}, {b})",
                                        "bbox": span.get("bbox"),
                                        "reason": "Very light/white text color",
                                    }
                                )

    return transparent_texts


def check_off_page_text(
    text_dict: Dict, page_rect: fitz.Rect, page_num: int
) -> List[Dict]:
    """Check for text positioned outside the visible page area."""
    off_page_texts = []

    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line.get("spans", []):
                    bbox = span.get("bbox")
                    if bbox:
                        span_rect = fitz.Rect(bbox)
                        # Check if text is completely outside page boundaries
                        if not span_rect.intersects(page_rect):
                            text_content = span.get("text", "").strip()
                            if text_content:
                                off_page_texts.append(
                                    {
                                        "page": page_num,
                                        "text": text_content,
                                        "bbox": bbox,
                                        "page_rect": tuple(page_rect),
                                        "reason": "Text positioned outside page boundaries",
                                    }
                                )

    return off_page_texts


def check_zero_size_text(text_dict: Dict, page_num: int) -> List[Dict]:
    """Check for text with zero or very small font sizes."""
    zero_size_texts = []

    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line.get("spans", []):
                    font_size = span.get("size", 0)
                    # Check for zero or very small font sizes
                    if font_size <= 0.5:  # Practically invisible
                        text_content = span.get("text", "").strip()
                        if text_content:
                            zero_size_texts.append(
                                {
                                    "page": page_num,
                                    "text": text_content,
                                    "font_size": font_size,
                                    "bbox": span.get("bbox"),
                                    "reason": f"Font size too small: {font_size}",
                                }
                            )

    return zero_size_texts


def check_white_text(text_dict: Dict, page_num: int) -> List[Dict]:
    """Check for white text that might be invisible on white backgrounds."""
    white_texts = []

    for block in text_dict.get("blocks", []):
        if "lines" in block:
            for line in block["lines"]:
                for span in line.get("spans", []):
                    color = span.get("color", 0)
                    if color == 0xFFFFFF or color == 16777215:  # Pure white
                        text_content = span.get("text", "").strip()
                        if text_content:
                            white_texts.append(
                                {
                                    "page": page_num,
                                    "text": text_content,
                                    "color": "White (RGB(255, 255, 255))",
                                    "bbox": span.get("bbox"),
                                    "reason": "White text (invisible on white background)",
                                }
                            )

    return white_texts


def check_hidden_text(page: fitz.Page, page_num: int) -> List[Dict]:
    """Compare all extractable text vs visually rendered text to find hidden content."""
    hidden_texts = []

    # Extract all text (including hidden)
    all_text = page.get_text()

    # Get visible text by rendering the page and using OCR-like extraction
    # This is a simplified approach - in practice, you might want more sophisticated methods
    visible_text_blocks = page.get_text("blocks")
    visible_text = ""

    for block in visible_text_blocks:
        if isinstance(block, tuple) and len(block) >= 5:
            visible_text += block[4]  # Text content is at index 4

    # Simple comparison - look for significant differences
    all_text_clean = re.sub(r"\s+", " ", all_text.strip())
    visible_text_clean = re.sub(r"\s+", " ", visible_text.strip())

    if len(all_text_clean) > len(visible_text_clean) * 1.1:  # 10% threshold
        hidden_texts.append(
            {
                "page": page_num,
                "all_text_length": len(all_text_clean),
                "visible_text_length": len(visible_text_clean),
                "potential_hidden_chars": len(all_text_clean) - len(visible_text_clean),
                "reason": "Significant difference between extractable and visible text",
            }
        )

    return hidden_texts


def print_results(results: Dict):
    """Print the results in a readable format."""
    print("=" * 60)
    print("INVISIBLE TEXT DETECTION RESULTS")
    print("=" * 60)

    summary = results["summary"]
    print(
        f"Total invisible text instances found: {summary['total_invisible_text_instances']}"
    )
    print(f"Pages with invisible text: {summary['pages_with_invisible_text']}")
    print(f"Types of invisible text found: {', '.join(summary['types_found'])}")
    print()

    for category, items in results.items():
        if category == "summary" or not items:
            continue

        print(f"\n{category.upper().replace('_', ' ')}:")
        print("-" * 40)

        for item in items:
            print(f"Page {item['page']}: {item.get('reason', 'Unknown')}")
            if "text" in item:
                text_preview = (
                    item["text"][:100] + "..."
                    if len(item["text"]) > 100
                    else item["text"]
                )
                print(f"  Text: '{text_preview}'")
            if "bbox" in item and item["bbox"]:
                print(f"  Position: {item['bbox']}")
            if "color" in item:
                print(f"  Color: {item['color']}")
            if "font_size" in item:
                print(f"  Font size: {item['font_size']}")
            print()


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python script.py <pdf_path>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        results = detect_invisible_text(pdf_path)
        print_results(results)

    except FileNotFoundError:
        print(f"Error: PDF file '{pdf_path}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error analyzing PDF: {e}", file=sys.stderr)
        sys.exit(1)
