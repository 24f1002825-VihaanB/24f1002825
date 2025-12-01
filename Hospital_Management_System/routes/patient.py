from datetime import datetime, date, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models.models import (
    db,
    Department,
    Doctor,
    Patient,
    DoctorAvailability,
    Appointment,
    Treatment,
)
from routes.auth import role_required

patient_bp = Blueprint("patient", __name__, template_folder="../templates")


# ---------- Dashboard (appointments + Find Doctors) ----------

@patient_bp.route("/dashboard")
@role_required("patient")
def dashboard():
    """Show the patient's own appointments and a link to find doctors."""
    pid = current_user.real_id
    patient = Patient.query.get_or_404(pid)

    appointments = (
        Appointment.query
        .filter_by(patient_id=pid)
        .order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .all()
    )

    return render_template(
        "patient/dashboard.html",
        patient=patient,
        appointments=appointments,
    )


# ---------- First step: choose department ----------

@patient_bp.route("/departments")
@role_required("patient")
def departments():
    """First step: patient chooses a department to see its doctors."""
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template("patient/departments.html", departments=departments)


# ---------- Browse doctors by department ----------

@patient_bp.route("/browse")
@role_required("patient")
def browse():
    """
    Let patient pick a department and then see active (non-blacklisted) doctors
    in that department.
    Expect ?dept=<id> in query string.
    """
    dept_id = request.args.get("dept", type=int)
    departments = Department.query.order_by(Department.name.asc()).all()
    doctors = []

    if dept_id:
        doctors = (
            Doctor.query
            .filter_by(department_id=dept_id, is_blacklisted=False)
            .order_by(Doctor.name.asc())
            .all()
        )

    return render_template(
        "patient/browse.html",
        depts=departments,
        docs=doctors,
        dept_id=dept_id,
    )


# ---------- See availability for a particular doctor ----------

@patient_bp.route("/doctor/<int:did>/availability")
@role_required("patient")
def availability(did):
    """Show available slots for a doctor for the coming 7 days."""
    doc = Doctor.query.get_or_404(did)

    if doc.is_blacklisted:
        flash(
            "This doctor is not available for booking. Please choose another doctor.",
            "warning",
        )
        return redirect(url_for("patient.browse"))

    today = date.today()
    end = today + timedelta(days=6)  # 7-day window (today + next 6 days)

    all_slots = (
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == did,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= end,
        )
        .order_by(
            DoctorAvailability.date.asc(),
            DoctorAvailability.start_time.asc(),
        )
        .all()
    )

    # booked slots for this doctor
    booked = {
        (a.date, a.start_time, a.end_time)
        for a in Appointment.query.filter_by(doctor_id=did)
        .filter(Appointment.status == "Booked")
        .all()
    }

    available_slots = [
        s for s in all_slots
        if (s.date, s.start_time, s.end_time) not in booked
    ]

    return render_template(
        "patient/availability.html",
        doc=doc,
        slots=available_slots,
    )


# ---------- Book appointment (POST-only) ----------

@patient_bp.route("/book", methods=["POST"])
@role_required("patient")
def book():
    """Book an appointment for the current patient in a selected slot."""
    slot_id = request.form.get("slot_id", type=int)
    if not slot_id:
        flash("Invalid slot selected.", "danger")
        return redirect(url_for("patient.dashboard"))

    slot = DoctorAvailability.query.get_or_404(slot_id)
    doc = slot.doctor

    if doc.is_blacklisted:
        flash(
            "This doctor is currently not accepting appointments.",
            "danger",
        )
        return redirect(url_for("patient.browse"))

    pid = current_user.real_id
    patient = Patient.query.get_or_404(pid)

    if patient.is_blacklisted:
        flash(
            "Your account is restricted. Please contact the hospital.",
            "danger",
        )
        return redirect(url_for("patient.dashboard"))

    # prevent double booking of same doctor slot
    existing = Appointment.query.filter_by(
        doctor_id=doc.id,
        date=slot.date,
        start_time=slot.start_time,
        end_time=slot.end_time,
    ).first()
    if existing:
        flash("This slot has already been booked. Please choose another.", "warning")
        return redirect(url_for("patient.availability", did=doc.id))

    ap = Appointment(
        patient_id=patient.id,
        doctor_id=doc.id,
        date=slot.date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status="Booked",
    )
    db.session.add(ap)
    db.session.commit()

    flash("Appointment booked successfully.", "success")
    return redirect(url_for("patient.dashboard"))


# ---------- Cancel appointment ----------

@patient_bp.route("/appointment/<int:aid>/cancel", methods=["POST"])
@role_required("patient")
def cancel_appointment(aid):
    """Allow patient to cancel their own booked appointment."""
    pid = current_user.real_id
    ap = Appointment.query.get_or_404(aid)

    if ap.patient_id != pid:
        flash("You are not allowed to cancel this appointment.", "danger")
        return redirect(url_for("patient.dashboard"))

    if ap.status != "Booked":
        flash("Only booked appointments can be cancelled.", "warning")
        return redirect(url_for("patient.dashboard"))

    ap.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("patient.dashboard"))


# ---------- Patient profile (view + edit own) ----------

@patient_bp.route("/profile", methods=["GET", "POST"])
@role_required("patient")
def profile():
    pid = current_user.real_id
    patient = Patient.query.get_or_404(pid)

    if request.method == "POST":
        patient.name = request.form.get("name") or patient.name
        patient.address = request.form.get("address")
        patient.gender = request.form.get("gender")
        patient.medical_history = request.form.get("medical_history")
        patient.allergies = request.form.get("allergies")
        patient.current_medications = request.form.get("current_medications")

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("patient.profile"))

    return render_template("patient/profile.html", patient=patient)


# ---------- Patient's own appointment history ----------

@patient_bp.route("/history")
@role_required("patient")
def history():
    """Show the logged-in patient's appointment and treatment history."""
    pid = current_user.real_id
    patient = Patient.query.get_or_404(pid)

    aps = (
        Appointment.query
        .filter_by(patient_id=pid)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template("patient/history.html", patient=patient, aps=aps)


# ---------- Appointment detail (with treatment) ----------

@patient_bp.route("/appointment/<int:aid>")
@role_required("patient")
def appointment_detail(aid):
    """Show full details (including treatment) for a single appointment."""
    ap = Appointment.query.get_or_404(aid)

    # Security: only the patient who owns this appointment can view it
    if ap.patient_id != current_user.real_id:
        flash("Unauthorized access to appointment.", "danger")
        return redirect(url_for("patient.dashboard"))

    return render_template("patient/appointment_detail.html", ap=ap)
