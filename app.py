import csv
import io
import os
import uuid
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, make_response
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"

app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///soems.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
app.config["PROFILE_UPLOAD_FOLDER"] = os.path.join(app.static_folder, "uploads", "profiles")
app.config["ALLOWED_PROFILE_EXTENSIONS"] = {"jpg", "jpeg", "png", "webp"}
db.init_app(app)
login_manager.init_app(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    grade_level = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    profile_photo = db.Column(db.String(255))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    subjects = db.relationship("SubjectEnrollment", back_populates="student", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    grade_level = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    enrollments = db.relationship("SubjectEnrollment", back_populates="subject", cascade="all, delete-orphan")
    exams = db.relationship("Exam", back_populates="subject", cascade="all, delete-orphan")


class SubjectEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    student = db.relationship("User", back_populates="subjects")
    subject = db.relationship("Subject", back_populates="enrollments")


class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    exam_type = db.Column(db.String(30), nullable=False, default="MCQ")
    grade_level = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    total_marks = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    teacher = db.relationship("User", foreign_keys=[teacher_id])
    subject = db.relationship("Subject", back_populates="exams")
    questions = db.relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    attempts = db.relationship("Attempt", back_populates="exam", cascade="all, delete-orphan")


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255))
    option_b = db.Column(db.String(255))
    option_c = db.Column(db.String(255))
    option_d = db.Column(db.String(255))
    answer = db.Column(db.String(255), nullable=False)
    marks = db.Column(db.Integer, default=1)
    exam = db.relationship("Exam", back_populates="questions")


class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exam.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    exam = db.relationship("Exam", back_populates="attempts")
    student = db.relationship("User", foreign_keys=[student_id])


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access that area.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.context_processor
def inject_globals():
    return {"now": datetime.utcnow()}


@app.route("/")
def index():
    return redirect(url_for("dashboard")) if current_user.is_authenticated else redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").lower().strip()).first()
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user, remember=True)
            return redirect(url_for("dashboard"))
        flash("Check your email and password, then try again.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        if not full_name:
            flash("Full name is required.", "error")
            return render_template("profile.html", user=current_user)
        current_user.full_name = full_name
        new_password = request.form.get("password", "")
        if new_password:
            if len(new_password) < 8:
                flash("Password must be at least 8 characters.", "error")
                return render_template("profile.html", user=current_user)
            current_user.set_password(new_password)
        photo = request.files.get("profile_photo")
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in app.config["ALLOWED_PROFILE_EXTENSIONS"]:
                flash("Profile photos must be JPG, PNG, or WEBP files.", "error")
                return render_template("profile.html", user=current_user)
            os.makedirs(app.config["PROFILE_UPLOAD_FOLDER"], exist_ok=True)
            stored_name = f"user-{current_user.id}-{uuid.uuid4().hex}.{extension}"
            photo.save(os.path.join(app.config["PROFILE_UPLOAD_FOLDER"], stored_name))
            current_user.profile_photo = f"uploads/profiles/{stored_name}"
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=current_user)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "admin":
        stats = {"users": User.query.count(), "teachers": User.query.filter_by(role="teacher").count(), "students": User.query.filter_by(role="student").count(), "subjects": Subject.query.count(), "exams": Exam.query.count()}
        return render_template("dashboard.html", stats=stats, recent_exams=Exam.query.order_by(Exam.created_at.desc()).limit(5).all())
    if current_user.role == "teacher":
        exams = Exam.query.filter_by(teacher_id=current_user.id).order_by(Exam.created_at.desc()).all()
        attempts = Attempt.query.join(Exam).filter(Exam.teacher_id == current_user.id).all()
        average = round(sum(a.score for a in attempts) / len(attempts)) if attempts else 0
        stats = {"exams": len(exams), "active": sum(e.is_active for e in exams), "participation": len(attempts), "average": average}
        return render_template("dashboard.html", stats=stats, teacher_exams=exams)
    enrolled_ids = [entry.subject_id for entry in current_user.subjects]
    available = Exam.query.filter(Exam.is_active.is_(True), Exam.grade_level == current_user.grade_level, Exam.subject_id.in_(enrolled_ids or [0])).all()
    attempts = Attempt.query.filter_by(student_id=current_user.id).order_by(Attempt.submitted_at.desc()).all()
    return render_template("dashboard.html", available_exams=available, attempts=attempts)


@app.route("/exams")
@login_required
def exams():
    if current_user.role == "student":
        return redirect(url_for("dashboard"))
    query = Exam.query if current_user.role == "admin" else Exam.query.filter_by(teacher_id=current_user.id)
    return render_template("exams.html", exams=query.order_by(Exam.created_at.desc()).all(), subjects=Subject.query.all())


@app.route("/exams/new", methods=["GET", "POST"])
@role_required("admin", "teacher")
def create_exam():
    if request.method == "POST":
        exam = Exam(title=request.form["title"], exam_type=request.form["exam_type"], grade_level=int(request.form["grade_level"]), subject_id=int(request.form["subject_id"]), description=request.form.get("description"), instructions=request.form.get("instructions"), duration_minutes=int(request.form["duration_minutes"]), teacher_id=current_user.id if current_user.role == "teacher" else int(request.form.get("teacher_id") or current_user.id))
        db.session.add(exam)
        db.session.commit()
        flash("Exam created. Add questions whenever you are ready.", "success")
        return redirect(url_for("exam_detail", exam_id=exam.id))
    return render_template("exam_form.html", subjects=Subject.query.all(), teachers=User.query.filter_by(role="teacher", is_active=True).all())


def can_manage_exam(exam):
    return current_user.role == "admin" or (current_user.role == "teacher" and exam.teacher_id == current_user.id)


@app.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@role_required("admin", "teacher")
def edit_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    if not can_manage_exam(exam):
        flash("You can only manage exams assigned to you.", "error")
        return redirect(url_for("exams"))
    if request.method == "POST":
        exam.title = request.form["title"]
        exam.exam_type = request.form["exam_type"]
        exam.grade_level = int(request.form["grade_level"])
        exam.subject_id = int(request.form["subject_id"])
        exam.description = request.form.get("description")
        exam.instructions = request.form.get("instructions")
        exam.duration_minutes = int(request.form["duration_minutes"])
        if current_user.role == "admin":
            exam.teacher_id = int(request.form.get("teacher_id") or exam.teacher_id)
        db.session.commit()
        flash("Exam updated successfully.", "success")
        return redirect(url_for("exam_detail", exam_id=exam.id))
    return render_template("exam_form.html", exam=exam, subjects=Subject.query.all(), teachers=User.query.filter_by(role="teacher", is_active=True).all())


@app.post("/exams/<int:exam_id>/delete")
@role_required("admin", "teacher")
def delete_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    if not can_manage_exam(exam):
        flash("You can only manage exams assigned to you.", "error")
        return redirect(url_for("exams"))
    db.session.delete(exam)
    db.session.commit()
    flash("Exam deleted.", "success")
    return redirect(url_for("exams"))


@app.post("/exams/<int:exam_id>/toggle")
@role_required("admin", "teacher")
def toggle_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    if not can_manage_exam(exam):
        flash("You can only manage exams assigned to you.", "error")
        return redirect(url_for("exams"))
    exam.is_active = not exam.is_active
    db.session.commit()
    flash(f"Exam {'activated' if exam.is_active else 'deactivated'}.", "success")
    return redirect(url_for("exams"))


@app.route("/exams/<int:exam_id>")
@login_required
def exam_detail(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    return render_template("exam_detail.html", exam=exam)


@app.route("/exams/<int:exam_id>/take", methods=["GET", "POST"])
@role_required("student")
def take_exam(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    eligible = exam.is_active and exam.grade_level == current_user.grade_level and any(item.subject_id == exam.subject_id for item in current_user.subjects)
    if not eligible:
        flash("This exam is not assigned to your grade and enrolled subjects.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        score = 0
        for question in exam.questions:
            response = request.form.get(f"question_{question.id}", "").strip().lower()
            if response == question.answer.strip().lower():
                score += question.marks
        attempt = Attempt(exam=exam, student=current_user, score=score)
        db.session.add(attempt)
        db.session.commit()
        return render_template("result.html", attempt=attempt, exam=exam)
    return render_template("take_exam.html", exam=exam)


@app.route("/questions/<int:exam_id>/import", methods=["POST"])
@role_required("admin", "teacher")
def import_questions(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    upload = request.files.get("file")
    if not upload:
        flash("Choose a CSV file first.", "error")
        return redirect(url_for("exam_detail", exam_id=exam.id))
    rows = csv.DictReader(io.StringIO(upload.stream.read().decode("utf-8-sig")))
    for row in rows:
        db.session.add(Question(exam=exam, prompt=row["prompt"], option_a=row.get("option_a"), option_b=row.get("option_b"), option_c=row.get("option_c"), option_d=row.get("option_d"), answer=row["answer"], marks=int(row.get("marks") or 1)))
    db.session.commit()
    flash("Questions imported successfully.", "success")
    return redirect(url_for("exam_detail", exam_id=exam.id))


@app.route("/exams/<int:exam_id>/export")
@login_required
def export_questions(exam_id):
    exam = db.get_or_404(Exam, exam_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["prompt", "option_a", "option_b", "option_c", "option_d", "answer", "marks"])
    for question in exam.questions:
        writer.writerow([question.prompt, question.option_a, question.option_b, question.option_c, question.option_d, question.answer, question.marks])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={exam.title.replace(' ', '_')}_questions.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@app.route("/subjects")
@role_required("admin", "teacher")
def subjects():
    return render_template("subjects.html", subjects=Subject.query.order_by(Subject.grade_level, Subject.name).all())


@app.get("/subjects/<int:subject_id>")
@role_required("admin", "teacher")
def subject_detail(subject_id):
    return render_template("subject_detail.html", subject=db.get_or_404(Subject, subject_id))


@app.route("/subjects/new", methods=["GET", "POST"])
@role_required("admin")
def create_subject():
    if request.method == "POST":
        subject = Subject(name=request.form["name"], code=request.form["code"].upper(), grade_level=int(request.form["grade_level"]), description=request.form.get("description"))
        db.session.add(subject)
        db.session.commit()
        flash("Subject created.", "success")
        return redirect(url_for("subjects"))
    return render_template("subject_form.html")


@app.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    if request.method == "POST":
        subject.name = request.form["name"]
        subject.code = request.form["code"].upper()
        subject.grade_level = int(request.form["grade_level"])
        subject.description = request.form.get("description")
        db.session.commit()
        flash("Subject updated.", "success")
        return redirect(url_for("subjects"))
    return render_template("subject_form.html", subject=subject)


@app.post("/subjects/<int:subject_id>/delete")
@role_required("admin")
def delete_subject(subject_id):
    subject = db.get_or_404(Subject, subject_id)
    if subject.exams:
        flash("Move or delete this subject's exams before deleting the subject.", "error")
        return redirect(url_for("subjects"))
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted.", "success")
    return redirect(url_for("subjects"))


@app.route("/users")
@role_required("admin")
def users():
    return render_template("users.html", users=User.query.order_by(User.full_name).all())


@app.get("/users/<int:user_id>")
@role_required("admin")
def user_detail(user_id):
    return render_template("user_detail.html", user=db.get_or_404(User, user_id))


@app.route("/users/new", methods=["GET", "POST"])
@role_required("admin")
def create_user():
    if request.method == "POST":
        user = User(full_name=request.form["full_name"], email=request.form["email"].lower().strip(), role=request.form["role"], grade_level=int(request.form["grade_level"]) if request.form.get("grade_level") else None)
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("users"))
    return render_template("user_form.html")


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    if request.method == "POST":
        user.full_name = request.form["full_name"]
        user.email = request.form["email"].lower().strip()
        user.role = request.form["role"]
        user.grade_level = int(request.form["grade_level"]) if request.form.get("grade_level") else None
        if request.form.get("password"):
            user.set_password(request.form["password"])
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("users"))
    return render_template("user_form.html", user=user)


@app.post("/users/<int:user_id>/delete")
@role_required("admin")
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot delete your own administrator account.", "error")
        return redirect(url_for("users"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("users"))


@app.post("/users/<int:user_id>/toggle")
@role_required("admin")
def toggle_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("users"))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"User {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("users"))


def seed_data():
    if User.query.first():
        return
    admin = User(full_name="Amina Okafor", email="admin@soems.local", role="admin")
    teacher = User(full_name="Daniel Mensah", email="teacher@soems.local", role="teacher")
    student = User(full_name="Maya Patel", email="student@soems.local", role="student", grade_level=8)
    for user in (admin, teacher, student):
        user.set_password("password123")
        db.session.add(user)
    math = Subject(name="Mathematics", code="MATH-08", grade_level=8, description="Core mathematics for Grade 8 learners.")
    science = Subject(name="Integrated Science", code="SCI-08", grade_level=8, description="Exploring the living and physical world.")
    db.session.add_all([math, science])
    db.session.flush()
    db.session.add(SubjectEnrollment(student=student, subject=math))
    exam = Exam(title="Algebra Foundations", exam_type="MCQ", grade_level=8, subject=math, description="A focused check of algebraic thinking.", instructions="Read each question carefully. You have one attempt.", duration_minutes=15, teacher=teacher, total_marks=3)
    db.session.add(exam)
    db.session.flush()
    db.session.add_all([Question(exam=exam, prompt="What is 3x when x = 4?", option_a="7", option_b="12", option_c="1", option_d="34", answer="12"), Question(exam=exam, prompt="Which expression equals 2(x + 3)?", option_a="2x + 3", option_b="x + 6", option_c="2x + 6", option_d="2x + 5", answer="2x + 6"), Question(exam=exam, prompt="What is the value of 10 - 2²?", option_a="6", option_b="16", option_c="8", option_d="4", answer="6")])
    db.session.commit()


with app.app_context():
    os.makedirs(app.instance_path, exist_ok=True)
    db.create_all()
    seed_data()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
