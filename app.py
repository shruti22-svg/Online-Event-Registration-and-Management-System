import hashlib
import os
import re
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get(
    "EVENT_DB", os.path.join(APP_DIR, "database", "events.db")
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "event-reg-college-key")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            student_id TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'student'
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            venue TEXT NOT NULL,
            description TEXT,
            capacity INTEGER NOT NULL DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, event_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(event_id) REFERENCES events(id)
        );
        """
    )

    if db.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'").fetchone()["c"] == 0:
        db.execute(
            "INSERT INTO users (name, email, password_hash, student_id, phone, role) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "College Admin",
                "admin@college.edu",
                hash_password("admin123"),
                "ADMIN",
                "0000000000",
                "admin",
            ),
        )

    if db.execute("SELECT COUNT(*) AS c FROM users WHERE email = ?", ("student@college.edu",)).fetchone()["c"] == 0:
        db.execute(
            "INSERT INTO users (name, email, password_hash, student_id, phone, role) VALUES (?, ?, ?, ?, ?, ?)",
            (
                "Demo Student",
                "student@college.edu",
                hash_password("student123"),
                "STU1001",
                "9876543210",
                "student",
            ),
        )

    if db.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"] == 0:
        db.executemany(
            "INSERT INTO events (title, event_date, venue, description, capacity) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    "Tech Fest 2026",
                    "2026-12-10",
                    "Main Auditorium",
                    "Project expo, coding contest and guest lectures.",
                    200,
                ),
                (
                    "Cultural Night",
                    "2026-12-15",
                    "Open Air Theatre",
                    "Music, dance and drama performances.",
                    300,
                ),
                (
                    "Sports Meet",
                    "2026-12-20",
                    "College Ground",
                    "Track, field and indoor games.",
                    150,
                ),
                (
                    "AI Workshop",
                    "2026-11-28",
                    "Lab Block A",
                    "Hands-on session on basic AI tools.",
                    80,
                ),
            ],
        )
    db.commit()


with app.app_context():
    init_db()


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["role"] != "admin":
            flash("Admin login required.", "error")
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_user():
    return {"user": current_user()}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.route("/")
def home():
    events = get_db().execute(
        "SELECT * FROM events ORDER BY event_date"
    ).fetchall()
    return render_template("index.html", events=events)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    student_id = (request.form.get("student_id") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    if not name or not email or not password or not student_id or not phone:
        return render_template(
            "register.html",
            message="Please fill all fields.",
            message_type="error",
            form=request.form,
        )
    if not EMAIL_RE.match(email):
        return render_template(
            "register.html",
            message="Please enter a valid email address.",
            message_type="error",
            form=request.form,
        )
    if len(password) < 6:
        return render_template(
            "register.html",
            message="Password must be at least 6 characters.",
            message_type="error",
            form=request.form,
        )

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return render_template(
            "register.html",
            message="Duplicate registration prevented. This email is already registered.",
            message_type="error",
            form=request.form,
        )

    db.execute(
        "INSERT INTO users (name, email, password_hash, student_id, phone, role) VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, hash_password(password), student_id, phone, "student"),
    )
    db.commit()
    flash("Registration successful. Please login.", "success")
    return redirect(url_for("login", registered="1"))


@app.route("/login", methods=["GET", "POST"])
def login():
    banner = ""
    if request.args.get("registered") == "1":
        banner = "Registration successful. Please login."

    if request.method == "GET":
        return render_template("login.html", banner=banner)

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    if not email or not password:
        return render_template(
            "login.html",
            message="Please enter email and password.",
            message_type="error",
        )

    user = get_db().execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ?",
        (email, hash_password(password)),
    ).fetchone()
    if not user or user["role"] == "admin":
        return render_template(
            "login.html",
            message="Invalid email or password.",
            message_type="error",
        )

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    db = get_db()
    my_regs = db.execute(
        """
        SELECT r.id, e.title, e.event_date, e.venue
        FROM registrations r
        JOIN events e ON e.id = r.event_id
        WHERE r.user_id = ?
        ORDER BY e.event_date
        """,
        (user["id"],),
    ).fetchall()
    events = db.execute("SELECT * FROM events ORDER BY event_date").fetchall()
    return render_template("dashboard.html", my_regs=my_regs, events=events)


@app.route("/events")
def events():
    db = get_db()
    rows = db.execute(
        """
        SELECT e.*, COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON r.event_id = e.id
        GROUP BY e.id
        ORDER BY e.event_date
        """
    ).fetchall()
    return render_template("events.html", events=rows)


@app.route("/events/<int:event_id>/register", methods=["GET", "POST"])
@login_required
def event_register(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("events"))

    user = current_user()
    already = db.execute(
        "SELECT id FROM registrations WHERE user_id = ? AND event_id = ?",
        (user["id"], event_id),
    ).fetchone()

    count = db.execute(
        "SELECT COUNT(*) AS c FROM registrations WHERE event_id = ?", (event_id,)
    ).fetchone()["c"]

    if request.method == "GET":
        return render_template(
            "event_register.html",
            event=event,
            already=already,
            count=count,
        )

    if already:
        return render_template(
            "event_register.html",
            event=event,
            already=already,
            count=count,
            message="You are already registered for this event.",
            message_type="error",
        )
    if count >= event["capacity"]:
        return render_template(
            "event_register.html",
            event=event,
            already=already,
            count=count,
            message="This event is full.",
            message_type="error",
        )

    cur = db.execute(
        "INSERT INTO registrations (user_id, event_id, created_at) VALUES (?, ?, ?)",
        (user["id"], event_id, datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()
    return redirect(url_for("confirmation", registration_id=cur.lastrowid))


@app.route("/confirmation/<int:registration_id>")
@login_required
def confirmation(registration_id):
    db = get_db()
    row = db.execute(
        """
        SELECT r.id, r.created_at, u.name, u.email, u.student_id, u.phone,
               e.title, e.event_date, e.venue
        FROM registrations r
        JOIN users u ON u.id = r.user_id
        JOIN events e ON e.id = r.event_id
        WHERE r.id = ?
        """,
        (registration_id,),
    ).fetchone()
    if not row or row["email"] != current_user()["email"]:
        flash("Confirmation not found.", "error")
        return redirect(url_for("my_events"))
    return render_template("confirmation.html", record=row)


@app.route("/my-events")
@login_required
def my_events():
    db = get_db()
    rows = db.execute(
        """
        SELECT r.id AS registration_id, e.id AS event_id, e.title, e.event_date, e.venue, r.created_at
        FROM registrations r
        JOIN events e ON e.id = r.event_id
        WHERE r.user_id = ?
        ORDER BY e.event_date
        """,
        (current_user()["id"],),
    ).fetchall()
    return render_template("my_events.html", rows=rows)


@app.route("/events/<int:event_id>/participants")
def participants(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash("Event not found.", "error")
        return redirect(url_for("events"))
    people = db.execute(
        """
        SELECT u.name, u.email, u.student_id, r.created_at
        FROM registrations r
        JOIN users u ON u.id = r.user_id
        WHERE r.event_id = ?
        ORDER BY r.created_at
        """,
        (event_id,),
    ).fetchall()
    return render_template("participants.html", event=event, people=people)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    user = get_db().execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ? AND role = 'admin'",
        (email, hash_password(password)),
    ).fetchone()
    if not user:
        return render_template(
            "admin_login.html",
            message="Invalid admin credentials.",
            message_type="error",
        )
    session.clear()
    session["user_id"] = user["id"]
    session["role"] = "admin"
    return redirect(url_for("admin_dashboard"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_dashboard():
    db = get_db()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        event_date = (request.form.get("event_date") or "").strip()
        venue = (request.form.get("venue") or "").strip()
        description = (request.form.get("description") or "").strip()
        capacity = request.form.get("capacity") or "100"
        if not title or not event_date or not venue:
            flash("Title, date and venue are required.", "error")
        else:
            try:
                cap = int(capacity)
            except ValueError:
                cap = 100
            db.execute(
                "INSERT INTO events (title, event_date, venue, description, capacity) VALUES (?, ?, ?, ?, ?)",
                (title, event_date, venue, description, cap),
            )
            db.commit()
            flash("Event added.", "success")
        return redirect(url_for("admin_dashboard"))

    stats = {
        "students": db.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'student'").fetchone()["c"],
        "events": db.execute("SELECT COUNT(*) AS c FROM events").fetchone()["c"],
        "registrations": db.execute("SELECT COUNT(*) AS c FROM registrations").fetchone()["c"],
    }
    students = db.execute(
        "SELECT id, name, email, student_id, phone FROM users WHERE role = 'student' ORDER BY id"
    ).fetchall()
    events_rows = db.execute(
        """
        SELECT e.*, COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON r.event_id = e.id
        GROUP BY e.id
        ORDER BY e.event_date
        """
    ).fetchall()
    registrations = db.execute(
        """
        SELECT r.id, u.name, u.email, e.title, r.created_at
        FROM registrations r
        JOIN users u ON u.id = r.user_id
        JOIN events e ON e.id = r.event_id
        ORDER BY r.id DESC
        """
    ).fetchall()
    return render_template(
        "admin.html",
        stats=stats,
        students=students,
        events=events_rows,
        registrations=registrations,
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5002"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
