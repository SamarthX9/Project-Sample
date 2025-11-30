# db_init.py
import os
from main import app, db  # use the same app config and db
from models import Admin, Department, Doctor, Patient, Appointment, Treatment, DoctorAvailability

def initialize_db():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_dir = os.path.join(basedir, "database")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # create tables
    with app.app_context():
        db.create_all()

        # seed default admin (programmatic insertion)
        if not Admin.query.filter_by(admin_username='admin').first():
            admin = Admin(admin_username='admin', name='Hospital Admin', email='admin@hospital.com')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ Inserted default admin -> username: admin  password: admin123")
        else:
            print("✓ Default admin already present.")

        # seed sample departments
        default_departments = [
            ('Cardiology', 'Heart and cardiovascular diseases'),
            ('Neurology', 'Nervous system and brain disorders'),
            ('Orthopedics', 'Bone and joint disorders'),
            ('Pediatrics', 'Medical care for children'),
            ('General Practice', 'General medical care'),
        ]
        for dept_name, dept_desc in default_departments:
            if not Department.query.filter_by(name=dept_name).first():
                dept = Department(name=dept_name, description=dept_desc)
                db.session.add(dept)
        db.session.commit()
        print("✓ Departments seeded.")

        # seed sample doctors
        if not Doctor.query.first():
            doctors_data = [
                ('Dr. John Smith', 'john@hospital.com', '9876543210', 'Cardiology'),
                ('Dr. Sarah Jones', 'sarah@hospital.com', '9876543211', 'Neurology'),
                ('Dr. Mike Johnson', 'mike@hospital.com', '9876543212', 'Orthopedics'),
            ]
            for name, email, phone, spec in doctors_data:
                doc = Doctor(name=name, email=email, phone=phone, specialization=spec)
                doc.set_password('doctor123')
                db.session.add(doc)
            db.session.commit()
            print("✓ Sample doctors seeded.")

        # seed sample patients
        if not Patient.query.first():
            patients_data = [
                ('John Doe', 'john@patient.com', '8765432100', 30, 'Male'),
                ('Jane Doe', 'jane@patient.com', '8765432101', 28, 'Female'),
                ('Robert Brown', 'robert@patient.com', '8765432102', 45, 'Male'),
            ]
            for name, email, phone, age, gender in patients_data:
                pat = Patient(name=name, email=email, phone=phone, age=age, gender=gender)
                pat.set_password('patient123')
                db.session.add(pat)
            db.session.commit()
            print("✓ Sample patients seeded.")
        else:
            print("✓ Patients already present.")

if __name__ == "__main__":
    initialize_db()

