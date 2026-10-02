from flask import Flask, render_template, request, redirect, url_for, flash, g
from database import init_db, get_db
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clinic_secret_key_2024'

# ── Context processor & teardown ─────────────────────────────────────────────
@app.context_processor
def inject_globals():
    from flask import session
    return {
        'now': datetime.now(),
        'current_user': {
            'username': session.get('username'),
            'role':     session.get('role'),
        }
    }

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ── Register blueprints ───────────────────────────────────────────────────────
from auth import auth
from student import student
app.register_blueprint(auth)
app.register_blueprint(student)

# ── Init DB ───────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

# ── Import staff_required decorator ──────────────────────────────────────────
from auth import staff_required

# ── STAFF DASHBOARD ───────────────────────────────────────────────────────────
@app.route('/')
@staff_required
def dashboard():
    db = get_db()
    stats = {
        'total_patients':      db.execute('SELECT COUNT(*) FROM patients').fetchone()[0],
        'today_appointments':  db.execute(
            "SELECT COUNT(*) FROM appointments WHERE date = ?",
            (datetime.today().strftime('%Y-%m-%d'),)
        ).fetchone()[0],
        'pending_bills':       db.execute("SELECT COUNT(*) FROM bills WHERE status='Unpaid'").fetchone()[0],
        'total_prescriptions': db.execute('SELECT COUNT(*) FROM prescriptions').fetchone()[0],
    }
    recent_appointments = db.execute('''
        SELECT a.id, p.name AS patient, a.date, a.time, a.reason, a.status
        FROM appointments a JOIN patients p ON a.patient_id = p.id
        ORDER BY a.date DESC, a.time DESC LIMIT 5
    ''').fetchall()
    return render_template('dashboard.html', stats=stats, recent=recent_appointments)


# ── PATIENTS ──────────────────────────────────────────────────────────────────
@app.route('/patients')
@staff_required
def patients():
    db = get_db()
    search = request.args.get('search', '')
    if search:
        rows = db.execute(
            "SELECT * FROM patients WHERE name LIKE ? OR matric_no LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM patients ORDER BY id DESC').fetchall()
    return render_template('patients.html', patients=rows, search=search)

@app.route('/patients/new', methods=['GET', 'POST'])
@staff_required
def new_patient():
    if request.method == 'POST':
        from werkzeug.security import generate_password_hash
        db = get_db()
        # Insert patient
        cur = db.execute('''
            INSERT INTO patients (name, matric_no, age, gender, phone, email, blood_group, address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['name'], request.form['matric_no'], request.form['age'],
            request.form['gender'], request.form['phone'], request.form['email'],
            request.form['blood_group'], request.form['address']
        ))
        patient_id = cur.lastrowid

        # Optionally create student login
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username and password:
            existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
            if existing:
                flash('Patient registered but username already taken — choose a different one.', 'warning')
            else:
                db.execute(
                    'INSERT INTO users (username, password_hash, role, patient_id) VALUES (?, ?, ?, ?)',
                    (username, generate_password_hash(password), 'student', patient_id)
                )
                flash('Patient registered and student login created!', 'success')
        else:
            flash('Patient registered successfully! (No login created)', 'success')

        db.commit()
        return redirect(url_for('patients'))
    return render_template('patient_form.html', patient=None)

@app.route('/patients/<int:pid>')
@staff_required
def patient_detail(pid):
    db = get_db()
    patient      = db.execute('SELECT * FROM patients WHERE id = ?', (pid,)).fetchone()
    appointments = db.execute('SELECT * FROM appointments WHERE patient_id = ? ORDER BY date DESC', (pid,)).fetchall()
    prescriptions= db.execute('SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY date DESC', (pid,)).fetchall()
    bills        = db.execute('SELECT * FROM bills WHERE patient_id = ? ORDER BY date DESC', (pid,)).fetchall()
    has_login    = db.execute('SELECT id FROM users WHERE patient_id = ?', (pid,)).fetchone()
    return render_template('patient_detail.html', patient=patient, appointments=appointments,
                           prescriptions=prescriptions, bills=bills, has_login=has_login)

@app.route('/patients/<int:pid>/edit', methods=['GET', 'POST'])
@staff_required
def edit_patient(pid):
    db = get_db()
    patient = db.execute('SELECT * FROM patients WHERE id = ?', (pid,)).fetchone()
    if request.method == 'POST':
        db.execute('''
            UPDATE patients SET name=?, matric_no=?, age=?, gender=?, phone=?, email=?, blood_group=?, address=?
            WHERE id=?
        ''', (
            request.form['name'], request.form['matric_no'], request.form['age'],
            request.form['gender'], request.form['phone'], request.form['email'],
            request.form['blood_group'], request.form['address'], pid
        ))
        db.commit()
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('patient_detail', pid=pid))
    return render_template('patient_form.html', patient=patient)

@app.route('/patients/<int:pid>/create-login', methods=['POST'])
@staff_required
def create_patient_login(pid):
    from werkzeug.security import generate_password_hash
    db = get_db()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not password:
        flash('Username and password are required.', 'danger')
    else:
        existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if existing:
            flash('That username is already taken.', 'danger')
        else:
            db.execute(
                'INSERT INTO users (username, password_hash, role, patient_id) VALUES (?, ?, ?, ?)',
                (username, generate_password_hash(password), 'student', pid)
            )
            db.commit()
            flash('Student login created successfully!', 'success')
    return redirect(url_for('patient_detail', pid=pid))


# ── APPOINTMENTS ──────────────────────────────────────────────────────────────
@app.route('/appointments')
@staff_required
def appointments():
    db = get_db()
    rows = db.execute('''
        SELECT a.*, p.name AS patient_name, p.matric_no
        FROM appointments a JOIN patients p ON a.patient_id = p.id
        ORDER BY a.date DESC, a.time DESC
    ''').fetchall()
    return render_template('appointments.html', appointments=rows)

@app.route('/appointments/new', methods=['GET', 'POST'])
@staff_required
def new_appointment():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            INSERT INTO appointments (patient_id, date, time, reason, status)
            VALUES (?, ?, ?, ?, 'Scheduled')
        ''', (request.form['patient_id'], request.form['date'],
              request.form['time'], request.form['reason']))
        db.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointments'))
    patients = db.execute('SELECT id, name, matric_no FROM patients').fetchall()
    return render_template('appointment_form.html', patients=patients)

@app.route('/appointments/<int:aid>/status', methods=['POST'])
@staff_required
def update_appointment_status(aid):
    db = get_db()
    db.execute('UPDATE appointments SET status=? WHERE id=?', (request.form['status'], aid))
    db.commit()
    flash('Appointment status updated!', 'success')
    return redirect(url_for('appointments'))


# ── PRESCRIPTIONS ─────────────────────────────────────────────────────────────
@app.route('/prescriptions')
@staff_required
def prescriptions():
    db = get_db()
    rows = db.execute('''
        SELECT pr.*, p.name AS patient_name, p.matric_no
        FROM prescriptions pr JOIN patients p ON pr.patient_id = p.id
        ORDER BY pr.date DESC
    ''').fetchall()
    return render_template('prescriptions.html', prescriptions=rows)

@app.route('/prescriptions/new', methods=['GET', 'POST'])
@staff_required
def new_prescription():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            INSERT INTO prescriptions (patient_id, date, diagnosis, medication, dosage, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (request.form['patient_id'], request.form['date'],
              request.form['diagnosis'], request.form['medication'],
              request.form['dosage'], request.form['notes']))
        db.commit()
        flash('Prescription added successfully!', 'success')
        return redirect(url_for('prescriptions'))
    patients = db.execute('SELECT id, name, matric_no FROM patients').fetchall()
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('prescription_form.html', patients=patients, today=today)


# ── BILLING ───────────────────────────────────────────────────────────────────
@app.route('/billing')
@staff_required
def billing():
    db = get_db()
    rows = db.execute('''
        SELECT b.*, p.name AS patient_name, p.matric_no
        FROM bills b JOIN patients p ON b.patient_id = p.id
        ORDER BY b.date DESC
    ''').fetchall()
    return render_template('billing.html', bills=rows)

@app.route('/billing/new', methods=['GET', 'POST'])
@staff_required
def new_bill():
    db = get_db()
    if request.method == 'POST':
        db.execute('''
            INSERT INTO bills (patient_id, date, description, amount, status)
            VALUES (?, ?, ?, ?, 'Unpaid')
        ''', (request.form['patient_id'], request.form['date'],
              request.form['description'], request.form['amount']))
        db.commit()
        flash('Bill created successfully!', 'success')
        return redirect(url_for('billing'))
    patients = db.execute('SELECT id, name, matric_no FROM patients').fetchall()
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template('bill_form.html', patients=patients, today=today)

@app.route('/billing/<int:bid>/pay', methods=['POST'])
@staff_required
def pay_bill(bid):
    db = get_db()
    db.execute("UPDATE bills SET status='Paid' WHERE id=?", (bid,))
    db.commit()
    flash('Bill marked as paid!', 'success')
    return redirect(url_for('billing'))


# ── REPORTS ───────────────────────────────────────────────────────────────────
@app.route('/reports')
@staff_required
def reports():
    db = get_db()
    monthly   = db.execute("SELECT strftime('%Y-%m', date) as month, COUNT(*) as count FROM appointments GROUP BY month ORDER BY month DESC LIMIT 6").fetchall()
    gender    = db.execute("SELECT gender, COUNT(*) as count FROM patients GROUP BY gender").fetchall()
    revenue   = db.execute("SELECT strftime('%Y-%m', date) as month, SUM(amount) as total FROM bills WHERE status='Paid' GROUP BY month ORDER BY month DESC LIMIT 6").fetchall()
    diagnoses = db.execute("SELECT diagnosis, COUNT(*) as count FROM prescriptions GROUP BY diagnosis ORDER BY count DESC LIMIT 5").fetchall()
    return render_template('reports.html', monthly=monthly, gender=gender,
                           revenue=revenue, diagnoses=diagnoses)


if __name__ == '__main__':
    app.run(debug=True)
