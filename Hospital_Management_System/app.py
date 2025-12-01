from flask import Flask
from config import Config
from models.models import db
from routes.auth import auth_bp, login_manager
from routes.admin import admin_bp
from routes.doctor import doctor_bp
from routes.patient import patient_bp
from flask import render_template

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.choose_role"

    # blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(patient_bp, url_prefix="/patient")

    @app.route("/")
    def home():
        return render_template("auth/choose_role.html")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
