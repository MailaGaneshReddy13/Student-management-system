import sqlite3
import database
from models import Student
import auth
from utils import (
    ValidationError, 
    DuplicateRecordError, 
    RecordNotFoundError, 
    validate_email, 
    validate_student_id, 
    validate_name, 
    validate_date
)

def create_student(student_id, name, email, phone, department, year, dob, password):
    """
    Creates a new student record and login credentials.
    Raises DuplicateRecordError if ID or email exists. Returns the created Student object.
    """
    # Validation
    student_id = validate_student_id(student_id)
    name = validate_name(name)
    email = validate_email(email)
    dob = validate_date(dob)

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        # Check duplicate student_id
        cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
        if cursor.fetchone():
            raise DuplicateRecordError(f"Student ID '{student_id}' is already registered.")

        # Check duplicate email
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (email,))
        if cursor.fetchone():
            raise DuplicateRecordError(f"Email address '{email}' is already in use.")

        # Insert user login (auth module handles password hashing)
        user_id = auth.create_user_record(cursor, email, password, role='student')

        # Insert student record
        cursor.execute(
            """INSERT INTO students (student_id, user_id, name, email, phone, department, year, dob)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, user_id, name, email, phone, department, year, dob)
        )
        conn.commit()
        
        # Return student object
        return Student(student_id, user_id, name, email, phone, department, year, dob)
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database insertion failed: {str(e)}")
    finally:
        conn.close()

def get_all_students(search_query=None, department=None, year=None):
    """
    Returns a list of Student OOP objects matching optional filters.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (name LIKE ? OR student_id LIKE ? OR email LIKE ?)"
        like_expr = f"%{search_query}%"
        params.extend([like_expr, like_expr, like_expr])
        
    if department:
        query += " AND department = ?"
        params.append(department)
        
    if year:
        query += " AND year = ?"
        params.append(year)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [Student.from_row(row) for row in rows]

def get_student_by_id(student_id):
    """
    Retrieves student by ID. Raises RecordNotFoundError if missing.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise RecordNotFoundError(f"Student with ID '{student_id}' does not exist.")
    return Student.from_row(row)

def get_student_by_user_id(user_id):
    """
    Retrieves student by associated User ID. Raises RecordNotFoundError if missing.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise RecordNotFoundError(f"Student record associated with User ID '{user_id}' does not exist.")
    return Student.from_row(row)

def update_student(student_id, name, email, phone, department, year, dob):
    """
    Updates student record. Raises RecordNotFoundError if missing or DuplicateRecordError if email is taken.
    """
    name = validate_name(name)
    email = validate_email(email)
    dob = validate_date(dob)

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, email FROM students WHERE student_id = ?", (student_id,))
        record = cursor.fetchone()
        if not record:
            raise RecordNotFoundError(f"Student with ID '{student_id}' not found.")
            
        user_id = record['user_id']
        old_email = record['email']
        
        # Check duplicate email on other accounts
        if old_email != email:
            cursor.execute("SELECT 1 FROM users WHERE username = ? AND id != ?", (email, user_id))
            if cursor.fetchone():
                raise DuplicateRecordError(f"Email '{email}' is already in use by another user.")
        
        # Update user login
        cursor.execute("UPDATE users SET username = ? WHERE id = ?", (email, user_id))
        
        # Update student record
        cursor.execute(
            """UPDATE students 
               SET name = ?, email = ?, phone = ?, department = ?, year = ?, dob = ?
               WHERE student_id = ?""",
            (name, email, phone, department, year, dob, student_id)
        )
        conn.commit()
        return Student(student_id, user_id, name, email, phone, department, year, dob)
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database update failed: {str(e)}")
    finally:
        conn.close()

def update_student_profile(student_id, phone):
    """
    Allows updating limited profile details (phone number).
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        # Check student exists
        cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            raise RecordNotFoundError(f"Student with ID '{student_id}' not found.")
            
        cursor.execute("UPDATE students SET phone = ? WHERE student_id = ?", (phone, student_id))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Profile update failed: {str(e)}")
    finally:
        conn.close()

def delete_student(student_id):
    """
    Deletes student and user logins. Raises RecordNotFoundError if missing.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM students WHERE student_id = ?", (student_id,))
        row = cursor.fetchone()
        if not row:
            raise RecordNotFoundError(f"Student with ID '{student_id}' not found.")
        
        user_id = row['user_id']
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Deletion failed: {str(e)}")
    finally:
        conn.close()
