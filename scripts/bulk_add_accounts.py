#!/usr/bin/env python3
"""
CLI Utility to bulk import MT5 accounts from CSV, TSV, or colon-delimited files.

Usage:
  python scripts/bulk_add_accounts.py <path-to-file.csv> [--server SERVER] [--node NODE] [--overwrite]

Supported Formats:
  1. CSV with headers: login, password, server, name, node, symbol, timeframe, expert
  2. Simple CSV: 25506235,Password123,VantageMarkets-Demo
  3. Colon-separated: 25506235:Password123:VantageMarkets-Demo
"""

import sys
import os
import argparse

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.db import init_db
from app.api_accounts import parse_csv_or_text_content, create_accounts_bulk

def main():
    parser = argparse.ArgumentParser(description="Bulk add MT5 accounts to Hub Database")
    parser.add_argument("file", help="Path to CSV, TSV, or TXT file containing MT5 credentials")
    parser.add_argument("--server", default="", help="Default broker server name if omitted in file")
    parser.add_argument("--node", default="auto", help="Assigned Worker Node ID (default: auto)")
    parser.add_argument("--no-overwrite", action="store_true", help="Do not overwrite existing accounts")

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"[!] Error: File '{args.file}' does not exist.")
        sys.exit(1)

    print(f"[*] Reading accounts from '{args.file}'...")
    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    parsed = parse_csv_or_text_content(
        content,
        default_server=args.server,
        default_node=args.node
    )

    if not parsed:
        print("[!] No valid MT5 account entries detected in the file.")
        sys.exit(1)

    print(f"[*] Successfully parsed {len(parsed)} account records. Initializing DB...")
    init_db()

    print(f"[*] Inserting / updating accounts in database...")
    res = create_accounts_bulk(parsed, overwrite_existing=not args.no_overwrite)

    print("\n" + "=" * 50)
    print("BULK IMPORT SUMMARY")
    print("=" * 50)
    print(f"Total Parsed : {res['total']}")
    print(f"Newly Created: {res['created']}")
    print(f"Updated      : {res['updated']}")
    print(f"Skipped      : {res['skipped']}")
    print(f"Errors       : {len(res['errors'])}")
    if res['errors']:
        print("\nErrors encountered:")
        for err in res['errors']:
            print(f"  - Line/Index {err.get('index')}: Login {err.get('login')} -> {err.get('error')}")
    print("=" * 50)
    print("[✓] Done! Terminals will be auto-assigned and started by the Hub scheduler.")

if __name__ == "__main__":
    main()
