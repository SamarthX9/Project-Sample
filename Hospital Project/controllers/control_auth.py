# controllers/control_auth.py
# Authentication (login/register/logout) and simple role-based decorators + test dashboards.
#
# This file follows your project's import pattern:
# main.py creates `app` then imports controllers, so importing `app` here is fine.

from flask import render_template, request, redirect, url_for, flash, session
from main import app, db
from models import Admin, Doctor, Patient
from werkzeug.security import check_password_hash

# -----------------------
# Helper decorators
# -----------------------
def login_required(f):
    """Simple login_required decorator for routes that require any logged-in user."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or 'user_id' not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(required_role):
    """
    Decorator factory to enforce role (admin / doctor / patient).
    Example: @role_required('admin')
    """
    from functools import wraps
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'role' not in session:
                flash("Please login to continue.", "warning")
                return redirect(url_for('login'))
            if session.get('role') != required_role:
                flash("Access denied. Insufficient permissions.", "danger")
                # Redirect to their dashboard if logged in as other role
                role = session.get('role')
                if role == 'admin':
                    return redirect('/admin/dashboard')
                if role == 'doctor':
                    return redirect('/doctor/dashboard')
                if role == 'patient':
                    return redirect('/patient/dashboard')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return wrapper


# -----------------------
# Routes: login / register / logout
# -----------------------
@app.route('/')
def home():
    # quick home page
    return redirect(url_for('login'))


@app.route('/debug/patients')
def debug_patients():
    patients = Patient.query.all()
    return f"<h3>All Patients ({len(patients)})</h3>" + "".join([f"<p>{p.id}: {p.name} ({p.email})</p>" for p in patients])


@app.route('/debug/doctors')
def debug_doctors():
    doctors = Doctor.query.all()
    return f"<h3>All Doctors ({len(doctors)})</h3>" + "".join([f"<p>{d.id}: {d.name} ({d.email})</p>" for d in doctors])


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login form accepts:
      - role: admin / doctor / patient
      - identifier: admin uses username, doctor/patient uses email
      - password
    On success, session stores:
      session['role'] = 'admin' / 'doctor' / 'patient'
      session['user_id'] = admin_username or numeric id for doctor/patient
    """
    if request.method == 'POST':
        role = request.form.get('role')
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not role or not identifier or not password:
            flash("Please fill all fields.", "warning")
            return redirect(url_for('login'))

        # Query according to role
        user = None
        if role == 'admin':
            # Admin uses admin_username (matches your sample)
            user = Admin.query.filter_by(admin_username=identifier).first()
            if user and check_password_hash(user.password_hash, password):
                session['role'] = 'admin'
                session['user_id'] = user.admin_username
                flash("Admin login successful.", "success")
                return redirect('/admin/dashboard')
            else:
                flash("Invalid admin credentials.", "danger")
                return redirect(url_for('login'))

        elif role == 'doctor':
            user = Doctor.query.filter_by(email=identifier).first()
            if not user:
                flash("Doctor not found.", "warning")
                return redirect(url_for('login'))
            if user.is_blacklisted:
                flash("Your account is blocked. Contact admin.", "danger")
                return redirect(url_for('login'))
            if check_password_hash(user.password_hash, password):
                session['role'] = 'doctor'
                session['user_id'] = user.id
                flash("Doctor login successful.", "success")
                return redirect('/doctor/dashboard')
            else:
                flash("Invalid credentials.", "danger")
                return redirect(url_for('login'))

        elif role == 'patient':
            user = Patient.query.filter_by(email=identifier).first()
            if not user:
                flash("Patient not found.", "warning")
                return redirect(url_for('login'))
            if user.is_blacklisted:
                flash("Your account is blocked. Contact admin.", "danger")
                return redirect(url_for('login'))
            if check_password_hash(user.password_hash, password):
                session['role'] = 'patient'
                session['user_id'] = user.id
                flash("Patient login successful.", "success")
                return redirect('/patient/dashboard')
            else:
                flash("Invalid credentials.", "danger")
                return redirect(url_for('login'))
        else:
            flash("Invalid role selected.", "danger")
            return redirect(url_for('login'))

    # GET
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register_patient():
    """
    Patient registration page. Only patients register here.
    """
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "warning")
            return redirect(url_for('register_patient'))

        # check existing
        existing = Patient.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered. Login instead.", "warning")
            return redirect(url_for('login'))

        # create patient
        patient = Patient(name=name, email=email, phone=phone, age=age, gender=gender)
        # set password (models use set_password method)
        patient.set_password(password)
        try:
            db.session.add(patient)
            db.session.commit()
            print(f"✓ Patient registered: {email}")
            flash("Registration successful. Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error registering patient: {str(e)}")
            flash(f"Error creating account: {str(e)}", "danger")
            return redirect(url_for('register_patient'))

    return render_template('auth/register_patient.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# Admin-only: create doctor (admin manages doctors)
@app.route('/admin/register_doctor', methods=['GET', 'POST'])
@role_required('admin')
def register_doctor():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        phone = request.form.get('phone', '').strip()
        specialization = request.form.get('specialization', '').strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "warning")
            return redirect(url_for('register_doctor'))

        # check existing
        if Doctor.query.filter_by(email=email).first():
            flash("Email already registered for a doctor.", "warning")
            return redirect(url_for('admin_dashboard'))

        doctor = Doctor(name=name, email=email, phone=phone, specialization=specialization)
        doctor.set_password(password)
        try:
            db.session.add(doctor)
            db.session.commit()
            print(f"✓ Doctor registered: {email}")
            flash("Doctor created successfully.", "success")
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error registering doctor: {str(e)}")
            flash(f"Error creating doctor: {str(e)}", "danger")
            return redirect(url_for('register_doctor'))

    return render_template('auth/register_doctor.html')


# -----------------------
# Simple placeholder dashboards (so you can test role redirects)
# Replace these with full controllers later.
# -----------------------
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    # show counts and links (simple)
    total_doctors = Doctor.query.count()
    total_patients = Patient.query.count()
    total_appointments = 0
    try:
        # lazy import to avoid circular at module-import-time in some setups
        from models import Appointment
        total_appointments = Appointment.query.count()
    except Exception:
        total_appointments = 0

    return render_template('admin/dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments)


# -----------------------
# Admin management pages
# -----------------------
@app.route('/admin/doctors')
@role_required('admin')
def admin_doctors():
    doctors = Doctor.query.order_by(Doctor.created_at.desc()).all()
    return render_template('admin/doctors.html', doctors=doctors)


@app.route('/admin/search_doctors')
@role_required('admin')
def admin_search_doctors():
    query = request.args.get('query', '').strip()
    spec = request.args.get('specialization', '').strip()
    results = []
    if query or spec:
        filter_conditions = []
        if query:
            filter_conditions.append(
                db.or_(
                    Doctor.name.ilike(f'%{query}%'),
                    Doctor.email.ilike(f'%{query}%'),
                    Doctor.phone.ilike(f'%{query}%')
                )
            )
        if spec:
            filter_conditions.append(Doctor.specialization.ilike(f'%{spec}%'))
        results = Doctor.query.filter(*filter_conditions).order_by(Doctor.created_at.desc()).all()
    return render_template('admin/search_doctors.html', results=results, query=query, specialization=spec)


@app.route('/admin/doctor/<int:doc_id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def admin_edit_doctor(doc_id):
    doctor = Doctor.query.get_or_404(doc_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        specialization = request.form.get('specialization', '').strip()
        
        # Validate required fields
        if not name or not email:
            flash('Name and email are required.', 'warning')
            return redirect(url_for('admin_edit_doctor', doc_id=doc_id))
        
        # Check if email is being changed and if new email already exists
        if email != doctor.email:
            existing = Doctor.query.filter_by(email=email).first()
            if existing:
                flash('Email already in use by another doctor.', 'warning')
                return redirect(url_for('admin_edit_doctor', doc_id=doc_id))
        
        # Update fields
        doctor.name = name
        doctor.email = email
        doctor.phone = phone
        doctor.specialization = specialization
        
        try:
            db.session.commit()
            flash('Doctor updated successfully.', 'success')
            return redirect(url_for('admin_doctors'))
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error updating doctor: {str(e)}")
            flash(f'Error updating doctor: {str(e)}', 'danger')
            return redirect(url_for('admin_edit_doctor', doc_id=doc_id))
    return render_template('admin/edit_doctor.html', doctor=doctor)


@app.route('/admin/doctor/<int:doc_id>/toggle_blacklist')
@role_required('admin')
def admin_toggle_doctor_blacklist(doc_id):
    doctor = Doctor.query.get_or_404(doc_id)
    # Toggle: if True, set to False; if False, set to True; if None, set to True
    current_status = doctor.is_blacklisted if doctor.is_blacklisted is not None else False
    doctor.is_blacklisted = not current_status
    new_status = 'blocked' if doctor.is_blacklisted else 'unblocked'
    try:
        db.session.commit()
        print(f"✓ Doctor {doc_id} ({doctor.name}) {new_status}. is_blacklisted={doctor.is_blacklisted}")
        flash(f'Doctor {new_status} successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error toggling doctor blacklist: {str(e)}")
        flash(f'Error updating status: {str(e)}', 'danger')
    return redirect(url_for('admin_doctors'))


@app.route('/admin/patients')
@role_required('admin')
def admin_patients():
    patients = Patient.query.order_by(Patient.created_at.desc()).all()
    return render_template('admin/patients.html', patients=patients)


@app.route('/admin/search_patients')
@role_required('admin')
def admin_search_patients():
    query = request.args.get('query', '').strip()
    results = []
    if query:
        results = Patient.query.filter(
            db.or_(
                Patient.name.ilike(f'%{query}%'),
                Patient.email.ilike(f'%{query}%'),
                Patient.phone.ilike(f'%{query}%')
            )
        ).order_by(Patient.created_at.desc()).all()
    return render_template('admin/search_patients.html', results=results, query=query)


@app.route('/admin/patient/<int:pat_id>')
@role_required('admin')
def admin_patient_detail(pat_id):
    patient = Patient.query.get_or_404(pat_id)
    try:
        from models import Appointment
        appointments = Appointment.query.filter_by(patient_id=pat_id).all()
    except Exception:
        appointments = []
    return render_template('admin/patient_detail.html', patient=patient, appointments=appointments)


@app.route('/admin/patient/<int:pat_id>/toggle_blacklist')
@role_required('admin')
def admin_toggle_patient_blacklist(pat_id):
    patient = Patient.query.get_or_404(pat_id)
    # Toggle: if True, set to False; if False, set to True; if None, set to True
    current_status = patient.is_blacklisted if patient.is_blacklisted is not None else False
    patient.is_blacklisted = not current_status
    new_status = 'blocked' if patient.is_blacklisted else 'unblocked'
    try:
        db.session.commit()
        print(f"✓ Patient {pat_id} ({patient.name}) {new_status}. is_blacklisted={patient.is_blacklisted}")
        flash(f'Patient {new_status} successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error toggling patient blacklist: {str(e)}")
        flash(f'Error updating status: {str(e)}', 'danger')
    return redirect(url_for('admin_patients'))


@app.route('/admin/appointments')
@role_required('admin')
def admin_appointments():
    try:
        from models import Appointment, Patient, Doctor
        appts = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    except Exception:
        appts = []

    # Build quick lookup maps for patient and doctor names to display in template
    patients_info = {}
    doctors_info = {}
    try:
        for a in appts:
            # patient
            if a.patient_id not in patients_info:
                p = Patient.query.get(a.patient_id)
                if p:
                    patients_info[a.patient_id] = p
            # doctor
            if a.doctor_id not in doctors_info:
                d = Doctor.query.get(a.doctor_id)
                if d:
                    doctors_info[a.doctor_id] = d
    except Exception:
        patients_info = {}
        doctors_info = {}

    return render_template('admin/appointments.html', appointments=appts, patients_info=patients_info, doctors_info=doctors_info)


@app.route('/admin/appointment/<int:appt_id>/update_status', methods=['POST'])
@role_required('admin')
def admin_update_appointment_status(appt_id):
    from models import Appointment
    appt = Appointment.query.get_or_404(appt_id)
    new_status = request.form.get('status')
    if new_status not in ('Booked', 'Completed', 'Cancelled'):
        flash('Invalid status.', 'warning')
        return redirect(url_for('admin_appointments'))
    appt.status = new_status
    try:
        db.session.commit()
        flash('Appointment status updated.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error updating appointment.', 'danger')
    return redirect(url_for('admin_appointments'))


@app.route('/doctor/dashboard')
@role_required('doctor')
def doctor_dashboard():
    # get doctor id from session
    doc_id = session.get('user_id')
    doctor = Doctor.query.get(doc_id)
    # upcoming placeholder
    upcoming = []
    week_appts = []
    booked_count = 0
    completed_count = 0
    try:
        from models import Appointment, DoctorAvailability, Patient, Treatment
        # upcoming appointments for this doctor
        upcoming = Appointment.query.filter_by(doctor_id=doc_id).order_by(Appointment.date.asc(), Appointment.time.asc()).all()
        
        # Count booked (status='Booked') and completed (status='Completed') appointments
        booked_count = len([a for a in upcoming if a.status == 'Booked'])
        completed_count = len([a for a in upcoming if a.status == 'Completed'])
        
        # simple week filter: collect appts with date within next 7 days (string compare ok if YYYY-MM-DD)
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        week_end = today + timedelta(days=7)
        def in_next_week(a_date_str):
            try:
                d = datetime.strptime(a_date_str, '%Y-%m-%d').date()
                return today <= d <= week_end
            except Exception:
                return False
        week_appts = [a for a in upcoming if in_next_week(a.date)]

        # Get current availability
        availability = DoctorAvailability.query.filter_by(doctor_id=doc_id).all()
        
        # patients list (unique)
        patient_ids = sorted({a.patient_id for a in upcoming})
        patients = Patient.query.filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
        
        # Get treatment info for completed appointments
        treatments = {}
        for a in upcoming:
            t = Treatment.query.filter_by(appointment_id=a.id).first()
            if t:
                treatments[a.id] = t
        
        # Get patient info for each appointment
        patients_info = {}
        for a in upcoming:
            p = Patient.query.get(a.patient_id)
            if p:
                patients_info[a.id] = p
    except Exception:
        upcoming = []
        week_appts = []
        patients = []
        treatments = {}
        patients_info = {}
        availability = []
    return render_template('doctor/dashboard.html', doctor=doctor, upcoming=upcoming, week_appts=week_appts, patients=patients, treatments=treatments, patients_info=patients_info, booked_count=booked_count, completed_count=completed_count, availability=availability)



@app.route('/doctor/appointment/<int:appt_id>/update_status', methods=['POST'])
@role_required('doctor')
def doctor_update_appointment_status(appt_id):
    from models import Appointment
    doc_id = session.get('user_id')
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != doc_id:
        flash('Not authorized to update this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    new_status = request.form.get('status')
    if new_status not in ('Booked', 'Completed', 'Cancelled'):
        flash('Invalid status.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    appt.status = new_status
    try:
        db.session.commit()
        flash('Appointment status updated.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error updating appointment.', 'danger')
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/profile', methods=['GET', 'POST'])
@role_required('doctor')
def doctor_profile():
    doc_id = session.get('user_id')
    doctor = Doctor.query.get(doc_id)
    
    if request.method == 'POST':
        doctor.name = request.form.get('name', '').strip() or doctor.name
        doctor.phone = request.form.get('phone', '').strip() or doctor.phone
        doctor.specialization = request.form.get('specialization', '').strip() or doctor.specialization
        
        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('doctor_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('doctor_profile'))
    
    return render_template('doctor/edit_profile.html', doctor=doctor)


@app.route('/doctor/availability/add', methods=['POST'])
@role_required('doctor')
def doctor_add_availability():
    from models import DoctorAvailability
    from datetime import datetime, timedelta
    doc_id = session.get('user_id')
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    
    if not start_date or not end_date or not start_time or not end_time:
        flash('All availability fields are required.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    
    # Validate date range is within next 7 days
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        today = datetime.utcnow().date()
        max_date = today + timedelta(days=7)
        
        if start_date_obj < today:
            flash('Start date cannot be in the past.', 'warning')
            return redirect(url_for('doctor_dashboard'))
        
        if end_date_obj > max_date:
            flash('You can only set availability within the next 7 days.', 'warning')
            return redirect(url_for('doctor_dashboard'))
        
        if end_date_obj < start_date_obj:
            flash('End date must be after or equal to start date.', 'warning')
            return redirect(url_for('doctor_dashboard'))
    except ValueError:
        flash('Invalid date format.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    
    # Validate times
    try:
        start_time_obj = datetime.strptime(start_time, '%H:%M').time()
        end_time_obj = datetime.strptime(end_time, '%H:%M').time()
        
        if end_time_obj <= start_time_obj:
            flash('End time must be after start time.', 'warning')
            return redirect(url_for('doctor_dashboard'))
    except ValueError:
        flash('Invalid time format.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    
    avail = DoctorAvailability(doctor_id=doc_id, start_date=start_date, end_date=end_date, start_time=start_time, end_time=end_time)
    try:
        db.session.add(avail)
        db.session.commit()
        print(f"✓ Availability added for doctor {doc_id} from {start_date} to {end_date}, {start_time}-{end_time}")
        flash('Availability set successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"✗ Error adding availability: {str(e)}")
        flash(f'Error setting availability: {str(e)}', 'danger')
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/availability/<int:avail_id>/delete')
@role_required('doctor')
def doctor_delete_availability(avail_id):
    from models import DoctorAvailability
    doc_id = session.get('user_id')
    avail = DoctorAvailability.query.get_or_404(avail_id)
    
    if avail.doctor_id != doc_id:
        flash('Not authorized to delete this availability.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    try:
        db.session.delete(avail)
        db.session.commit()
        flash('Availability deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting availability: {str(e)}', 'danger')
    
    return redirect(url_for('doctor_dashboard'))


@app.route('/doctor/patient/<int:pat_id>/history')
@role_required('doctor')
def doctor_view_patient_history(pat_id):
    from models import Patient, Appointment, Treatment
    # ensure patient exists
    patient = Patient.query.get_or_404(pat_id)
    try:
        appointments = Appointment.query.filter_by(patient_id=pat_id).order_by(Appointment.date.desc()).all()
    except Exception:
        appointments = []
    # attach treatments where available
    treatments = {}
    try:
        for a in appointments:
            if a.treatment:
                treatments[a.id] = a.treatment
    except Exception:
        treatments = {}
    
    # Get doctor info for each appointment
    doctors_info = {}
    try:
        for a in appointments:
            doc = Doctor.query.get(a.doctor_id)
            if doc:
                doctors_info[a.id] = doc
    except Exception:
        doctors_info = {}
    
    return render_template('doctor/patient_history.html', patient=patient, appointments=appointments, treatments=treatments, doctors_info=doctors_info)


@app.route('/doctor/appointment/<int:appt_id>/add_treatment', methods=['GET', 'POST'])
@role_required('doctor')
def doctor_add_treatment(appt_id):
    from models import Appointment, Treatment
    doc_id = session.get('user_id')
    appt = Appointment.query.get_or_404(appt_id)
    
    if appt.doctor_id != doc_id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    existing_treatment = Treatment.query.filter_by(appointment_id=appt_id).first()
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis', '').strip()
        prescription = request.form.get('prescription', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not diagnosis:
            flash('Diagnosis is required.', 'warning')
            return redirect(url_for('doctor_add_treatment', appt_id=appt_id))
        
        if existing_treatment:
            existing_treatment.diagnosis = diagnosis
            existing_treatment.prescription = prescription
            existing_treatment.notes = notes
        else:
            existing_treatment = Treatment(appointment_id=appt_id, diagnosis=diagnosis, prescription=prescription, notes=notes)
            db.session.add(existing_treatment)
        
        try:
            db.session.commit()
            flash('Treatment record saved.', 'success')
            return redirect(url_for('doctor_dashboard'))
        except Exception:
            db.session.rollback()
            flash('Error saving treatment.', 'danger')
            return redirect(url_for('doctor_add_treatment', appt_id=appt_id))
    
    return render_template('doctor/add_treatment.html', appointment=appt, treatment=existing_treatment)


@app.route('/patient/dashboard')
@role_required('patient')
def patient_dashboard():
    from models import Appointment, Department, Treatment
    from datetime import datetime, timedelta
    pat_id = session.get('user_id')
    patient = Patient.query.get(pat_id)
    
    # Get appointments (upcoming + past)
    try:
        appointments = Appointment.query.filter_by(patient_id=pat_id).order_by(Appointment.date.desc()).all()
    except Exception:
        appointments = []
    
    # Get treatments for each appointment
    treatments = {}
    try:
        for a in appointments:
            t = Treatment.query.filter_by(appointment_id=a.id).first()
            if t:
                treatments[a.id] = t
    except Exception:
        treatments = {}
    
    # Get doctor info for each appointment
    doctors_info = {}
    try:
        for a in appointments:
            doc = Doctor.query.get(a.doctor_id)
            if doc:
                doctors_info[a.id] = doc
    except Exception:
        doctors_info = {}
    
    # Get departments
    try:
        # Base departments from Department table
        departments_objs = Department.query.all()
        # Also include any doctor specializations that are not yet represented as departments
        try:
            specs = db.session.query(Doctor.specialization).distinct().all()
            spec_names = [s[0] for s in specs if s and s[0]]
        except Exception:
            spec_names = []

        dept_names = [d.name for d in departments_objs] if departments_objs else []

        # Create a combined list of dict-like items with a `name` field so template access (d.name) works
        combined = []
        for d in departments_objs:
            combined.append({'name': d.name})
        for s in spec_names:
            if s and s not in dept_names:
                combined.append({'name': s})

        departments = combined
    except Exception:
        departments = []
    
    # Separate completed and upcoming appointments
    completed_appts = [a for a in appointments if a.status == 'Completed']
    upcoming_appts = [a for a in appointments if a.status == 'Booked']
    
    return render_template('patient/dashboard.html', 
                          patient=patient, 
                          appointments=appointments,
                          treatments=treatments,
                          doctors_info=doctors_info,
                          completed_appts=completed_appts,
                          upcoming_appts=upcoming_appts,
                          departments=departments)


@app.route('/patient/search_doctors')
@role_required('patient')
def patient_search_doctors():
    from models import DoctorAvailability
    from datetime import datetime, timedelta
    specialization = request.args.get('specialization', '').strip()
    doctor_name = request.args.get('name', '').strip()
    
    query = Doctor.query.filter_by(is_blacklisted=False)
    if specialization:
        query = query.filter_by(specialization=specialization)
    if doctor_name:
        query = query.filter(Doctor.name.ilike(f'%{doctor_name}%'))
    
    doctors = query.all()
    
    # Get availability for each doctor
    doctor_avail = {}
    for d in doctors:
        try:
            avails = DoctorAvailability.query.filter_by(doctor_id=d.id).all()
            doctor_avail[d.id] = avails
        except Exception:
            doctor_avail[d.id] = []
    
    # All specializations for filter dropdown
    specs = db.session.query(Doctor.specialization).distinct().filter(Doctor.is_blacklisted==False).all()
    specializations = [s[0] for s in specs if s[0]]
    
    return render_template('patient/search_doctors.html', 
                          doctors=doctors, 
                          doctor_avail=doctor_avail,
                          specializations=specializations,
                          selected_spec=specialization,
                          doctor_name=doctor_name)


@app.route('/patient/book_appointment', methods=['GET', 'POST'])
@role_required('patient')
def patient_book_appointment():
    from models import Appointment
    pat_id = session.get('user_id')
    selected_doctor_id = request.args.get('doctor_id')
    
    if request.method == 'POST':
        from models import DoctorAvailability
        doc_id = request.form.get('doctor_id')
        date = request.form.get('date', '').strip()
        time = request.form.get('time', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not doc_id or not date or not time:
            flash('Doctor, date, and time are required.', 'warning')
            return redirect(url_for('patient_search_doctors'))
        
        # Check if doctor has availability for this date and time
        try:
            from datetime import datetime
            booking_date = datetime.strptime(date, '%Y-%m-%d').date()
            
            # Find availability that covers this date
            avail = DoctorAvailability.query.filter_by(doctor_id=int(doc_id)).first()
            if not avail:
                flash(f'Doctor has not set any availability yet. Please select another doctor or check back later.', 'warning')
                return redirect(url_for('patient_book_appointment'))
            
            # Check if booking date falls within any availability range
            avail_start = datetime.strptime(avail.start_date, '%Y-%m-%d').date()
            avail_end = datetime.strptime(avail.end_date, '%Y-%m-%d').date()
            
            if not (avail_start <= booking_date <= avail_end):
                flash(f'Doctor is available from {avail.start_date} to {avail.end_date}. Please select a date within this range.', 'warning')
                return redirect(url_for('patient_book_appointment', doctor_id=doc_id))
            
            # Check if requested time is within doctor's availability window
            if time < avail.start_time or time > avail.end_time:
                flash(f'Doctor is only available from {avail.start_time} to {avail.end_time}. Please select a time within this window.', 'warning')
                return redirect(url_for('patient_book_appointment', doctor_id=doc_id))
        except Exception as e:
            print(f"Error checking availability: {str(e)}")
            flash('Error verifying doctor availability.', 'danger')
            return redirect(url_for('patient_book_appointment'))
        
        # Check for double-booking
        existing = Appointment.query.filter_by(doctor_id=doc_id, date=date, time=time).first()
        if existing:
            flash('This time slot is already booked. Please choose another.', 'warning')
            return redirect(url_for('patient_search_doctors'))
        
        # Check if patient has appointment at this time
        patient_conflict = Appointment.query.filter_by(patient_id=pat_id, date=date, time=time).first()
        if patient_conflict:
            flash('You already have an appointment at this time.', 'warning')
            return redirect(url_for('patient_search_doctors'))
        
        appt = Appointment(patient_id=pat_id, doctor_id=int(doc_id), date=date, time=time, reason=reason, status='Booked')
        try:
            db.session.add(appt)
            db.session.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient_appointments'))
        except Exception:
            db.session.rollback()
            flash('Error booking appointment.', 'danger')
            return redirect(url_for('patient_search_doctors'))
    
    # GET: show form with doctors dropdown
    doctors = Doctor.query.filter_by(is_blacklisted=False).all()
    selected_doctor = None
    availability = []
    if selected_doctor_id:
        selected_doctor = Doctor.query.get(int(selected_doctor_id))
        # Get availability for this doctor
        from models import DoctorAvailability
        try:
            availability = DoctorAvailability.query.filter_by(doctor_id=int(selected_doctor_id)).all()
        except Exception:
            availability = []
    return render_template('patient/book_appointment.html', doctors=doctors, selected_doctor=selected_doctor, selected_doctor_id=selected_doctor_id, availability=availability)


@app.route('/patient/appointments')
@role_required('patient')
def patient_appointments():
    from models import Appointment, Treatment
    pat_id = session.get('user_id')
    
    try:
        appointments = Appointment.query.filter_by(patient_id=pat_id).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    except Exception:
        appointments = []
    
    # Fetch treatments for each appointment
    treatments = {}
    for a in appointments:
        try:
            t = Treatment.query.filter_by(appointment_id=a.id).first()
            if t:
                treatments[a.id] = t
        except Exception:
            pass
    
    # Fetch doctor info for each appointment
    doctors_info = {}
    for a in appointments:
        try:
            doc = Doctor.query.get(a.doctor_id)
            if doc:
                doctors_info[a.id] = doc
        except Exception:
            pass
    
    return render_template('patient/appointments.html', appointments=appointments, treatments=treatments, doctors_info=doctors_info)


@app.route('/patient/appointment/<int:appt_id>/reschedule', methods=['GET', 'POST'])
@role_required('patient')
def patient_reschedule_appointment(appt_id):
    from models import Appointment
    pat_id = session.get('user_id')
    appt = Appointment.query.get_or_404(appt_id)
    
    if appt.patient_id != pat_id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('patient_appointments'))
    
    if request.method == 'POST':
        new_date = request.form.get('date', '').strip()
        new_time = request.form.get('time', '').strip()
        
        if not new_date or not new_time:
            flash('Date and time required.', 'warning')
            return redirect(url_for('patient_reschedule_appointment', appt_id=appt_id))
        
        # Check for conflicts
        conflict = Appointment.query.filter_by(doctor_id=appt.doctor_id, date=new_date, time=new_time).filter(Appointment.id != appt_id).first()
        if conflict:
            flash('This time slot is already booked.', 'warning')
            return redirect(url_for('patient_reschedule_appointment', appt_id=appt_id))
        
        appt.date = new_date
        appt.time = new_time
        try:
            db.session.commit()
            flash('Appointment rescheduled.', 'success')
            return redirect(url_for('patient_appointments'))
        except Exception:
            db.session.rollback()
            flash('Error rescheduling.', 'danger')
            return redirect(url_for('patient_reschedule_appointment', appt_id=appt_id))
    
    return render_template('patient/reschedule_appointment.html', appointment=appt)


@app.route('/patient/appointment/<int:appt_id>/cancel')
@role_required('patient')
def patient_cancel_appointment(appt_id):
    from models import Appointment
    pat_id = session.get('user_id')
    appt = Appointment.query.get_or_404(appt_id)
    
    if appt.patient_id != pat_id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('patient_appointments'))
    
    appt.status = 'Cancelled'
    try:
        db.session.commit()
        flash('Appointment cancelled.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error cancelling appointment.', 'danger')
    
    return redirect(url_for('patient_appointments'))


@app.route('/patient/appointment/<int:appt_id>/treatment')
@role_required('patient')
def patient_view_treatment(appt_id):
    from models import Appointment, Treatment
    pat_id = session.get('user_id')
    appt = Appointment.query.get_or_404(appt_id)
    
    if appt.patient_id != pat_id:
        flash('Not authorized.', 'danger')
        return redirect(url_for('patient_appointments'))
    
    treatment = Treatment.query.filter_by(appointment_id=appt_id).first()
    return render_template('patient/treatment_detail.html', appointment=appt, treatment=treatment)


@app.route('/patient/profile', methods=['GET', 'POST'])
@role_required('patient')
def patient_profile():
    pat_id = session.get('user_id')
    patient = Patient.query.get(pat_id)
    
    if request.method == 'POST':
        patient.name = request.form.get('name', '').strip() or patient.name
        patient.phone = request.form.get('phone', '').strip() or patient.phone
        patient.age = request.form.get('age', '').strip() or patient.age
        patient.gender = request.form.get('gender', '').strip() or patient.gender
        patient.address = request.form.get('address', '').strip() or patient.address
        
        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('patient_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
            return redirect(url_for('patient_profile'))
    
    return render_template('patient/edit_profile.html', patient=patient)
