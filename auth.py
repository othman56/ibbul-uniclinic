from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

auth = Blueprint('auth', __name__)

# ── Access control decorators ─────────────────────────────────────────────────

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def staff_required(f):
    """Allow only staff users. Students get redirected to their dashboard."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'staff':
            flash('Access denied. Staff only.', 'danger')
            return redirect(url_for('student.dashboard'))
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    """Allow only student users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── Routes ────────────────────────────────────────────────────────────────────

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Already logged in — redirect to appropriate dashboard
    if 'user_id' in session:
        return redirect(url_for('student.dashboard') if session.get('role') == 'student' else url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            session['patient_id'] = user['patient_id']  # None for staff
            flash(f'Welcome back, {user["username"]}!', 'success')
            if user['role'] == 'student':
                return redirect(url_for('student.dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth.route('/create-staff', methods=['GET', 'POST'])
def create_staff():
    """
    One-time staff account creation. Once at least one staff account exists,
    this page redirects to login (to prevent unauthorised account creation).
    """
    db = get_db()
    staff_count = db.execute("SELECT COUNT(*) FROM users WHERE role='staff'").fetchone()[0]
    if staff_count > 0 and 'user_id' not in session:
        flash('Staff accounts already exist. Please log in.', 'info')
        return redirect(url_for('auth.login'))
    if staff_count > 0 and session.get('role') != 'staff':
        flash('Only existing staff can create new staff accounts.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            flash('That username is already taken.', 'danger')
        else:
            db.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), 'staff')
            )
            db.commit()
            flash(f'Staff account "{username}" created successfully!', 'success')
            return redirect(url_for('auth.login'))
    return render_template('create_staff.html')
