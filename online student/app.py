from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from functools import wraps
import os
import database
import auth
import student_manager
import marks_manager
import file_handler
from utils import SchoolSystemError, ValidationError, DuplicateRecordError, RecordNotFoundError
import gemini_assistant

# Load environment variables from .env manually to avoid library dependency
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ[key.strip()] = val.strip()

load_env()

app = Flask(__name__)
app.secret_key = 'super-secret-school-key-for-session-management'

# Initialize database schemas
database.init_db()

# Decorators for Role-Based Access Control
def login_required(f):
    @wraps(f)
    def decorated_function(*a, **kw):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*a, **kw)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*a, **kw):
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'success': False, 'message': 'Admin privilege required.'}), 403
        return f(*a, **kw)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*a, **kw):
        if 'user_id' not in session or session.get('role') != 'student':
            return jsonify({'success': False, 'message': 'Student privilege required.'}), 403
        return f(*a, **kw)
    return decorated_function

# Error handlers for APIs
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify({'success': False, 'message': str(e)}), 400

@app.errorhandler(DuplicateRecordError)
def handle_duplicate_error(e):
    return jsonify({'success': False, 'message': str(e)}), 400

@app.errorhandler(RecordNotFoundError)
def handle_not_found_error(e):
    return jsonify({'success': False, 'message': str(e)}), 404

@app.errorhandler(SchoolSystemError)
def handle_system_error(e):
    return jsonify({'success': False, 'message': str(e)}), 400

# Pages / Views Routes

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('student_dashboard'))
    return render_template('admin_dashboard.html', username=session.get('username'))

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('admin_dashboard'))
    
    try:
        student = student_manager.get_student_by_user_id(session.get('user_id'))
        return render_template('student_dashboard.html', student=student.to_dict())
    except RecordNotFoundError:
        session.clear()
        return redirect(url_for('login_page'))

# Authentication APIs

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    try:
        user = auth.authenticate_user(username, password)
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'role': user.role
        })
    except (ValidationError, RecordNotFoundError) as e:
        return jsonify({'success': False, 'message': str(e)}), 401

@app.route('/api/auth/register', methods=['POST'])
def api_register_student():
    data = request.json or {}
    student_id = data.get('student_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    department = data.get('department')
    year = data.get('year')
    dob = data.get('dob')
    password = data.get('password')
    
    if not password:
        return jsonify({'success': False, 'message': 'Password is required.'}), 400
        
    student = student_manager.create_student(
        student_id=student_id, name=name, email=email, phone=phone,
        department=department, year=year, dob=dob, password=password
    )
    return jsonify({'success': True, 'message': f"Student '{student.name}' registered successfully."})

@app.route('/api/auth/register-admin', methods=['POST'])
def api_register_admin():
    """Register a new admin account via the sign-up form."""
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Name, email and password are required.'}), 400

    conn = database.get_db_connection()
    cursor = conn.cursor()
    try:
        # Use auth module to create the user record with role='admin'
        auth.create_user_record(cursor, email, password, role='admin')
        conn.commit()
        return jsonify({'success': True, 'message': f"Admin account for '{name}' created successfully."})
    except (ValidationError, DuplicateRecordError) as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    if request.method == 'POST':
        return jsonify({'success': True, 'message': 'Logged out successfully.'})
    return redirect(url_for('login_page'))

# Student API (Self Profile Management)

@app.route('/api/student/profile', methods=['PUT'])
@login_required
@student_required
def api_update_own_profile():
    data = request.json or {}
    phone = data.get('phone')
    
    student = student_manager.get_student_by_user_id(session.get('user_id'))
    student_manager.update_student_profile(student.student_id, phone)
    return jsonify({'success': True, 'message': 'Profile updated successfully.'})

@app.route('/api/student/marks', methods=['GET'])
@login_required
@student_required
def api_get_own_marks():
    student = student_manager.get_student_by_user_id(session.get('user_id'))
    res = marks_manager.get_student_marks(student.student_id)
    
    # Serialize Mark OOP objects to dict
    serialized_subjects = [m.to_dict() for m in res['subjects']]
    res['subjects'] = serialized_subjects
    return jsonify({'success': True, 'data': res})

@app.route('/api/student/attendance', methods=['GET'])
@login_required
@student_required
def api_get_own_attendance():
    student = student_manager.get_student_by_user_id(session.get('user_id'))
    logs = marks_manager.get_student_attendance(student.student_id)
    summary = marks_manager.get_attendance_summary(student.student_id)
    
    serialized_logs = [log.to_dict() for log in logs]
    return jsonify({
        'success': True,
        'data': {
            'logs': serialized_logs,
            'summary': summary
        }
    })

# Admin APIs (Student CRUD & Management)

@app.route('/api/admin/students', methods=['GET'])
@login_required
@admin_required
def api_admin_list_students():
    search = request.args.get('search')
    dept = request.args.get('department')
    year = request.args.get('year')
    
    students = student_manager.get_all_students(search_query=search, department=dept, year=year)
    return jsonify({'success': True, 'data': [s.to_dict() for s in students]})

@app.route('/api/admin/students', methods=['POST'])
@login_required
@admin_required
def api_admin_create_student():
    data = request.json or {}
    student_id = data.get('student_id')
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    department = data.get('department')
    year = data.get('year')
    dob = data.get('dob')
    password = data.get('password')
    
    if not password:
        password = student_id # default password to student_id
        
    student = student_manager.create_student(
        student_id=student_id, name=name, email=email, phone=phone,
        department=department, year=year, dob=dob, password=password
    )
    return jsonify({'success': True, 'message': f"Student '{student.name}' registered successfully."})

@app.route('/api/admin/students/<student_id>', methods=['GET'])
@login_required
@admin_required
def api_admin_get_student(student_id):
    student = student_manager.get_student_by_id(student_id)
    return jsonify({'success': True, 'data': student.to_dict()})

@app.route('/api/admin/students/<student_id>', methods=['PUT'])
@login_required
@admin_required
def api_admin_update_student(student_id):
    data = request.json or {}
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    department = data.get('department')
    year = data.get('year')
    dob = data.get('dob')
    
    student = student_manager.update_student(
        student_id=student_id, name=name, email=email, phone=phone,
        department=department, year=year, dob=dob
    )
    return jsonify({'success': True, 'message': f"Student '{student.name}' updated successfully."})

@app.route('/api/admin/students/<student_id>', methods=['DELETE'])
@login_required
@admin_required
def api_admin_delete_student(student_id):
    student_manager.delete_student(student_id)
    return jsonify({'success': True, 'message': 'Student record and login account deleted successfully.'})

# Admin APIs (Marks Management)

@app.route('/api/admin/students/<student_id>/marks', methods=['GET'])
@login_required
@admin_required
def api_admin_get_marks(student_id):
    res = marks_manager.get_student_marks(student_id)
    # Serialize OOP Mark objects
    res['subjects'] = [m.to_dict() for m in res['subjects']]
    return jsonify({'success': True, 'data': res})

@app.route('/api/admin/students/<student_id>/marks', methods=['POST', 'PUT'])
@login_required
@admin_required
def api_admin_upsert_marks(student_id):
    data = request.json or {}
    subject_name = data.get('subject_name')
    marks_obtained = data.get('marks_obtained')
    max_marks = data.get('max_marks', 100)
    
    mark = marks_manager.add_or_update_marks(
        student_id=student_id, subject_name=subject_name,
        marks_obtained=marks_obtained, max_marks=max_marks
    )
    return jsonify({'success': True, 'message': f"Marks for '{mark.subject_name}' updated successfully."})

@app.route('/api/admin/students/<student_id>/marks/<subject_name>', methods=['DELETE'])
@login_required
@admin_required
def api_admin_delete_marks(student_id, subject_name):
    marks_manager.delete_marks(student_id, subject_name)
    return jsonify({'success': True, 'message': f"Marks for subject '{subject_name}' deleted."})

# Admin APIs (Attendance Management)

@app.route('/api/admin/students/<student_id>/attendance', methods=['GET'])
@login_required
@admin_required
def api_admin_get_attendance(student_id):
    logs = marks_manager.get_student_attendance(student_id)
    summary = marks_manager.get_attendance_summary(student_id)
    
    serialized_logs = [log.to_dict() for log in logs]
    return jsonify({
        'success': True,
        'data': {
            'logs': serialized_logs,
            'summary': summary
        }
    })

@app.route('/api/admin/students/<student_id>/attendance', methods=['POST'])
@login_required
@admin_required
def api_admin_add_attendance(student_id):
    data = request.json or {}
    date = data.get('date')
    status = data.get('status')
    
    record = marks_manager.add_attendance(student_id=student_id, date=date, status=status)
    return jsonify({'success': True, 'message': f"Attendance status logged as '{record.status}' for date {record.date}."})

# Admin Dashboard Stats API

@app.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
def api_admin_stats():
    stats = marks_manager.get_dashboard_stats()
    return jsonify({'success': True, 'data': stats})

# ----------------------------------------------------
# File Handling backup / recovery APIs
# ----------------------------------------------------

@app.route('/api/admin/backup/export/json', methods=['GET'])
@login_required
@admin_required
def api_backup_export_json():
    json_data = file_handler.export_students_to_json()
    return Response(
        json_data,
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=student_system_backup.json"}
    )

@app.route('/api/admin/backup/export/csv', methods=['GET'])
@login_required
@admin_required
def api_backup_export_csv():
    csv_data = file_handler.export_students_to_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=students_profile_export.csv"}
    )

@app.route('/api/admin/backup/import/json', methods=['POST'])
@login_required
@admin_required
def api_backup_import_json():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No backup file uploaded.'}), 400
        
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'success': False, 'message': 'Empty file selected.'}), 400
        
    file_content = uploaded_file.read().decode('utf-8')
    res = file_handler.import_students_from_json(file_content)
    
    return jsonify({
        'success': True,
        'message': f"Import complete. Succeeded: {res['success_count']}, Failed: {len(res['errors'])}",
        'data': res
    })

@app.route('/api/admin/backup/import/csv', methods=['POST'])
@login_required
@admin_required
def api_backup_import_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No CSV file uploaded.'}), 400
        
    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({'success': False, 'message': 'Empty file selected.'}), 400
        
    file_content = uploaded_file.read().decode('utf-8')
    res = file_handler.import_students_from_csv(file_content)
    
    return jsonify({
        'success': True,
        'message': f"Import complete. Succeeded: {res['success_count']}, Failed: {len(res['errors'])}",
        'data': res
    })

# ----------------------------------------------------
# Noticeboard & Announcements endpoints
# ----------------------------------------------------

@app.route('/api/announcements', methods=['GET'])
@login_required
def api_list_announcements():
    notices = marks_manager.get_all_announcements()
    return jsonify({'success': True, 'data': notices})

@app.route('/api/admin/announcements', methods=['POST'])
@login_required
@admin_required
def api_create_announcement():
    data = request.json or {}
    title = data.get('title')
    content = data.get('content')
    
    announcement_id = marks_manager.create_announcement(title, content)
    return jsonify({
        'success': True, 
        'message': 'Announcement published successfully.',
        'data': {'id': announcement_id}
    })

@app.route('/api/admin/announcements/<int:announcement_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_announcement(announcement_id):
    marks_manager.delete_announcement(announcement_id)
    return jsonify({'success': True, 'message': 'Announcement deleted successfully.'})

@app.route('/api/admin/attendance/at-risk', methods=['GET'])
@login_required
@admin_required
def api_admin_at_risk_attendance():
    threshold_str = request.args.get('threshold', '75.0')
    try:
        threshold = float(threshold_str)
    except ValueError:
        threshold = 75.0
        
    students = marks_manager.get_students_at_risk_attendance(threshold)
    return jsonify({'success': True, 'data': students})

@app.route('/api/admin/seed-data', methods=['POST'])
@login_required
@admin_required
def api_admin_seed_data():
    """Seeds the database with sample student data, marks and attendance for demo purposes."""
    sample_students = [
        {'student_id': 'STU001', 'name': 'Alice Johnson', 'email': 'alice@school.com',
         'phone': '9876543210', 'department': 'Computer Science', 'year': '2nd Year',
         'dob': '2003-05-14', 'password': 'alice123'},
        {'student_id': 'STU002', 'name': 'Bob Martinez', 'email': 'bob@school.com',
         'phone': '9123456780', 'department': 'Mechanical Engineering', 'year': '1st Year',
         'dob': '2004-08-22', 'password': 'bob123'},
        {'student_id': 'STU003', 'name': 'Priya Sharma', 'email': 'priya@school.com',
         'phone': '9988776655', 'department': 'Information Technology', 'year': '3rd Year',
         'dob': '2002-12-01', 'password': 'priya123'},
        {'student_id': 'STU004', 'name': 'David Chen', 'email': 'david@school.com',
         'phone': '9001122334', 'department': 'Electronics & Communication', 'year': '4th Year',
         'dob': '2001-03-30', 'password': 'david123'},
        {'student_id': 'STU005', 'name': 'Sara Williams', 'email': 'sara@school.com',
         'phone': '9871234560', 'department': 'Business Administration', 'year': '2nd Year',
         'dob': '2003-09-18', 'password': 'sara123'},
    ]

    sample_marks = {
        'STU001': [('Mathematics', 88, 100), ('Physics', 75, 100), ('Data Structures', 92, 100), ('English', 80, 100)],
        'STU002': [('Thermodynamics', 70, 100), ('Engineering Drawing', 65, 100), ('Mathematics', 55, 100)],
        'STU003': [('Database Systems', 95, 100), ('Web Technology', 88, 100), ('Networking', 78, 100), ('Python', 91, 100)],
        'STU004': [('Signal Processing', 82, 100), ('Microcontrollers', 74, 100), ('VLSI Design', 68, 100)],
        'STU005': [('Business Law', 85, 100), ('Marketing', 90, 100), ('Accounting', 76, 100), ('Economics', 62, 100)],
    }

    sample_attendance = {
        'STU001': [('2025-07-01','Present'),('2025-07-02','Present'),('2025-07-03','Absent'),
                   ('2025-07-04','Present'),('2025-07-07','Present'),('2025-07-08','Late'),
                   ('2025-07-09','Present'),('2025-07-10','Present')],
        'STU002': [('2025-07-01','Absent'),('2025-07-02','Absent'),('2025-07-03','Absent'),
                   ('2025-07-04','Present'),('2025-07-07','Present'),('2025-07-08','Absent'),
                   ('2025-07-09','Present'),('2025-07-10','Absent')],
        'STU003': [('2025-07-01','Present'),('2025-07-02','Present'),('2025-07-03','Present'),
                   ('2025-07-04','Present'),('2025-07-07','Present'),('2025-07-08','Present'),
                   ('2025-07-09','Late'),('2025-07-10','Present')],
        'STU004': [('2025-07-01','Present'),('2025-07-02','Late'),('2025-07-03','Present'),
                   ('2025-07-04','Absent'),('2025-07-07','Present'),('2025-07-08','Present'),
                   ('2025-07-09','Present'),('2025-07-10','Present')],
        'STU005': [('2025-07-01','Present'),('2025-07-02','Present'),('2025-07-03','Late'),
                   ('2025-07-04','Present'),('2025-07-07','Absent'),('2025-07-08','Present'),
                   ('2025-07-09','Present'),('2025-07-10','Present')],
    }

    created = []
    skipped = []

    for s in sample_students:
        try:
            student_manager.create_student(**s)
            created.append(s['student_id'])
        except (DuplicateRecordError, ValidationError):
            skipped.append(s['student_id'])

    # Add marks for successfully created students
    for sid, subjects in sample_marks.items():
        for subj, obtained, max_m in subjects:
            try:
                marks_manager.add_or_update_marks(student_id=sid, subject_name=subj,
                                                   marks_obtained=obtained, max_marks=max_m)
            except Exception:
                pass

    # Add attendance for successfully created students
    for sid, records in sample_attendance.items():
        for date, status in records:
            try:
                marks_manager.add_attendance(student_id=sid, date=date, status=status)
            except Exception:
                pass

    return jsonify({
        'success': True,
        'message': f"Seed complete. Created: {len(created)}, Already existed (skipped): {len(skipped)}.",
        'data': {'created': created, 'skipped': skipped}
    })

# ----------------------------------------------------
# Gemini AI Assistant Endpoints
# ----------------------------------------------------

@app.route('/api/student/ai-recommendations', methods=['GET'])
@login_required
@student_required
def api_student_ai_recommendations():
    """Generates a personalized counselor advice sheet for the logged-in student."""
    try:
        student = student_manager.get_student_by_user_id(session.get('user_id'))
        
        # Get marks
        marks_data = marks_manager.get_student_marks(student.student_id)
        subjects = [m.to_dict() for m in marks_data['subjects']]
        
        # Get attendance rate
        att_summary = marks_manager.get_attendance_summary(student.student_id)
        attendance_rate = att_summary['rate']
        
        # Generate recommendations using Gemini
        feedback = gemini_assistant.generate_performance_recommendations(
            student_name=student.name,
            department=student.department,
            year=student.year,
            subjects=subjects,
            attendance_rate=attendance_rate
        )
        
        return jsonify({'success': True, 'feedback': feedback})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/ai-assistant', methods=['POST'])
@login_required
@admin_required
def api_admin_ai_assistant():
    """AI Assistant to help admins draft announcements or analyze reports."""
    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'success': False, 'message': 'Prompt cannot be empty.'}), 400
        
    system_instruction = (
        "You are an AI Administrator Assistant at a school portal. "
        "Help the administrator draft announcements, newsletters, noticeboard posts, "
        "or answer administrative strategy questions with professional tone."
    )
    
    response = gemini_assistant.ask_gemini(prompt, system_instruction)
    return jsonify({'success': True, 'response': response})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
