import unittest
import os
import tempfile
import json
import sqlite3

# Configure database module path prior to loading other managers
os.environ['TESTING'] = 'True'
import database
import app
import auth
import student_manager
import marks_manager
import file_handler
import utils

class ModularSchoolTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()
        database.DATABASE_PATH = self.db_path
        
        # Initialize test database
        database.init_db()
        
        # Configure Flask application client
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.app.test_client()

    def tearDown(self):
        # Close database descriptor and remove file
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # ----------------------------------------------------
    # Database and Managers level tests
    # ----------------------------------------------------

    def test_admin_seeding(self):
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE username = 'admin@school.com'")
        admin = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(admin)
        self.assertEqual(admin['role'], 'admin')

    def test_student_crud_and_exceptions(self):
        # Create Student
        student = student_manager.create_student(
            student_id='STU200',
            name='Alice Wonderland',
            email='alice@wonder.com',
            phone='111-222',
            department='Computer Science',
            year='2nd Year',
            dob='2000-01-01',
            password='securepassword'
        )
        self.assertIsNotNone(student)
        self.assertEqual(student.name, 'Alice Wonderland')

        # Test duplicate record exception
        with self.assertRaises(utils.DuplicateRecordError):
            student_manager.create_student(
                student_id='STU200', # Duplicate ID
                name='Bob duplicate',
                email='bob@wonder.com',
                phone='111',
                department='Computer Science',
                year='1st Year',
                dob='2000-01-01',
                password='pass'
            )

        # Test duplicate email exception
        with self.assertRaises(utils.DuplicateRecordError):
            student_manager.create_student(
                student_id='STU201',
                name='Bob duplicate',
                email='alice@wonder.com', # Duplicate Email
                phone='111',
                department='Computer Science',
                year='1st Year',
                dob='2000-01-01',
                password='pass'
            )

    def test_student_authentication(self):
        student_manager.create_student(
            student_id='STU202', name='Charlie Green', email='charlie@green.com',
            phone='333', department='Information Technology', year='3rd Year',
            dob='1999-03-03', password='goodpassword'
        )

        # Test authentication success
        user = auth.authenticate_user('charlie@green.com', 'goodpassword')
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'charlie@green.com')

        # Test wrong password
        with self.assertRaises(utils.ValidationError):
            auth.authenticate_user('charlie@green.com', 'badpassword')

        # Test missing user
        with self.assertRaises(utils.RecordNotFoundError):
            auth.authenticate_user('unknown@user.com', 'any')

    def test_marks_computations(self):
        student_manager.create_student(
            student_id='STU203', name='David Miller', email='david@miller.com',
            phone='444', department='Mechanical Engineering', year='4th Year',
            dob='1998-04-04', password='pass'
        )

        # Add subject marks
        marks_manager.add_or_update_marks('STU203', 'Thermodynamics', 85, 100)
        marks_manager.add_or_update_marks('STU203', 'Fluid Mechanics', 40, 50) # 80%
        marks_manager.add_or_update_marks('STU203', 'CAD Design', 60, 100) # 60%

        # Total Obtained: 85 + 40 + 60 = 185. Total Max: 100 + 50 + 100 = 250
        # Percentage: 185 / 250 * 100 = 74.0% (Grade B)
        report = marks_manager.get_student_marks('STU203')
        self.assertEqual(report['total_obtained'], 185.0)
        self.assertEqual(report['total_max'], 250.0)
        self.assertEqual(report['percentage'], 74.0)
        self.assertEqual(report['grade'], 'B')

    def test_attendance_weights(self):
        student_manager.create_student(
            student_id='STU204', name='Elena Gilbert', email='elena@gilbert.com',
            phone='555', department='Business Administration', year='1st Year',
            dob='2001-05-05', password='pass'
        )

        # Log attendance statuses
        marks_manager.add_attendance('STU204', '2026-10-01', 'Present')
        marks_manager.add_attendance('STU204', '2026-10-02', 'Absent')
        marks_manager.add_attendance('STU204', '2026-10-03', 'Late')

        summary = marks_manager.get_attendance_summary('STU204')
        self.assertEqual(summary['total'], 3)
        self.assertEqual(summary['counts']['Present'], 1)
        self.assertEqual(summary['counts']['Absent'], 1)
        self.assertEqual(summary['counts']['Late'], 1)
        
        # Attendance percentage: (1 + 0.5) / 3 = 50%
        self.assertEqual(summary['rate'], 50.0)

    # ----------------------------------------------------
    # File Handling CSV & JSON backup tests
    # ----------------------------------------------------

    def test_file_backup_exports(self):
        student_manager.create_student(
            student_id='STU205', name='Frank Castle', email='frank@castle.com',
            phone='666', department='Electronics & Communication', year='3rd Year',
            dob='1999-06-06', password='pass'
        )
        marks_manager.add_or_update_marks('STU205', 'Embedded Systems', 95, 100)
        marks_manager.add_attendance('STU205', '2026-11-01', 'Present')

        # Export JSON
        json_backup = file_handler.export_students_to_json()
        parsed_json = json.loads(json_backup)
        self.assertTrue(len(parsed_json['students']) >= 1)
        
        # Export CSV
        csv_backup = file_handler.export_students_to_csv()
        self.assertIn('STU205', csv_backup)
        self.assertIn('frank@castle.com', csv_backup)

    def test_file_backup_imports(self):
        json_import_data = """{
            "students": [
                {
                    "student_id": "STU990",
                    "name": "Imported JSON Student",
                    "email": "json@import.com",
                    "phone": "999-0101",
                    "department": "Computer Science",
                    "year": "1st Year",
                    "dob": "2003-09-09",
                    "marks": [
                        { "subject_name": "Python OOP", "marks_obtained": 98.0, "max_marks": 100.0 }
                    ],
                    "attendance": [
                        { "date": "2026-12-01", "status": "Present" }
                    ]
                }
            ]
        }"""
        
        res = file_handler.import_students_from_json(json_import_data)
        self.assertEqual(res['success_count'], 1)
        self.assertEqual(len(res['errors']), 0)
        
        # Verify inserted
        student = student_manager.get_student_by_id('STU990')
        self.assertEqual(student.name, 'Imported JSON Student')
        
        marks = marks_manager.get_student_marks('STU990')
        self.assertEqual(marks['total_obtained'], 98.0)
        
        attendance = marks_manager.get_student_attendance('STU990')
        self.assertEqual(len(attendance), 1)

if __name__ == '__main__':
    unittest.main()
