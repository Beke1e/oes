# Smart Online Examination Management System (SOEMS)

SOEMS is a Flask-based examination platform for administrators, teachers, and learners in elementary schools, high schools, colleges, and universities. It provides role-aware tools for creating, delivering, and evaluating exams across different educational levels.

## Included in this starter

- Secure password hashing and Flask-Login authentication
- Role-aware Administrator, Teacher, and Student dashboards
- Exam access based on active status and student grade level
- Support for elementary, high school, college, and university examination programs
- Exam builder with MCQ, True/False, and Fill in the Blank types
- Countdown timer with browser auto-submit and server-side instant scoring
- CSV question import and export
- SQLite by default, with MySQL-compatible `DATABASE_URL`
- Responsive Bootstrap-compatible UI, Font Awesome icons, and light/dark mode
- Seeded demo accounts and sample Grade 8 Mathematics exam

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`.

Demo password for all accounts is `password123`:

- `admin@soems.local`
- `teacher@soems.local`
- `student@soems.local`

The SQLite database is created at `instance/soems.db` on first launch. To reset demo data, stop the app and delete that file.

## CSV question format

Question imports support UTF-8 (including files with a BOM) and Windows-1252 CSV files.

```csv
prompt,option_a,option_b,option_c,option_d,answer,marks
What is 2 + 2?,3,4,5,6,4,1
```

## MySQL and PythonAnywhere

Set the following environment variables in the PythonAnywhere web app configuration or WSGI environment:

```text
SECRET_KEY=use-a-long-random-value
DATABASE_URL=mysql+pymysql://username:password@hostname/database_name
FLASK_DEBUG=0
```

Set the WSGI entry point to:

```python
import sys
sys.path.insert(0, '/home/yourusername/oes')
from app import app as application
```

For production, keep `FLASK_DEBUG=0`, use a unique secret key, and serve uploaded profile files from a configured storage location.

## Next production increments

The current foundation is intentionally compact. The next modules to add are full CRUD forms for users/subjects, notification persistence, profile photo upload validation, PDF export, analytics charts, CSRF protection with Flask-WTF, and audit logging.
