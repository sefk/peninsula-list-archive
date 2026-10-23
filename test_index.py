from index import clean_body, norm_subject, thread


def test_norm_subject():
    assert norm_subject("Re: [Peninsula] Re: Fence help") == "Fence help"


def test_clean_body():
    text = "Try Bob.\n\nOn Mon, Jan 1, Al wrote:\n> fence?\n-- \nsig"
    assert clean_body(text) == "Try Bob."


def test_thread_by_references():
    msgs = [
        {"msgid": "<a>", "refs": [], "subject": "Fence", "date": "2020-01-01"},
        {"msgid": "<b>", "refs": ["<a>"], "subject": "Re: Fence", "date": "2020-01-02"},
        {"msgid": "<c>", "refs": [], "subject": "Other", "date": "2020-01-03"},
    ]
    assert sorted(map(sorted, thread(msgs))) == [[0, 1], [2]]
