"""Local search UI: uv run web.py runserver  (then open http://127.0.0.1:8000)"""
import sqlite3
import sys
from pathlib import Path

import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import Http404
from django.shortcuts import render
from django.urls import path
from django.utils.html import escape
from django.utils.safestring import mark_safe

from search import DB, build_query

settings.configure(
    DEBUG=True,
    ALLOWED_HOSTS=["localhost", "127.0.0.1"],
    ROOT_URLCONF=__name__,
    SECRET_KEY="local-only",
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(Path(__file__).parent / "templates")],
    }],
)


def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def highlight(snip):
    return mark_safe(escape(snip).replace("\x02", "<mark>").replace("\x03", "</mark>"))


def search(request):
    q = request.GET.get("q", "").strip()
    results = []
    if q and build_query(q):
        rows = connect().execute(
            """SELECT t.id, t.subject, t.started, t.n_messages, t.url,
                      snippet(fts, 1, '\x02', '\x03', ' … ', 30) AS snip
               FROM fts JOIN threads t ON t.id = fts.rowid
               WHERE fts MATCH ? ORDER BY bm25(fts, 5.0, 1.0) LIMIT 50""",
            (build_query(q),),
        ).fetchall()
        results = [{**dict(r), "snip": highlight(r["snip"])} for r in rows]
    return render(request, "search.html", {"q": q, "results": results})


def thread(request, tid):
    db = connect()
    t = db.execute("SELECT * FROM threads WHERE id = ?", (tid,)).fetchone()
    if t is None:
        raise Http404
    msgs = db.execute("SELECT * FROM messages WHERE thread_id = ? ORDER BY date", (tid,)).fetchall()
    return render(request, "thread.html", {"t": t, "msgs": msgs})


urlpatterns = [path("", search), path("thread/<int:tid>/", thread)]

if __name__ == "__main__":
    django.setup()
    execute_from_command_line(sys.argv)
