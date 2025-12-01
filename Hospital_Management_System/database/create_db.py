from datetime import datetime, date, time, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from models.models import db, Admin, Department, Doctor, Patient, DoctorAvailability


ADMIN_EMAIL = "admin@hms.local"
ADMIN_PASSWORD = "Admin@123"

DOCTOR_DEFAULT_PASSWORD = "Doctor@123"
PATIENT_DEFAULT_PASSWORD = "Patient@123"


def seed_minimal_data(app):
    """Create admin, some departments, doctors, a demo patient and availability slots."""
    with app.app_context():
        # --- Admin ---
        if not Admin.query.filter_by(email=ADMIN_EMAIL).first():
            admin = Admin(
                name="System Admin",
                email=ADMIN_EMAIL,
                password_hash=generate_password_hash(ADMIN_PASSWORD),
            )
            db.session.add(admin)

        # --- Departments ---
        dept_names = ["Cardiology", "Orthopedics", "Neurology", "Pediatrics"]
        departments = {}
        for name in dept_names:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, description=f"{name} department.")
                db.session.add(dept)
            departments[name] = dept

        db.session.flush()  

        # --- Doctors (with password_hash) ---
        doctors_seed = [
            ("Dr. Abode", "abode@hms.local", "Cardiology", 12),
            ("Dr. Pranit", "pranit@hms.local", "Orthopedics", 8),
            ("Dr. Npop", "npop@hms.local", "Neurology", 10),
        ]

        for name, email, dept_name, years in doctors_seed:
            if Doctor.query.filter_by(email=email).first():
                continue
            dept = departments.get(dept_name)
            if not dept:
                continue
            doc = Doctor(
                name=name,
                email=email,
                department_id=dept.id,
                years_experience=years,
                bio="",
                is_blacklisted=False,
                password_hash=generate_password_hash(DOCTOR_DEFAULT_PASSWORD),
            )
            db.session.add(doc)

        # --- Demo Patient ---
        demo_email = "demo.patient@hms.local"
        if not Patient.query.filter_by(email=demo_email).first():
            p = Patient(
                name="Demo Patient",
                email=demo_email,
                password_hash=generate_password_hash(PATIENT_DEFAULT_PASSWORD),
                gender="Other",
                address="Demo address",
                medical_history="Hypertension, under regular follow-up.",
                allergies="None known",
                current_medications="Amlodipine 5mg OD",
            )

            db.session.add(p)

        db.session.commit()

        # --- Availability slots for each doctor (next 7 days, 2 slots per day) ---
        doctors = Doctor.query.all()
        today = date.today()

        for doc in doctors:
            for offset in range(7):
                d = today + timedelta(days=offset)

                # two slots per day
                slots = [
                    (time(10, 0), time(12, 0)),
                    (time(16, 0), time(18, 0)),
                ]

                for start, end in slots:
                    exists = DoctorAvailability.query.filter_by(
                        doctor_id=doc.id,
                        date=d,
                        start_time=start,
                        end_time=end,
                    ).first()
                    if exists:
                        continue

                    slot = DoctorAvailability(
                        doctor_id=doc.id,
                        date=d,
                        start_time=start,
                        end_time=end,
                    )
                    db.session.add(slot)

        db.session.commit()
        print("✔ Database seeded with admin, departments, doctors, patient and availability.")


def create_and_seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✔ All tables created.")
    seed_minimal_data(app)


if __name__ == "__main__":
    create_and_seed()
