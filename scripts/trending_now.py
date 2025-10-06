#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick CLI to print trending searches (seedless)

Usage (from repo root):
  python scripts/trending_now.py --pn south_korea --geo KR --topn 20 --daily
  python scripts/trending_now.py               # defaults to realtime KR
"""

import argparse
import os
import sys


def _add_naverdir_to_path():
    # Ensure we can import core.google_trends from journey/naver
    here = os.path.abspath(os.path.dirname(__file__))
    repo = os.path.abspath(os.path.join(here, os.pardir))
    naver_dir = os.path.join(repo, "journey", "naver")
    if os.path.isdir(naver_dir) and naver_dir not in sys.path:
        sys.path.insert(0, naver_dir)


def main():
    _add_naverdir_to_path()
    try:
        from core.google_trends import trending_now  # type: ignore
    except Exception as e:
        print("Error: unable to import trending module. Did you clone the repo root correctly?", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(2)

    ap = argparse.ArgumentParser(description="Print trending searches (Google Trends)")
    ap.add_argument("--pn", default="south_korea", help="Region param for daily trending (e.g., south_korea)")
    ap.add_argument("--geo", default="KR", help="Geo for realtime trending")
    ap.add_argument("--cat", default="all", help="Category for realtime trending")
    ap.add_argument("--topn", type=int, default=20, help="Number of rows")
    ap.add_argument("--daily", action="store_true", help="Use daily trending instead of realtime")
    args = ap.parse_args()

    try:
        df = trending_now(pn=args.pn, realtime=not args.daily, geo=args.geo, cat=args.cat, topn=args.topn)
        if df is None or df.empty:
            print("No results.")
            return 0
        for _, row in df.iterrows():
            q = row.get("query", "")
            src = row.get("source", "")
            val = row.get("value", 0)
            print(f"- {q} \t[{src}]\t{val}")
        return 0
    except Exception as e:
        print(f"Failed to fetch trending: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

