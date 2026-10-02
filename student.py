from flask import Blueprint, render_template, session, redirect, url_for
from database import get_db
from auth import student_required

student = Blueprint('student', __name__, url_prefix='/student')

@student.route('/dashboard')
@student_required
def dashboard():
    db = get_db()
    pid = session['patient_id']
    patient = db.execute('SELECT * FROM patients WHERE id = ?', (pid,)).fetchone()
    stats = {
        'appointments': db.execute('SELECT COUNT(*) FROM appointments WHERE patient_id = ?', (pid,)).fetchone()[0],
        'prescriptions': db.execute('SELECT COUNT(*) FROM prescriptions WHERE patient_id = ?', (pid,)).fetchone()[0],
        'unpaid_bills':  db.execute("SELECT COUNT(*) FROM bills WHERE patient_id = ? AND status='Unpaid'", (pid,)).fetchone()[0],
        'total_bills':   db.execute('SELECT COUNT(*) FROM bills WHERE patient_id = ?', (pid,)).fetchone()[0],
    }
    upcoming = db.execute(
        "SELECT * FROM appointments WHERE patient_id = ? AND status='Scheduled' ORDER BY date ASC, time ASC LIMIT 3",
        (pid,)
    ).fetchall()
    recent_rx = db.execute(
        'SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY date DESC LIMIT 3',
        (pid,)
    ).fetchall()
    return render_template('student/dashboard.html', patient=patient, stats=stats,
                           upcoming=upcoming, recent_rx=recent_rx)


@student.route('/appointments')
@student_required
def appointments():
    db = get_db()
    pid = session['patient_id']
    rows = db.execute(
        'SELECT * FROM appointments WHERE patient_id = ? ORDER BY date DESC, time DESC',
        (pid,)
    ).fetchall()
    return render_template('student/appointments.html', appointments=rows)


@student.route('/prescriptions')
@student_required
def prescriptions():
    db = get_db()
    pid = session['patient_id']
    rows = db.execute(
        'SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY date DESC',
        (pid,)
    ).fetchall()
    return render_template('student/prescriptions.html', prescriptions=rows)


@student.route('/billing')
@student_required
def billing():
    db = get_db()
    pid = session['patient_id']
    rows = db.execute(
        'SELECT * FROM bills WHERE patient_id = ? ORDER BY date DESC',
        (pid,)
    ).fetchall()
    total_paid   = sum(b['amount'] for b in rows if b['status'] == 'Paid')
    total_unpaid = sum(b['amount'] for b in rows if b['status'] == 'Unpaid')
    return render_template('student/billing.html', bills=rows,
                           total_paid=total_paid, total_unpaid=total_unpaid)
