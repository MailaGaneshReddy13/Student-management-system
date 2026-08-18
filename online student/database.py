import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'school.db')

def get_db_connection():
    """
    Establish a connection to the SQLite database.
    Configures Row factory and enables foreign key constraints.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """
    Initializes database tables, creates necessary search indices, 
    and seeds a default administrator account.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table (Authentication and Role details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student'))
        )
    ''')

    # Students Table (Personal Profile details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            department TEXT NOT NULL,
            year TEXT NOT NULL,
            dob TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Marks Table (Subject Scores details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL DEFAULT 100,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(student_id, subject_name)
        )
    ''')

    # Attendance Table (Daily logs details)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            UNIQUE(student_id, date)
        )
    ''')

    # Announcements Table (General broadcasts/notices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            date_posted TEXT NOT NULL
        )
    ''')

    # Indices optimization
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department)')

    # Seed Default Admin account
    cursor.execute("SELECT * FROM users WHERE username = 'admin@school.com'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ('admin@school.com', hashed_pw, 'admin')
        )
        conn.commit()

    conn.close()
