# models.py
from datetime import datetime, date, time
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------ Admin ------------------
class Admin(db.Model):
    __tablename__ = 'admin'
    admin_username = db.Column(db.String(50), primary_key=True)  # matches sample style
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(150), nullable=True)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


# ------------------ Department ------------------
class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.String(500))

    doctors = db.relationship('Doctor', back_populates='department', cascade='all, delete-orphan')


# ------------------ Doctor ------------------
class Doctor(db.Model):
    __tablename__ = 'doctor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=True)
    specialization = db.Column(db.String(150))
    password_hash = db.Column(db.String(255), nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    department = db.relationship('Department', back_populates='doctors')
    appointments = db.relationship('Appointment', back_populates='doctor', cascade='all, delete-orphan')
    availability = db.relationship('DoctorAvailability', back_populates='doctor', cascade='all, delete-orphan')

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


# ------------------ Patient ------------------
class Patient(db.Model):
    __tablename__ = 'patient'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(300))
    password_hash = db.Column(db.String(255), nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointments = db.relationship('Appointment', back_populates='patient', cascade='all, delete-orphan')

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


# ------------------ Appointment ------------------
class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)   # store as 'YYYY-MM-DD' for simplicity
    time = db.Column(db.String(5), nullable=False)    # store as 'HH:MM'
    status = db.Column(db.String(20), default='Booked')  # Booked / Completed / Cancelled
    reason = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship('Patient', back_populates='appointments')
    doctor = db.relationship('Doctor', back_populates='appointments')
    treatment = db.relationship('Treatment', back_populates='appointment', uselist=False, cascade='all, delete-orphan')

    # Note: We'll enforce no double-book with app logic + a DB-unique index if desired in raw SQL.


# ------------------ Treatment ------------------
class Treatment(db.Model):
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True, nullable=False)
    diagnosis = db.Column(db.String(1000))
    prescription = db.Column(db.String(1000))
    notes = db.Column(db.String(2000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship('Appointment', back_populates='treatment')


# ------------------ Doctor Availability ------------------
class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)    # 'YYYY-MM-DD' - from date
    end_date = db.Column(db.String(10), nullable=False)      # 'YYYY-MM-DD' - to date
    start_time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    end_time = db.Column(db.String(5), nullable=False)    # 'HH:MM'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('Doctor', back_populates='availability')

    doctor = db.relationship('Doctor', back_populates='availability')
