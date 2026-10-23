"""Download the quarterly mbox files from the Mailman private archive.

Credentials come from PENINSULA_USER / PENINSULA_PASS.
Files land in data/raw/. Existing files are skipped, except the newest quarter.
"""
import os
import re
import sys
import time
from pathlib import Path

import requests

BASE = "https://www.employees.org/mailman/private/peninsula/"
RAW = Path(__file__).parent / "data" / "raw"


def main():
    user, pw = os.environ.get("PENINSULA_USER"), os.environ.get("PENINSULA_PASS")
    if not user or not pw:
        sys.exit("Set PENINSULA_USER and PENINSULA_PASS")
    RAW.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    r = s.post(BASE, data={"username": user, "password": pw, "submit": "Let me in..."})
    r.raise_for_status()
    quarters = sorted(set(re.findall(r'href="(\d{4}q\d)\.txt\.gz"', r.text)))
    if not quarters:
        sys.exit("No archive links found; login probably failed")
    newest = quarters[-1]
    for q in quarters:
        dest = RAW / f"{q}.mbox"
        if dest.exists() and q != newest:
            continue
        resp = s.get(f"{BASE}{q}.txt.gz")
        resp.raise_for_status()
        dest.write_bytes(resp.content)  # served already decompressed
        print(f"{q}: {len(resp.content):,} bytes")
        time.sleep(1)


if __name__ == "__main__":
    main()
