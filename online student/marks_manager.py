import sqlite3
import database
from models import Mark, AttendanceRecord
from utils import (
    ValidationError, 
    RecordNotFoundError, 
    validate_marks, 
    validate_date, 
    validate_attendance_status
)

def add_or_update_marks(student_id, subject_name, marks_obtained, max_marks=100):
    """
    Adds or updates subject marks for a student. Returns created/updated Mark object.
    """
    marks_val, max_val = validate_marks(marks_obtained, max_marks)
    subject_name = subject_name.strip()
    if not subject_name:
        raise ValidationError("Subject name cannot be blank.")

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        # Verify student exists
        cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            raise RecordNotFoundError(f"Student with ID '{student_id}' does not exist.")

        cursor.execute(
            """INSERT INTO marks (student_id, subject_name, marks_obtained, max_marks)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(student_id, subject_name) 
               DO UPDATE SET marks_obtained = excluded.marks_obtained, max_marks = excluded.max_marks""",
            (student_id, subject_name, marks_val, max_val)
        )
        conn.commit()
        
        # Get inserted row id to return full object
        cursor.execute(
            "SELECT id FROM marks WHERE student_id = ? AND subject_name = ?", 
            (student_id, subject_name)
        )
        row_id = cursor.fetchone()[0]
        return Mark(row_id, student_id, subject_name, marks_val, max_val)
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database operation failed: {str(e)}")
    finally:
        conn.close()

def delete_marks(student_id, subject_name):
    """
    Deletes subject marks record for a student.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM marks WHERE student_id = ? AND subject_name = ?", (student_id, subject_name))
        if not cursor.fetchone():
            raise RecordNotFoundError(f"Marks record for subject '{subject_name}' not found for student '{student_id}'.")
            
        cursor.execute("DELETE FROM marks WHERE student_id = ? AND subject_name = ?", (student_id, subject_name))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database deletion failed: {str(e)}")
    finally:
        conn.close()

def get_student_marks(student_id):
    """
    Retrieves all subject marks, calculating totals and grades.
    Returns:
       { 'subjects': [Mark, Mark...], 'total_obtained': float, 'total_max': float, 'percentage': float, 'grade': str }
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM marks WHERE student_id = ?", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    
    marks_list = [Mark.from_row(row) for row in rows]
    total_obtained = sum(m.marks_obtained for m in marks_list)
    total_max = sum(m.max_marks for m in marks_list)
    
    percentage = (total_obtained / total_max * 100) if total_max > 0 else 0.0
    
    # Calculate overall grade
    if total_max > 0:
        if percentage >= 90: grade = 'A+'
        elif percentage >= 80: grade = 'A'
        elif percentage >= 70: grade = 'B'
        elif percentage >= 60: grade = 'C'
        elif percentage >= 50: grade = 'D'
        elif percentage >= 40: grade = 'E'
        else: grade = 'F'
    else:
        grade = 'N/A'
        
    return {
        'subjects': marks_list,
        'total_obtained': round(total_obtained, 2),
        'total_max': round(total_max, 2),
        'percentage': round(percentage, 2),
        'grade': grade
    }

def add_attendance(student_id, date, status):
    """
    Logs student attendance. Returns created/updated AttendanceRecord object.
    """
    date = validate_date(date)
    status = validate_attendance_status(status)

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        # Verify student exists
        cursor.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,))
        if not cursor.fetchone():
            raise RecordNotFoundError(f"Student with ID '{student_id}' does not exist.")

        cursor.execute(
            """INSERT INTO attendance (student_id, date, status)
               VALUES (?, ?, ?)
               ON CONFLICT(student_id, date) 
               DO UPDATE SET status = excluded.status""",
            (student_id, date, status)
        )
        conn.commit()
        
        cursor.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND date = ?", 
            (student_id, date)
        )
        row_id = cursor.fetchone()[0]
        return AttendanceRecord(row_id, student_id, date, status)
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database operation failed: {str(e)}")
    finally:
        conn.close()

def get_student_attendance(student_id):
    """
    Returns list of AttendanceRecord OOP objects.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC", (student_id,))
    rows = cursor.fetchall()
    conn.close()
    return [AttendanceRecord.from_row(row) for row in rows]

def get_attendance_summary(student_id):
    """
    Computes attendance counts and percentage.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT status, COUNT(*) as count FROM attendance WHERE student_id = ? GROUP BY status", 
        (student_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    counts = {'Present': 0, 'Absent': 0, 'Late': 0}
    total = 0
    for r in rows:
        counts[r['status']] = r['count']
        total += r['count']
        
    present_weight = counts['Present'] + (counts['Late'] * 0.5)
    attendance_rate = (present_weight / total * 100) if total > 0 else 100.0
    
    return {
        'counts': counts,
        'total': total,
        'rate': round(attendance_rate, 2)
    }

def get_dashboard_stats():
    """
    Retrieves global stats for total students, average marks, overall attendance rate, and pass/fail counts.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Total students
    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]
    
    # Average marks and pass/fail counts
    cursor.execute("SELECT student_id FROM students")
    all_student_ids = [row[0] for row in cursor.fetchall()]
    
    percentages = []
    pass_count = 0
    fail_count = 0
    
    for sid in all_student_ids:
        res = get_student_marks(sid)
        if res['total_max'] > 0:
            pct = res['percentage']
            percentages.append(pct)
            if pct >= 40:
                pass_count += 1
            else:
                fail_count += 1
        else:
            pass_count += 1 # Default neutral assumption
            
    avg_marks = round(sum(percentages) / len(percentages), 2) if percentages else 0.0
    
    # Overall attendance average
    cursor.execute("SELECT status, COUNT(*) as count FROM attendance GROUP BY status")
    status_counts = {'Present': 0, 'Absent': 0, 'Late': 0}
    total_att = 0
    for r in cursor.fetchall():
        status_counts[r['status']] = r['count']
        total_att += r['count']
        
    att_rate = 100.0
    if total_att > 0:
        present_w = status_counts['Present'] + (status_counts['Late'] * 0.5)
        att_rate = round((present_w / total_att) * 100, 2)
        
    conn.close()
    
    return {
        'total_students': total_students,
        'average_marks': avg_marks,
        'average_attendance': att_rate,
        'pass_count': pass_count,
        'fail_count': fail_count
    }

def create_announcement(title, content):
    """
    Creates a new school bulletin.
    """
    title = title.strip()
    content = content.strip()
    if not title or not content:
        raise ValidationError("Bulletin title and content cannot be empty.")

    from datetime import datetime
    date_str = datetime.now().strftime('%Y-%m-%d')

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO announcements (title, content, date_posted) VALUES (?, ?, ?)",
            (title, content, date_str)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database insertion failed: {str(e)}")
    finally:
        conn.close()

def get_all_announcements():
    """
    Retrieves all posted notices.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM announcements ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_announcement(announcement_id):
    """
    Deletes a notice.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM announcements WHERE id = ?", (announcement_id,))
        if not cursor.fetchone():
            raise RecordNotFoundError(f"Bulletin with ID '{announcement_id}' does not exist.")
            
        cursor.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValidationError(f"Database deletion failed: {str(e)}")
    finally:
        conn.close()

def get_students_at_risk_attendance(threshold=75.0):
    """
    Checks all student profiles and flags students whose attendance rate is lower than the threshold.
    """
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name, department, year FROM students")
    students = cursor.fetchall()
    conn.close()
    
    at_risk_list = []
    for s in students:
        sid = s['student_id']
        att_summary = get_attendance_summary(sid)
        if att_summary['total'] > 0 and att_summary['rate'] < threshold:
            at_risk_list.append({
                'student_id': sid,
                'name': s['name'],
                'department': s['department'],
                'year': s['year'],
                'rate': att_summary['rate'],
                'total_days': att_summary['total']
            })
            
    return at_risk_list
