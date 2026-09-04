# SOEMS Workspace Notes

- Flask entry point: `app.py`
- Run locally with `python app.py` after installing `requirements.txt`.
- Keep role authorization server-side using the existing `role_required` decorator.
- SQLite is the local default; production uses `DATABASE_URL` for MySQL compatibility.
- Preserve the existing Bootstrap-compatible responsive visual system in `static/css/app.css`.
