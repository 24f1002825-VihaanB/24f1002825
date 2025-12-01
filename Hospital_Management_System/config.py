import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-prod")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "hospital.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Default admin bootstrap (used by create_db.py)
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin@hms.local")
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "Admin@123")  # change before viva
DEFAULT_ADMIN_NAME = os.environ.get("ADMIN_NAME", "Super Admin")
