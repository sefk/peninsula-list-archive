"""Search the index: uv run search.py "recommendations for fencing companies" [-n 10]"""
import argparse
import re
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "data" / "peninsula.db"
STOP = {"a", "an", "the", "for", "of", "to", "and", "in", "on", "any", "some", "is", "are", "with", "who", "what", "does", "do"}


def build_query(q):
    terms = [t for t in re.findall(r"\w+", q.lower()) if t not in STOP]
    # OR the terms so BM25 ranks threads matching more (and rarer) terms first
    return " OR ".join(f'"{t}"*' if len(t) > 3 else f'"{t}"' for t in terms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-n", type=int, default=10)
    args = ap.parse_args()
    db = sqlite3.connect(DB)
    rows = db.execute(
        """SELECT t.id, t.subject, t.started, t.n_messages, t.url,
                  snippet(fts, 1, '[', ']', ' … ', 24)
           FROM fts JOIN threads t ON t.id = fts.rowid
           WHERE fts MATCH ? ORDER BY bm25(fts, 5.0, 1.0) LIMIT ?""",
        (build_query(args.query), args.n),
    ).fetchall()
    for tid, subj, started, n, url, snip in rows:
        print(f"#{tid}  {started[:10]}  ({n} msgs)  {subj}\n    {snip.replace(chr(10), ' ')}\n    {url}\n")
    if not rows:
        print("No matches.")


if __name__ == "__main__":
    main()
