# Hospital Management System (HMS)

A clean and modular Hospital Management System built using Flask, offering dedicated role-based dashboards for Admins, Doctors, and Patients.  
The system follows a structured MVC pattern using Blueprints, ensuring scalability and clarity.

---

## Features

### **Admin**
- Manage departments  
- Add, edit, delete, and blacklist doctors  
- View and search doctors & patients  
- View appointments summary (upcoming & completed)  
- Access patient medical history  

### **Doctor**
- View upcoming and past appointments  
- Complete appointments with treatment details  
- Add diagnosis, prescription, notes, tests done  
- View each patient's medical history and past treatments  

### **Patient**
- Register, login, update profile  
- Add medical history, allergies, and current medications  
- Browse departments  
- View doctors (excluding blacklisted doctors)  
- View 7-day doctor availability (2 slots per day)  
- Book and cancel appointments  
- View full appointment history & treatment details  

---

## Tech Stack
- **Python 3.10+**
- **Flask**
- **Flask-Login**
- **SQLAlchemy ORM**
- **SQLite**
- **Bootstrap 5**
- **Jinja2 Templates**

---

## Installation Guide

### **1. Create Virtual Environment**
```bash
python -m venv venv
```

### **2. Activate Environment**
**Windows**
```bash
venv\Scripts\activate
```

**Mac/Linux**
```bash
source venv/bin/activate
```

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4. Initialize the Database (Creates tables and seeds admin + doctors + patient + availability)**
```bash
python -m database.create_db
```

### **5. Run the Application**
```bash
python app.py
```

The system will be available at:

```
http://127.0.0.1:5000
```

---

## Default Login Credentials

### **Admin**
- Email: `admin@hms.local`  
- Password: `Admin@123`

### **Doctors (Seeded Examples)**
- Password for all seeded doctors: `Doctor@123`

### **Patients**
- Create your own account through the patient registration page.

---

## Project Structure

```
HMS/
├── app.py
├── models/
│   └── models.py
├── routes/
│   ├── auth.py
│   ├── admin.py
│   ├── doctor.py
│   └── patient.py
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── admin/
│   ├── doctor/
│   └── patient/
├── static/
│   ├── css/
│   └── js/
└── database/
    └── create_db.py
```

---

## Notes
- All UI pages use a consistent Bootstrap 5 theme.
- Strict role separation ensures secure access.
- Doctor availability auto-generates 7 days x 2 slots/day.
- Flash messages disappear automatically after a short timeout.
- Blacklisted doctors cannot log in or appear to patients.

---

## License
This project is intended for academic and learning purposes.

