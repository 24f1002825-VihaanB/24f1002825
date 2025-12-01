from datetime import datetime, date, time, timedelta
from models.models import db, Department, Doctor, Patient, Appointment, DoctorAvailability, Admin
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash
from routes.auth import role_required

admin_bp = Blueprint("admin", __name__, template_folder="../templates")


# ---------- helpers ----------

def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------- dashboard ----------

@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    counts = {
        "doctors": Doctor.query.count(),
        "patients": Patient.query.count(),
        "appointments": Appointment.query.count(),
    }

    upcoming = (
        Appointment.query.filter(Appointment.status == "Booked")
        .order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .limit(10)
        .all()
    )

    return render_template("admin/dashboard.html", counts=counts, upcoming=upcoming)


# ---------- doctor CRUD + default availability ----------

@admin_bp.route("/doctors", methods=["GET", "POST"])
@role_required("admin")
def doctors():
    depts = Department.query.order_by(Department.name.asc()).all()

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        dept_id = to_int(request.form.get("department_id"))
        years = to_int(request.form.get("years_experience"))
        password = request.form.get("password") or "Doctor@123"

        if not name or not email or not dept_id:
            flash("Name, email and department are required.", "warning")
            return redirect(url_for("admin.doctors"))

        if Doctor.query.filter_by(email=email).first():
            flash("Doctor already exists with this email.", "warning")
            return redirect(url_for("admin.doctors"))

        hashed_pw = generate_password_hash(password)

        # create doctor
        doc = Doctor(
            name=name,
            email=email,
            department_id=dept_id,
            years_experience=years,
            password_hash=hashed_pw,
        )
        db.session.add(doc)
        db.session.commit()

        # seed 7 days x 2 slots/day default availability
        today = date.today()
        slot_defs = [
            (time(10, 0), time(12, 0)),
            (time(16, 0), time(18, 0)),
        ]

        for offset in range(7):
            day = today + timedelta(days=offset)
            for start, end in slot_defs:
                exists = DoctorAvailability.query.filter_by(
                    doctor_id=doc.id,
                    date=day,
                    start_time=start,
                    end_time=end,
                ).first()
                if exists:
                    continue

                db.session.add(
                    DoctorAvailability(
                        doctor_id=doc.id,
                        date=day,
                        start_time=start,
                        end_time=end,
                    )
                )

        db.session.commit()

        flash("Doctor added successfully, with 7 days of availability.", "success")
        return redirect(url_for("admin.doctors"))

    doctors = Doctor.query.order_by(Doctor.id.desc()).all()
    return render_template("admin/doctors.html", doctors=doctors, depts=depts)


@admin_bp.route("/doctor/<int:did>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_doctor(did):
    """
    Acts as the doctor's dedicated profile page for the admin:
    - view details
    - edit name/email/department/experience
    - optionally change password
    - optionally change blacklist status
    """
    doc = Doctor.query.get_or_404(did)
    depts = Department.query.order_by(Department.name.asc()).all()

    if request.method == "POST":
        doc.name = (request.form.get("name") or "").strip()
        doc.email = (request.form.get("email") or "").strip()
        doc.department_id = to_int(request.form.get("department_id"))
        doc.years_experience = to_int(request.form.get("years_experience"))

        # optional password change
        new_password = request.form.get("password")
        if new_password:
            doc.password_hash = generate_password_hash(new_password)

        # optional blacklist toggle from the profile form
        # (safe even if the template doesn't send this field)
        doc.is_blacklisted = bool(request.form.get("is_blacklisted"))

        db.session.commit()
        flash("Doctor profile updated.", "success")
        # stay on this doctor's profile page
        return redirect(url_for("admin.edit_doctor", did=doc.id))

    return render_template("admin/edit_doctor.html", doc=doc, depts=depts)


@admin_bp.route("/doctor/<int:did>/delete")
@role_required("admin")
def delete_doctor(did):
    doc = Doctor.query.get_or_404(did)
    db.session.delete(doc)
    db.session.commit()
    flash("Doctor deleted.", "info")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/doctor/<int:did>/toggle_blacklist")
@role_required("admin")
def toggle_blacklist(did):
    doc = Doctor.query.get_or_404(did)
    doc.is_blacklisted = not doc.is_blacklisted
    db.session.commit()
    flash("Doctor status updated.", "info")
    return redirect(url_for("admin.doctors"))


# ---------- doctor availability management ----------

@admin_bp.route("/doctor/<int:did>/availability", methods=["GET", "POST"])
@role_required("admin")
def doctor_availability(did):
    doc = Doctor.query.get_or_404(did)

    if request.method == "POST":
        date_str = request.form.get("date")
        start_str = request.form.get("start_time")
        end_str = request.form.get("end_time")

        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            st = datetime.strptime(start_str, "%H:%M").time()
            et = datetime.strptime(end_str, "%H:%M").time()
        except (TypeError, ValueError):
            flash("Invalid date or time.", "danger")
            return redirect(url_for("admin.doctor_availability", did=did))

        exists = DoctorAvailability.query.filter_by(
            doctor_id=did, date=d, start_time=st, end_time=et
        ).first()
        if exists:
            flash("This slot already exists.", "warning")
        else:
            db.session.add(
                DoctorAvailability(
                    doctor_id=did, date=d, start_time=st, end_time=et
                )
            )
            db.session.commit()
            flash("Availability slot added.", "success")

        return redirect(url_for("admin.doctor_availability", did=did))

    slots = (
        DoctorAvailability.query.filter_by(doctor_id=did)
        .order_by(DoctorAvailability.date.asc(), DoctorAvailability.start_time.asc())
        .all()
    )
    return render_template("admin/doctor_availability.html", doc=doc, slots=slots)


@admin_bp.route("/availability/<int:aid>/delete")
@role_required("admin")
def delete_availability(aid):
    slot = DoctorAvailability.query.get_or_404(aid)
    did = slot.doctor_id
    db.session.delete(slot)
    db.session.commit()
    flash("Availability slot removed.", "info")
    return redirect(url_for("admin.doctor_availability", did=did))


# ---------- search -----------

@admin_bp.route("/search")
@role_required("admin")
def search():
    q = (request.args.get("q") or "").strip()
    date_str = request.args.get("date")

    today = date.today()
    if date_str:
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            day = today
    else:
        day = today

    doctors = []
    patients = []
    upcoming = []
    completed = []

    if q:
        like = f"%{q}%"

        doctors = (
            Doctor.query
            .join(Department)
            .filter(
                or_(
                    Doctor.name.ilike(like),
                    Department.name.ilike(like),
                )
            )
            .order_by(Doctor.name.asc())
            .all()
        )

        patients = (
            Patient.query
            .filter(Patient.name.ilike(like))
            .order_by(Patient.name.asc())
            .all()
        )

        # include Department join here because we filter on Department.name
        base = (
            Appointment.query
            .join(Doctor)
            .join(Department)
            .join(Patient)
            .filter(Appointment.date == day)
            .filter(
                or_(
                    Doctor.name.ilike(like),
                    Patient.name.ilike(like),
                    Department.name.ilike(like)
                )
            )
        )
    else:
        base = (
            Appointment.query
            .join(Doctor)
            .join(Patient)
            .filter(Appointment.date == day)
        )

    upcoming = (
        base.filter(Appointment.status == "Booked")
            .order_by(Appointment.start_time.asc())
            .all()
    )

    completed = (
        base.filter(Appointment.status == "Completed")
            .order_by(Appointment.start_time.asc())
            .all()
    )

    return render_template(
        "admin/search.html",
        day=day,
        q=q,
        doctors=doctors,
        patients=patients,
        upcoming=upcoming,
        completed=completed,
    )


# ---------- appointment management ----------

@admin_bp.route("/appointment/<int:aid>/cancel")
@role_required("admin")
def cancel_appointment(aid):
    ap = Appointment.query.get_or_404(aid)
    ap.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/profile", methods=["GET", "POST"])
@role_required("admin")
def profile():
    admin = Admin.query.get_or_404(current_user.real_id)

    if request.method == "POST":
        admin.name = request.form.get("name") or admin.name
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("admin.profile"))

    return render_template("admin/profile.html", admin=admin)
