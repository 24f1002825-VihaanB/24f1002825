from datetime import datetime, time, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ---------- Admin ----------

class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------- Department ----------

class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default="")

    doctors = db.relationship("Doctor", back_populates="department", cascade="all,delete")


# ---------- Doctor ----------

class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False)
    years_experience = db.Column(db.Integer, default=0)
    bio = db.Column(db.Text, default="")
    is_blacklisted = db.Column(db.Boolean, default=False)

    password_hash = db.Column(db.String(256), nullable=False)

    department = db.relationship("Department", back_populates="doctors")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all,delete")
    availability = db.relationship("DoctorAvailability", back_populates="doctor", cascade="all,delete")


# ---------- Patient ----------

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    gender = db.Column(db.String(20))
    address = db.Column(db.String(255))
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    medical_history = db.Column(db.Text, nullable=True)
    allergies = db.Column(db.String(255), nullable=True)
    current_medications = db.Column(db.String(255), nullable=True)

    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        cascade="all,delete"
    )


# ---------- Doctor Availability (time slots) ----------

class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availability"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    doctor = db.relationship("Doctor", back_populates="availability")

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "start_time", "end_time", name="uq_doctor_slot"),
    )


# ---------- Appointment ----------

class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)

    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    status = db.Column(db.String(20), default="Booked") 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    treatment = db.relationship(
        "Treatment",
        back_populates="appointment",
        uselist=False,
        cascade="all,delete",
    )

    __table_args__ = (
        # prevent double booking of the same slot for a doctor
        db.UniqueConstraint("doctor_id", "date", "start_time", "end_time", name="uq_doctor_apt_slot"),
    )

    def overlaps(self, other_start: time, other_end: time) -> bool:
        """Helper: check if this appointment overlaps a time window."""
        return not (self.end_time <= other_start or other_end <= self.start_time)


# ---------- Treatment / Medical History ----------

class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), unique=True, nullable=False
    )

    visit_type = db.Column(db.String(50), default="In-person")
    tests_done = db.Column(db.String(200))
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    appointment = db.relationship("Appointment", back_populates="treatment")
