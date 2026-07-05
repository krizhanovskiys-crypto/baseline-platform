"""Presenters — pure view-building functions.

A presenter takes already-fetched data (never a session, never Bot,
never touches I/O) and returns the text/keyboard a screen should show.
Handlers stay responsible for orchestration (fetch data, decide
whether a side effect like auto-close or a notification is needed,
send the result); presenters stay responsible only for "given this
data, what does the screen look like." This keeps handlers free of
view-assembly logic without moving business decisions out of the
service layer — a presenter never queries a repository or decides
permissions itself, it only renders what it's handed.
"""
