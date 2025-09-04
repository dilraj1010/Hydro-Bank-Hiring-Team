import os
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, abort
)
from werkzeug.utils import secure_filename

# ---------- Config ----------
BASE_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOAD_FOLDER = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "applications.db"

# NOTE: For security, it's highly recommended to use environment variables for credentials.
# For example: os.environ.get("ADMIN_USER")
ADMIN_USER = "hydro_72"
ADMIN_PASS = "P__72__@42__1010"
SECRET_KEY = "##00--00#72BX--1010X-5Hydro-Water"

ALLOWED_EXT = {"pdf", "doc", "docx"}
MAX_CONTENT_LENGTH = 3 * 1024 * 1024  # 3 MB

# ---------- Flask App ----------
app = Flask(__name__, template_folder=str(TEMPLATES_DIR))
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.secret_key = SECRET_KEY

# Ensure folders exist
UPLOAD_FOLDER.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# ---------- DB Helpers ----------
def init_db():
    """Initializes the database and creates the applicants table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        whatsapp TEXT,
        role TEXT,
        skills TEXT,
        portfolio TEXT,
        message TEXT,
        resume_filename TEXT,
        submitted_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_applicant(data):
    """Inserts a new applicant's data into the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applicants
        (name, email, whatsapp, role, skills, portfolio, message, resume_filename, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("email"),
        data.get("whatsapp"),
        data.get("role"),
        data.get("skills"),
        data.get("portfolio"),
        data.get("message"),
        data.get("resume_filename"),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def get_all_applicants():
    """Fetches all applicant records from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, email, whatsapp, role, skills, portfolio, message, resume_filename, submitted_at FROM applicants ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    keys = ["id", "name", "email", "whatsapp", "role", "skills", "portfolio", "message", "resume_filename", "submitted_at"]
    return [dict(zip(keys, row)) for row in rows]

def get_applicant(app_id):
    """Fetches a single applicant record by ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, email, whatsapp, role, skills, portfolio, message, resume_filename, submitted_at FROM applicants WHERE id=?", (app_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id", "name", "email", "whatsapp", "role", "skills", "portfolio", "message", "resume_filename", "submitted_at"]
    return dict(zip(keys, row))

def delete_applicant(app_id):
    """Deletes an applicant record and their associated resume file."""
    ap = get_applicant(app_id)
    if ap and ap["resume_filename"]:
        fpath = UPLOAD_FOLDER / ap["resume_filename"]
        if fpath.exists():
            fpath.unlink()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM applicants WHERE id=?", (app_id,))
    conn.commit()
    conn.close()

# ---------- Utilities ----------
def allowed_file(filename):
    """Checks if a file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ---------- Public Routes ----------
@app.route("/")
def home():
    """Renders the public homepage."""
    return render_template("index.html")

@app.route("/about")
def about():
    """Renders the about page."""
    return render_template("about.html")

@app.route("/faq")
def faq():
    """Renders the FAQ page."""
    return render_template("faq.html")

@app.route("/careers")
def careers():
    """Renders the careers page."""
    return render_template("careers.html")

@app.route("/apply", methods=["POST"])
def apply():
    """Handles new job application submissions."""
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()
    role = request.form.get("role", "").strip()
    skills = request.form.get("skills", "").strip()
    portfolio = request.form.get("portfolio", "").strip()
    message = request.form.get("message", "").strip()
    nda = request.form.get("nda", None)

    if not name or not email or not role:
        flash("Please fill required fields (name, email, role).", "error")
        return redirect(request.referrer or url_for("careers"))
    if not nda:
        flash("Please accept the NDA to proceed.", "error")
        return redirect(request.referrer or url_for("careers"))

    saved_filename = None
    file = request.files.get("resume")
    if file and file.filename:
        if not allowed_file(file.filename):
            flash("Invalid file type. Only PDF/DOC/DOCX allowed.", "error")
            return redirect(request.referrer or url_for("careers"))
        filename = secure_filename(file.filename)
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        filename = f"{ts}_{filename}"
        dest = UPLOAD_FOLDER / filename
        file.save(str(dest))
        saved_filename = filename

    insert_applicant({
        "name": name,
        "email": email,
        "whatsapp": whatsapp,
        "role": role,
        "skills": skills,
        "portfolio": portfolio,
        "message": message,
        "resume_filename": saved_filename
    })

    flash("Application submitted. We'll contact you soon.", "success")
    return redirect(url_for("careers"))

# ---------- Admin Routes ----------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serves uploaded files to logged-in admins."""
    if not session.get("admin_logged_in"):
        abort(403)
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Handles admin login."""
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials", "error")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    """Logs the admin out."""
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin_dashboard():
    """Displays the admin dashboard with applicant data."""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    applicants = get_all_applicants()
    return render_template("admin_dashboard.html", applicants=applicants)

@app.route("/admin/delete/<int:app_id>", methods=["POST"])
def admin_delete(app_id):
    """Deletes an applicant from the database and storage."""
    if not session.get("admin_logged_in"):
        abort(403)
    delete_applicant(app_id)
    flash("Application deleted.", "success")
    return redirect(url_for("admin_dashboard"))

# ---------- Start ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)