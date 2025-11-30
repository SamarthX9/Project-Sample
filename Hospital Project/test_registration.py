#!/usr/bin/env python
# test_registration.py - Test if registration works

from main import app, db
from models import Patient, Doctor

def test_patient_registration():
    with app.app_context():
        # Check if test patient exists
        test_email = "test_patient@test.com"
        existing = Patient.query.filter_by(email=test_email).first()
        
        if existing:
            print(f"✓ Test patient already exists: {test_email}")
            return
        
        # Create test patient
        patient = Patient(name="Test Patient", email=test_email, phone="1234567890", age=25, gender="Male")
        patient.set_password("testpass123")
        
        try:
            db.session.add(patient)
            db.session.commit()
            print(f"✓ Test patient created successfully: {test_email}")
            
            # Verify it was saved
            saved_patient = Patient.query.filter_by(email=test_email).first()
            if saved_patient:
                print(f"✓ Test patient verified in database: ID={saved_patient.id}")
            else:
                print(f"✗ Test patient NOT found in database after save!")
        except Exception as e:
            print(f"✗ Error creating test patient: {str(e)}")
            db.session.rollback()

def test_doctor_registration():
    with app.app_context():
        # Check if test doctor exists
        test_email = "test_doctor@test.com"
        existing = Doctor.query.filter_by(email=test_email).first()
        
        if existing:
            print(f"✓ Test doctor already exists: {test_email}")
            return
        
        # Create test doctor
        doctor = Doctor(name="Test Doctor", email=test_email, phone="9876543210", specialization="General")
        doctor.set_password("docpass123")
        
        try:
            db.session.add(doctor)
            db.session.commit()
            print(f"✓ Test doctor created successfully: {test_email}")
            
            # Verify it was saved
            saved_doctor = Doctor.query.filter_by(email=test_email).first()
            if saved_doctor:
                print(f"✓ Test doctor verified in database: ID={saved_doctor.id}")
            else:
                print(f"✗ Test doctor NOT found in database after save!")
        except Exception as e:
            print(f"✗ Error creating test doctor: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    print("Testing Patient Registration...")
    test_patient_registration()
    print("\nTesting Doctor Registration...")
    test_doctor_registration()
    print("\nTest completed!")
