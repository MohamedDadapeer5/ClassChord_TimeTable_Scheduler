from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False, default='faculty') # 'admin' or 'faculty'
    approval_points = db.Column(db.Integer, default=0)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(50), default='pending_approval') # pending_approval, approved
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
    
    approval_status = db.Column(db.String(50), default='pending') # pending, approved, change_requested
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    change_reason = db.Column(db.Text, nullable=True)