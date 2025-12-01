from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash

from models.models import db, Admin, Doctor, Patient
from functools import wraps

auth_bp = Blueprint("auth", __name__, template_folder="../templates")
login_manager = LoginManager()


# --- Session user wrapper (supports 3 roles with one LoginManager) ---
class SessionUser(UserMixin):
    """
    Lightweight session wrapper so we can keep role info in current_user
    without storing full model instances.

    Fields:
      - role: "admin" | "doctor" | "patient"
      - real_id: primary key in the corresponding table
      - name: display name
      - id: alias to real_id so current_user.id works
    """

    def __init__(self, role: str, real_id: int, name: str):
        self.role = role
        self.real_id = real_id
        self.name = name
        # ✅ important: flask-login and your code expect `.id`
        self.id = real_id

    def get_id(self) -> str:
        # stored in the session; user_loader uses this to reconstruct user
        return f"{self.role}:{self.real_id}"


@login_manager.user_loader
def load_user(user_id: str):
    """
    Reconstruct SessionUser from the ID stored in the session.
    user_id is in the form "role:real_id" (e.g., "patient:3").
    """
    try:
        role, rid = user_id.split(":")
        rid = int(rid)
    except Exception:
        return None

    if role == "admin":
        admin = Admin.query.get(rid)
        return SessionUser("admin", rid, admin.name) if admin else None

    if role == "doctor":
        d = Doctor.query.get(rid)
        return SessionUser("doctor", rid, d.name) if d else None

    if role == "patient":
        p = Patient.query.get(rid)
        return SessionUser("patient", rid, p.name) if p else None

    return None


# --- role guard ---
def role_required(role):
    """
    Decorator to ensure the logged-in user has the given role.
    Uses SessionUser.role that we stored at login.
    """
    def decorator(view):
        @wraps(view)
        def inner(*args, **kwargs):
            if not current_user.is_authenticated or getattr(current_user, "role", None) != role:
                flash("Unauthorized.", "danger")
                return redirect(url_for("auth.choose_role"))
            return view(*args, **kwargs)
        return inner
    return decorator


# ---------- UI: choose role ----------
@auth_bp.route("/login")
def choose_role():
    return render_template("auth/choose_role.html")


# ---------- Admin login ----------
@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(SessionUser("admin", admin.id, admin.name))
            return redirect(url_for("admin.dashboard"))

        flash("Invalid admin credentials.", "danger")

    return render_template("auth/admin_login.html")


# ---------- Doctor login (doctors are added by admin only) ----------
@auth_bp.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        doc = Doctor.query.filter_by(email=email).first()

        if not doc:
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.doctor_login"))

        if doc.is_blacklisted:
            flash("Access denied. You have been blacklisted. Contact admin.", "danger")
            return redirect(url_for("auth.doctor_login"))

        if not check_password_hash(doc.password_hash, password):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.doctor_login"))

        login_user(SessionUser("doctor", doc.id, doc.name))
        return redirect(url_for("doctor.dashboard"))

    return render_template("auth/doctor_login.html")


# ---------- Patient register + login ----------
@auth_bp.route("/patient/register", methods=["GET", "POST"])
def patient_register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        gender = request.form.get("gender")
        address = request.form.get("address")

        medical_history = request.form.get("medical_history")
        allergies = request.form.get("allergies")
        current_medications = request.form.get("current_medications")

        if Patient.query.filter_by(email=email).first():
            flash("Email already registered.", "warning")
        else:
            p = Patient(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                gender=gender,
                address=address,
                medical_history=medical_history,
                allergies=allergies,
                current_medications=current_medications,
                created_at=datetime.utcnow(),
            )
            db.session.add(p)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.patient_login"))

    return render_template("auth/patient_register.html")



@auth_bp.route("/patient/login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""

        p = Patient.query.filter_by(email=email).first()

        if not p or not check_password_hash(p.password_hash, password):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.patient_login"))

        if p.is_blacklisted:
            flash("Your account is restricted. Please contact the hospital.", "danger")
            return redirect(url_for("auth.patient_login"))

        login_user(SessionUser("patient", p.id, p.name))
        return redirect(url_for("patient.dashboard"))

    return render_template("auth/patient_login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.choose_role"))
