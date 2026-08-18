class User:
    def __init__(self, user_id, username, password_hash, role):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(row['id'], row['username'], row['password_hash'], row['role'])


class Student:
    def __init__(self, student_id, user_id, name, email, phone, department, year, dob):
        self.student_id = student_id
        self.user_id = user_id
        self.name = name
        self.email = email
        self.phone = phone
        self.department = department
        self.year = year
        self.dob = dob

    def to_dict(self):
        return {
            'student_id': self.student_id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'department': self.department,
            'year': self.year,
            'dob': self.dob
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            row['student_id'],
            row['user_id'],
            row['name'],
            row['email'],
            row['phone'],
            row['department'],
            row['year'],
            row['dob']
        )


class Mark:
    def __init__(self, mark_id, student_id, subject_name, marks_obtained, max_marks=100):
        self.id = mark_id
        self.student_id = student_id
        self.subject_name = subject_name
        self.marks_obtained = float(marks_obtained)
        self.max_marks = float(max_marks)

    @property
    def percentage(self):
        if self.max_marks > 0:
            return round((self.marks_obtained / self.max_marks) * 100, 2)
        return 0.0

    @property
    def grade(self):
        pct = self.percentage
        if pct >= 90:
            return 'A+'
        elif pct >= 80:
            return 'A'
        elif pct >= 70:
            return 'B'
        elif pct >= 60:
            return 'C'
        elif pct >= 50:
            return 'D'
        elif pct >= 40:
            return 'E'
        else:
            return 'F'

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_name': self.subject_name,
            'marks_obtained': self.marks_obtained,
            'max_marks': self.max_marks,
            'percentage': self.percentage,
            'grade': self.grade
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(
            row['id'],
            row['student_id'],
            row['subject_name'],
            row['marks_obtained'],
            row['max_marks']
        )


class AttendanceRecord:
    def __init__(self, att_id, student_id, date, status):
        self.id = att_id
        self.student_id = student_id
        self.date = date
        self.status = status

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'date': self.date,
            'status': self.status
        }

    @classmethod
    def from_row(cls, row):
        if not row:
            return None
        return cls(row['id'], row['student_id'], row['date'], row['status'])
