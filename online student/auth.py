from werkzeug.security import check_password_hash, generate_password_hash
import database
from models import User
from utils import ValidationError, RecordNotFoundError

def authenticate_user(username, password):
    """
    Authenticate a user using username and password.
    Returns a User object if successful, raises ValidationError or RecordNotFoundError on failure.
    """
    if not username or not password:
        raise ValidationError("Username and password are required.")

    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise RecordNotFoundError("User account does not exist.")

    user = User.from_row(row)
    if check_password_hash(user.password_hash, password):
        return user
    else:
        raise ValidationError("Invalid password.")

def create_user_record(cursor, username, password, role='student'):
    """
    Inserts a user record within a database transaction cursor.
    """
    if not username or not password:
        raise ValidationError("Username and password are required for user creation.")
        
    hashed_pw = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), hashed_pw, role)
        )
        return cursor.lastrowid
    except database.sqlite3.IntegrityError:
        raise ValidationError(f"Username '{username}' is already registered.")
