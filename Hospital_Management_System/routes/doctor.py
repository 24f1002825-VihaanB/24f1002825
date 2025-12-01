from datetime import datetime, date, time, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models.models import (
    db,
    Doctor,
    Patient,
    Appointment,
    Treatment,
    DoctorAvailability,
)
from routes.auth import role_required

doctor_bp = Blueprint("doctor", __name__, template_folder="../templates")


# ---------- Doctor dashboard ----------

@doctor_bp.route("/dashboard")
@role_required("doctor")
def dashboard():
    """Doctor view: upcoming + recently completed appointments."""
    did = current_user.real_id

    upcoming = (
        Appointment.query
        .filter_by(doctor_id=did, status="Booked")
        .order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .all()
    )

    completed = (
        Appointment.query
        .filter_by(doctor_id=did, status="Completed")
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "doctor/dashboard.html",
        upcoming=upcoming,
        completed=completed,
    )


# ---------- Mark / edit appointment as completed ----------

@doctor_bp.route("/appointment/<int:aid>/complete", methods=["GET", "POST"])
@role_required("doctor")
def complete_appointment(aid):
    """Mark an appointment as completed and record treatment details."""
    did = current_user.real_id
    ap = Appointment.query.get_or_404(aid)

    if ap.doctor_id != did:
        flash("Unauthorized.", "danger")
        return redirect(url_for("doctor.dashboard"))

    if request.method == "POST":
        visit_type = request.form.get("visit_type", "In-person")
        tests_done = request.form.get("tests_done")
        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription")
        notes = request.form.get("notes")

        ap.status = "Completed"

        if ap.treatment is None:
            ap.treatment = Treatment(
                visit_type=visit_type,
                tests_done=tests_done,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes,
            )
        else:
            t = ap.treatment
            t.visit_type = visit_type
            t.tests_done = tests_done
            t.diagnosis = diagnosis
            t.prescription = prescription
            t.notes = notes

        db.session.commit()
        flash("Visit marked as completed and treatment saved.", "success")
        return redirect(url_for("doctor.dashboard"))

    return render_template("doctor/complete.html", ap=ap)


# ---------- Doctor cancels an appointment ----------

@doctor_bp.route("/appointment/<int:aid>/cancel", methods=["POST"])
@role_required("doctor")
def cancel_appointment(aid):
    """Allow the doctor to cancel their own booked appointment."""
    did = current_user.real_id
    ap = Appointment.query.get_or_404(aid)

    if ap.doctor_id != did:
        flash("Unauthorized.", "danger")
        return redirect(url_for("doctor.dashboard"))

    if ap.status != "Booked":
        flash("Only booked appointments can be cancelled.", "warning")
        return redirect(url_for("doctor.dashboard"))

    ap.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("doctor.dashboard"))


# ---------- View history for a particular patient (with this doctor) ----------

@doctor_bp.route("/patient/<int:pid>/history")
@role_required("doctor")
def patient_history(pid):
    """Show all appointments this patient has had with the doctor."""
    did = current_user.real_id
    patient = Patient.query.get_or_404(pid)

    aps = (
        Appointment.query
        .filter_by(patient_id=pid, doctor_id=did)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template("doctor/history.html", patient=patient, aps=aps)


# ---------- Doctor profile (view only) ----------

@doctor_bp.route("/profile")
@role_required("doctor")
def profile():
    """Simple read-only view of the doctor's profile."""
    did = current_user.real_id
    doc = Doctor.query.get_or_404(did)
    return render_template("doctor/profile.html", doc=doc)


# ---------- Doctor manages their availability (next 7 days) ----------

@doctor_bp.route("/availability", methods=["GET", "POST"])
@role_required("doctor")
def manage_availability():
    """
    Doctor can define availability for the next 7 days.
    Two fixed slots per day (10–12, 4–6) for simplicity,
    matching the project requirements.
    """
    did = current_user.real_id
    today = date.today()
    end = today + timedelta(days=6)  # 7 days window

    # Fixed slot definitions (can be extended if needed)
    slot_defs = [
        (time(10, 0), time(12, 0)),
        (time(16, 0), time(18, 0)),
    ]

    if request.method == "POST":
        # Form sends a list of encoded slots: "YYYY-MM-DD|HH:MM|HH:MM"
        selected_values = request.form.getlist("slots")

        # Clear existing availability within the window
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == did,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= end,
        ).delete(synchronize_session=False)

        # Recreate based on selected checkboxes
        for value in selected_values:
            try:
                d_str, start_str, end_str = value.split("|")
                d = datetime.strptime(d_str, "%Y-%m-%d").date()
                st = datetime.strptime(start_str, "%H:%M").time()
                et = datetime.strptime(end_str, "%H:%M").time()
            except ValueError:
                continue

            db.session.add(
                DoctorAvailability(
                    doctor_id=did,
                    date=d,
                    start_time=st,
                    end_time=et,
                )
            )

        db.session.commit()
        flash("Availability updated for the next 7 days.", "success")
        return redirect(url_for("doctor.manage_availability"))

    # For GET, load current availability and build context
    existing = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == did,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= end,
    ).all()

    existing_set = {
        (a.date, a.start_time, a.end_time) for a in existing
    }

    days = []
    for offset in range(7):
        d = today + timedelta(days=offset)
        slots = []
        for st, et in slot_defs:
            key = (d, st, et)
            slots.append(
                {
                    "date": d,
                    "label": f"{st.strftime('%I:%M %p')} – {et.strftime('%I:%M %p')}",
                    "value": f"{d.isoformat()}|{st.strftime('%H:%M')}|{et.strftime('%H:%M')}",
                    "selected": key in existing_set,
                }
            )
        days.append({"date": d, "slots": slots})

    return render_template("doctor/availability.html", days=days)
