from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import hashlib
import csv
import io

app = Flask(__name__)
app.secret_key = "super_secret_key"

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        );
    ''')
    conn.commit()
    conn.close()

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO admins (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Email already exists.")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password)).fetchone()
        conn.close()
        if admin:
            session["user"] = email
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    conn = get_db_connection()
    if request.method == "POST":
        name = request.form.get("name")
        if name:
            conn.execute("INSERT INTO students (name) VALUES (?)", (name,))
            conn.commit()
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()
    return render_template("dashboard.html", students=students)

@app.route("/delete_student/<int:id>")
def delete_student(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/mark_attendance", methods=["POST"])
def mark_attendance():
    student_id = request.form["student_id"]
    status = request.form["status"]
    conn = get_db_connection()
    conn.execute("INSERT INTO attendance (student_id, status) VALUES (?, ?)", (student_id, status))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/edit_attendance/<int:id>", methods=["GET", "POST"])
def edit_attendance(id):
    conn = get_db_connection()
    if request.method == "POST":
        new_status = request.form["status"]
        conn.execute("UPDATE attendance SET status = ? WHERE id = ?", (new_status, id))
        conn.commit()
        conn.close()
        return redirect(url_for("report"))
    record = conn.execute("SELECT * FROM attendance WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("edit_attendance.html", record=record)

@app.route("/report", methods=["GET", "POST"])
def report():
    conn = get_db_connection()
    query = """
        SELECT a.id as aid, s.id, s.name, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
    """
    params = []
    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        if start_date and end_date:
            query += " WHERE date(a.date) BETWEEN ? AND ?"
            params = [start_date, end_date]
    query += " ORDER BY a.date DESC"
    data = conn.execute(query, params).fetchall()

    stats = {}
    for row in data:
        sid = row["id"]
        if sid not in stats:
            stats[sid] = {"name": row["name"], "present": 0, "total": 0}
        if row["status"] == "Present":
            stats[sid]["present"] += 1
        stats[sid]["total"] += 1

    for sid in stats:
        stats[sid]["percent"] = round((stats[sid]["present"] / stats[sid]["total"]) * 100, 2) if stats[sid]["total"] else 0

    conn.close()
    return render_template("report.html", data=data, stats=stats)

@app.route("/export_csv")
def export_csv():
    conn = get_db_connection()
    data = conn.execute("""
        SELECT s.name, a.date, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.date DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Date", "Status"])
    for row in data:
        writer.writerow([row["name"], row["date"], row["status"]])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="attendance.csv")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)

