import json
import csv
import io
import sqlite3
from werkzeug.security import generate_password_hash
import database
from utils import ValidationError, DuplicateRecordError, validate_email, validate_student_id, validate_name

def export_students_to_json():
    """
    Exports all database records (students, marks, attendance) to a single structured JSON string.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Get all students and associated user password hashes
    cursor.execute("""
        SELECT s.*, u.password_hash 
        FROM students s 
        JOIN users u ON s.user_id = u.id
    """)
    students_rows = cursor.fetchall()
    
    backup_data = {"students": []}
    
    for s_row in students_rows:
        student_id = s_row['student_id']
        
        # Get student's marks
        cursor.execute("SELECT subject_name, marks_obtained, max_marks FROM marks WHERE student_id = ?", (student_id,))
        marks_rows = cursor.fetchall()
        marks_list = [{'subject_name': m['subject_name'], 'marks_obtained': m['marks_obtained'], 'max_marks': m['max_marks']} for m in marks_rows]
        
        # Get student's attendance
        cursor.execute("SELECT date, status FROM attendance WHERE student_id = ?", (student_id,))
        att_rows = cursor.fetchall()
        att_list = [{'date': a['date'], 'status': a['status']} for a in att_rows]
        
        student_entry = {
            'student_id': s_row['student_id'],
            'name': s_row['name'],
            'email': s_row['email'],
            'phone': s_row['phone'],
            'department': s_row['department'],
            'year': s_row['year'],
            'dob': s_row['dob'],
            'password_hash': s_row['password_hash'],
            'marks': marks_list,
            'attendance': att_list
        }
        backup_data['students'].append(student_entry)
        
    conn.close()
    return json.dumps(backup_data, indent=2)

def export_students_to_csv():
    """
    Exports all student profiles to a CSV string.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, email, phone, department, year, dob FROM students")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['student_id', 'name', 'email', 'phone', 'department', 'year', 'dob'])
    
    # Write student details
    for r in rows:
        writer.writerow([r['student_id'], r['name'], r['email'], r['phone'] or '', r['department'], r['year'], r['dob'] or ''])
        
    return output.getvalue()

def import_students_from_json(json_content):
    """
    Imports students, marks, and attendance from a JSON backup.
    Gracefully handles duplicate accounts and invalid formats, returning success count and error lists.
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        raise ValidationError("Uploaded file is not a valid JSON document.")
        
    if 'students' not in data or not isinstance(data['students'], list):
        raise ValidationError("JSON file must contain a 'students' array.")

    success_count = 0
    errors = []
    
    conn = database.get_db_connection()
    
    for s in data['students']:
        cursor = conn.cursor()
        try:
            student_id = s.get('student_id')
            name = s.get('name')
            email = s.get('email')
            phone = s.get('phone')
            department = s.get('department')
            year = s.get('year')
            dob = s.get('dob')
            pw_hash = s.get('password_hash')
            
            if not student_id or not name or not email or not department or not year:
                raise ValidationError("Missing required student fields.")
                
            student_id = validate_student_id(student_id)
            name = validate_name(name)
            email = validate_email(email)

            # Check duplicate student_id
            cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
            if cursor.fetchone():
                raise DuplicateRecordError(f"Student ID '{student_id}' is already registered.")

            # Check duplicate email
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (email,))
            if cursor.fetchone():
                raise DuplicateRecordError(f"Email '{email}' is already taken.")

            # Start Transaction
            # Insert user record
            if not pw_hash:
                pw_hash = generate_password_hash(student_id) # default to ID if password not supplied
                
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'student')",
                (email, pw_hash)
            )
            user_id = cursor.lastrowid

            # Insert student record
            cursor.execute(
                """INSERT INTO students (student_id, user_id, name, email, phone, department, year, dob)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, user_id, name, email, phone, department, year, dob)
            )

            # Insert marks
            for m in s.get('marks', []):
                cursor.execute(
                    """INSERT INTO marks (student_id, subject_name, marks_obtained, max_marks) 
                       VALUES (?, ?, ?, ?)""",
                    (student_id, m.get('subject_name'), float(m.get('marks_obtained')), float(m.get('max_marks', 100)))
                )

            # Insert attendance
            for a in s.get('attendance', []):
                cursor.execute(
                    "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                    (student_id, a.get('date'), a.get('status'))
                )

            conn.commit()
            success_count += 1
        except Exception as e:
            conn.rollback()
            errors.append(f"Student '{s.get('student_id', 'unknown')}': {str(e)}")
            
    conn.close()
    return {'success_count': success_count, 'errors': errors}

def import_students_from_csv(csv_content):
    """
    Imports student profiles from a CSV string.
    CSV Columns: student_id, name, email, phone, department, year, dob
    Login passwords default to their student_id.
    """
    success_count = 0
    errors = []
    
    f = io.StringIO(csv_content)
    reader = csv.DictReader(f)
    
    # Verify headers
    required_headers = {'student_id', 'name', 'email', 'department', 'year'}
    if not reader.fieldnames or not required_headers.issubset(set(reader.fieldnames)):
        raise ValidationError(f"CSV file is missing one or more required columns: {required_headers}")

    conn = database.get_db_connection()
    
    for row in reader:
        cursor = conn.cursor()
        try:
            student_id = row.get('student_id')
            name = row.get('name')
            email = row.get('email')
            phone = row.get('phone', '')
            department = row.get('department')
            year = row.get('year')
            dob = row.get('dob', '')

            if not student_id or not name or not email or not department or not year:
                raise ValidationError("Row contains empty fields in required columns.")
                
            student_id = validate_student_id(student_id)
            name = validate_name(name)
            email = validate_email(email)

            # Check duplicate student_id
            cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
            if cursor.fetchone():
                raise DuplicateRecordError(f"Student ID '{student_id}' is already registered.")

            # Check duplicate email
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (email,))
            if cursor.fetchone():
                raise DuplicateRecordError(f"Email '{email}' is already in use.")

            # Insert User Login
            pw_hash = generate_password_hash(student_id)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'student')",
                (email, pw_hash)
            )
            user_id = cursor.lastrowid

            # Insert Student Profile
            cursor.execute(
                """INSERT INTO students (student_id, user_id, name, email, phone, department, year, dob)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, user_id, name, email, phone, department, year, dob)
            )

            conn.commit()
            success_count += 1
        except Exception as e:
            conn.rollback()
            errors.append(f"Row ID '{row.get('student_id', 'unknown')}': {str(e)}")
            
    conn.close()
    return {'success_count': success_count, 'errors': errors}
