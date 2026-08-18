import re
from datetime import datetime

# Custom Exceptions for robust error handling
class SchoolSystemError(Exception):
    """Base exception class for the application"""
    pass

class DuplicateRecordError(SchoolSystemError):
    """Raised when trying to create a record that already exists"""
    pass

class RecordNotFoundError(SchoolSystemError):
    """Raised when looking up a record that does not exist"""
    pass

class ValidationError(SchoolSystemError):
    """Raised when input validation fails"""
    pass

class DatabaseIntegrityError(SchoolSystemError):
    """Raised when database constraint is violated"""
    pass


# Input Validation utilities
def validate_email(email):
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not email or not re.match(email_regex, email):
        raise ValidationError(f"Invalid email format: '{email}'")
    return email

def validate_student_id(student_id):
    if not student_id or len(student_id.strip()) < 3:
        raise ValidationError("Student ID must be at least 3 characters long.")
    return student_id.strip()

def validate_name(name):
    if not name or len(name.strip()) < 2:
        raise ValidationError("Name must be at least 2 characters long.")
    return name.strip()

def validate_date(date_str):
    if not date_str:
        return None
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        raise ValidationError(f"Invalid date format: '{date_str}'. Expected 'YYYY-MM-DD'.")

def validate_marks(obtained, max_marks=100):
    try:
        obt = float(obtained)
        max_m = float(max_marks)
    except (ValueError, TypeError):
        raise ValidationError("Marks must be numeric values.")
    
    if obt < 0 or max_m <= 0:
        raise ValidationError("Marks cannot be negative, and max marks must be greater than zero.")
    if obt > max_m:
        raise ValidationError(f"Obtained marks ({obt}) cannot exceed maximum marks ({max_m}).")
    return obt, max_m

def validate_attendance_status(status):
    valid_statuses = ['Present', 'Absent', 'Late']
    if status not in valid_statuses:
        raise ValidationError(f"Invalid attendance status: '{status}'. Must be one of {valid_statuses}")
    return status
