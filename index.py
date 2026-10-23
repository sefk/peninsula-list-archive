"""Parse data/raw/*.mbox into threads and build a SQLite FTS5 index (data/peninsula.db)."""
import email
import mailbox
import re
import sqlite3
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "peninsula.db"
BASE = "https://www.employees.org/mailman/private/peninsula/"

SCHEMA = """
CREATE TABLE threads (id INTEGER PRIMARY KEY, subject TEXT, started TEXT,
                      quarter TEXT, n_messages INTEGER, url TEXT);
CREATE TABLE messages (id INTEGER PRIMARY KEY, thread_id INTEGER, msgid TEXT,
                       author TEXT, date TEXT, body TEXT);
CREATE VIRTUAL TABLE fts USING fts5(subject, body, tokenize='porter unicode61');
"""


def norm_subject(s):
    s = re.sub(r"\[Peninsula\]", "", s or "", flags=re.I)
    while True:
        t = re.sub(r"^\s*(re|fwd?)\s*:\s*", "", s, flags=re.I)
        if t == s:
            break
        s = t
    return re.sub(r"\s+", " ", s).strip()


def clean_body(text):
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith(">"):
            continue
        if line.rstrip("\r") == "-- ":
            break
        if re.match(r"^On .+(wrote|said):\s*$", line):
            continue
        out.append(line)
    # Drop Mailman footer, if present
    text = "\n".join(out)
    text = re.split(r"\n_{10,}\nPeninsula mailing list", text)[0]
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def deobfuscate(addr):
    return re.sub(r" at ", "@", addr or "")


def get_body(msg):
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        return part.get_content()
    except Exception:
        return ""


def load():
    msgs = []
    for path in sorted(RAW.glob("*.mbox")):
        q = path.stem
        box = mailbox.mbox(str(path), factory=lambda f: email.message_from_binary_file(f, policy=policy.default))
        for m in box:
            try:
                dt = parsedate_to_datetime(str(m["Date"])).isoformat()
            except Exception:
                dt = ""
            ids = re.findall(r"<[^>]+>", str(m["References"] or "") + " " + str(m["In-Reply-To"] or ""))
            msgs.append({
                "msgid": (re.findall(r"<[^>]+>", str(m["Message-ID"] or "")) or [None])[0],
                "refs": ids,
                "subject": str(m["Subject"] or ""),
                "author": deobfuscate(str(m["From"] or "")),
                "date": dt,
                "quarter": q,
                "body": clean_body(get_body(m)),
            })
    return msgs


def thread(msgs):
    """Union-find over message-id references, then merge by normalized subject within 120 days."""
    parent = list(range(len(msgs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_id = {m["msgid"]: i for i, m in enumerate(msgs) if m["msgid"]}
    for i, m in enumerate(msgs):
        for r in m["refs"]:
            if r in by_id:
                union(i, by_id[r])
    # Subject fallback for replies whose parent is missing
    last = {}
    for i in sorted(range(len(msgs)), key=lambda i: msgs[i]["date"]):
        subj = norm_subject(msgs[i]["subject"]).lower()
        if not subj:
            continue
        prev = last.get(subj)
        if prev is not None and re.match(r"\s*re\s*:", msgs[i]["subject"], re.I):
            union(i, prev)
        last[subj] = i
    groups = {}
    for i in range(len(msgs)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def main():
    msgs = load()
    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    groups = thread(msgs)
    for idxs in groups:
        idxs.sort(key=lambda i: msgs[i]["date"])
        first = msgs[idxs[0]]
        subject = norm_subject(first["subject"])
        cur = db.execute(
            "INSERT INTO threads (subject, started, quarter, n_messages, url) VALUES (?,?,?,?,?)",
            (subject, first["date"], first["quarter"], len(idxs), f"{BASE}{first['quarter']}/thread.html"),
        )
        tid = cur.lastrowid
        bodies = []
        for i in idxs:
            m = msgs[i]
            db.execute(
                "INSERT INTO messages (thread_id, msgid, author, date, body) VALUES (?,?,?,?,?)",
                (tid, m["msgid"], m["author"], m["date"], m["body"]),
            )
            bodies.append(m["body"])
        db.execute("INSERT INTO fts (rowid, subject, body) VALUES (?,?,?)", (tid, subject, "\n\n".join(bodies)))
    db.commit()
    print(f"{len(msgs)} messages, {len(groups)} threads -> {DB}")


if __name__ == "__main__":
    main()
