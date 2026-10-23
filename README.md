# peninsula-list-archive

Local, searchable index of the Peninsula mailing list private Mailman archive.
The scraped archive (`data/`) is git-ignored; only code is committed.

```
export PENINSULA_USER=you@example.com PENINSULA_PASS=...
uv run fetch.py                 # download quarterly mbox files to data/raw/
uv run index.py                 # parse, thread, build data/peninsula.db (SQLite FTS5)
uv run search.py "recommendations for fencing companies" -n 10
```

Web UI (local, no auth): `uv run web.py runserver`, then open http://127.0.0.1:8000.

Re-run `fetch.py` + `index.py` to pick up new mail (the newest quarter is always re-fetched).
Search is BM25 keyword search with stemming; semantic/embedding search is a possible next step.
