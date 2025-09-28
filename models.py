from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='faculty')  # 'admin', 'department_head', 'faculty'
    department = db.Column(db.String(100), nullable=True)
    approval_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Classroom(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # 'Lecture' or 'Lab'
    department = db.Column(db.String(100), nullable=True)
    is_available = db.Column(db.Boolean, default=True)

class Faculty(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subjects = db.Column(db.Text, nullable=False)  # JSON string of subject list
    leaves_per_month = db.Column(db.Integer, default=1)
    unavailable_slots = db.Column(db.Text, nullable=True)  # JSON string of unavailable slots
    department = db.Column(db.String(100), nullable=True)
    max_classes_per_day = db.Column(db.Integer, default=4)
    email = db.Column(db.String(120), nullable=True)

class Subject(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.String(50), db.ForeignKey('faculty.id'), nullable=False)
    batches = db.Column(db.Text, nullable=False)  # JSON string of batch IDs
    per_week = db.Column(db.Integer, nullable=False)
    needs_lab = db.Column(db.Boolean, default=False)
    fixed_slots = db.Column(db.Text, nullable=True)  # JSON string of fixed slot assignments
    department = db.Column(db.String(100), nullable=True)
    credits = db.Column(db.Integer, default=1)

class Batch(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    shift = db.Column(db.String(50), default='morning')  # 'morning', 'evening'
    electives = db.Column(db.Text, nullable=True)  # JSON string of elective subjects

class Shift(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(100), nullable=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(50), default='pending_approval')  # pending_approval, approved, rejected
    department = db.Column(db.String(100), nullable=True)
    shift = db.Column(db.String(50), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
    slots = db.relationship('Slot', backref='timetable', lazy=True, cascade="all, delete-orphan")

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)

    subject_id = db.Column(db.String(50), nullable=False)
    subject_name = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.String(50), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    batch_id = db.Column(db.String(50), nullable=False)
    batch_name = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.String(50), nullable=False)
    day = db.Column(db.String(20), nullable=False)
    slot_index = db.Column(db.Integer, nullable=False)

    approval_status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, change_requested
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    change_reason = db.Column(db.Text, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)