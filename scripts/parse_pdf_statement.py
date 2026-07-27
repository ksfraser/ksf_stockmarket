#!/usr/bin/env python3
"""
parse_pdf_statement.py — CLI wrapper for the shared PDF parser module.

Usage: python3 parse_pdf_statement.py <pdf_path> [--debug] [--force-ocr]

Output: JSON to stdout
"""

import json
import os
import sys

# Add parent directory to path so we can import pdf_parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_parser.parsers import parse_statement, extract_text


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: parse_pdf_statement.py <pdf_path> [--debug] [--force-ocr]"}))
        sys.exit(1)

    pdf_path = sys.argv[1]
    debug_mode = '--debug' in sys.argv
    force_ocr = '--force-ocr' in sys.argv

    if not os.path.exists(pdf_path):
        print(json.dumps({"error": f"File not found: {pdf_path}"}))
        sys.exit(1)

    result = parse_statement(pdf_path, debug=debug_mode, force_ocr=force_ocr)

    # Write debug file if 0 transactions or debug mode
    if debug_mode or not result['transactions']:
        try:
            debug_dir = '/var/www/stockmarket-app/uploads/debug/'
            os.makedirs(debug_dir, exist_ok=True)
            debug_file = debug_dir + os.path.basename(pdf_path) + '.debug.txt'
            with open(debug_file, 'w') as f:
                f.write("Format: {}\n".format(result['format']))
                f.write("Account: {}\n".format(result['account']))
                f.write("Pages: {}\n".format(result['pages']))
                f.write("Transactions found: {}\n\n".format(len(result['transactions'])))
                if result.get('text_preview'):
                    f.write("=== TEXT PREVIEW ===\n{}\n\n".format(result['text_preview']))
                if result.get('suspicious_lines'):
                    f.write("=== SUSPICIOUS LINES ===\n")
                    for sl in result['suspicious_lines']:
                        f.write(sl + "\n")
                # Also write full text
                f.write("\n=== FULL TEXT ===\n")
                text, _ = extract_text(pdf_path, force_ocr=force_ocr)
                f.write(text)
        except Exception:
            pass

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
