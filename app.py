from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from collections import defaultdict
import random
import copy
import os
from models import db, User, Timetable, Slot, Classroom, Faculty, Subject, Batch, Shift
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Temporal Harmony Algorithm ---
class TemporalHarmonyScheduler:
    def __init__(self, config, rooms, teachers, batches, subjects):
        self.config = config
        self.rooms = rooms
        self.teachers = teachers
        self.batches = batches
        self.subjects = subjects
        self.hms = config.get('HARMONY_MEMORY_SIZE', 20)
        self.par = config.get('PITCH_ADJUSTMENT_RATE', 0.3)
        self.iterations = config.get('NUM_GENERATIONS', 100)
        
    def _calculate_dissonance(self, timetable):
        if timetable is None: return float('inf')
        penalty = 0
        batch_schedules = defaultdict(lambda: defaultdict(list))
        teacher_schedules = defaultdict(lambda: defaultdict(list))
        for slot in timetable:
            batch_schedules[slot['batch_id']][slot['day']].append(slot['slot_index'])
            teacher_schedules[slot['teacher_id']][slot['day']].append(slot['slot_index'])
        for schedules in [batch_schedules, teacher_schedules]:
            for day_schedule in schedules.values():
                for slots in day_schedule.values():
                    if len(slots) > 1:
                        slots.sort()
                        penalty += (slots[-1] - slots[0] + 1) - len(slots)
        for day_schedule in teacher_schedules.values():
            for slots in day_schedule.values():
                if len(slots) >= 3:
                    slots.sort()
                    for i in range(len(slots) - 2):
                        if slots[i+1] == slots[i] + 1 and slots[i+2] == slots[i] + 2: penalty += 5
        return penalty

    def _get_valid_slots_for_lecture(self, lecture, timetable):
        valid_slots = []
        all_possible_slots = [(d, s) for d in self.config['DAYS_OF_WEEK'] for s in range(self.config['SLOTS_PER_DAY'])]
        teacher_info = self.teachers.get(lecture['teacher_id'], {})
        unavailable_slots = []
        for u in teacher_info.get("unavailable", []):
            if isinstance(u, str) and '-' in u:
                d, s = u.split('-')
                unavailable_slots.append((d, int(s)))
            elif isinstance(u, tuple):
                unavailable_slots.append(u)
        for day, slot_idx in all_possible_slots:
            if (day, slot_idx) in unavailable_slots: continue
            if any(l['teacher_id'] == lecture['teacher_id'] and l['day'] == day and l['slot_index'] == slot_idx for l in timetable): continue
            if any(l['batch_id'] == lecture['batch_id'] and l['day'] == day and l['slot_index'] == slot_idx for l in timetable): continue
            valid_slots.append((day, slot_idx))
        return valid_slots

    def _generate_random_valid_timetable(self):
        """Generate a complete timetable with balanced distribution across all days"""
        timetable = []

        # Create a pool of all lectures that need to be scheduled
        all_lectures = []
        for subject in self.subjects:
            num_to_schedule = subject["per_week"]
            for batch_id in subject["batches"]:
                for _ in range(num_to_schedule):
                    teacher_id = subject["teacher"]
                    batch_info = self.batches.get(batch_id, {})
                    teacher_info = self.teachers.get(teacher_id, {})
                    lecture = {
                        "subject_id": subject["id"],
                        "teacher_id": teacher_id,
                        "batch_id": batch_id,
                        "subject_name": subject["name"],
                        "needs_lab": subject.get("needs_lab", False),
                        "teacher_name": teacher_info.get("name", "N/A"),
                        "batch_name": batch_info.get("name", "N/A"),
                        "batch_size": batch_info.get("size", 0)
                    }
                    all_lectures.append(lecture)

        # Shuffle lectures to create different combinations
        random.shuffle(all_lectures)

        # Distribute lectures evenly across all days and slots first
        lectures_per_day = {}
        for i, day in enumerate(self.config['DAYS_OF_WEEK']):
            lectures_per_day[day] = []

        # Distribute lectures round-robin style across days
        for i, lecture in enumerate(all_lectures):
            day_index = i % len(self.config['DAYS_OF_WEEK'])
            day = self.config['DAYS_OF_WEEK'][day_index]
            lectures_per_day[day].append(lecture)

        # Now schedule each day's lectures into available slots
        for day in self.config['DAYS_OF_WEEK']:
            day_lectures = lectures_per_day[day][:]  # Copy the list
            random.shuffle(day_lectures)  # Shuffle within the day

            # Track teacher workload for this day
            teacher_workload = {}

            # For each slot, try to find a suitable lecture
            for slot_idx in range(self.config['SLOTS_PER_DAY']):
                # Try to find a lecture that can be scheduled in this slot - ensure ALL slots are considered
                lecture_scheduled = False

                # Shuffle lectures for this attempt to get different combinations
                available_lectures = [lec for lec in day_lectures
                                    if teacher_workload.get(lec['teacher_id'], 0) < 4]  # Respect teacher limits

                random.shuffle(available_lectures)

                for lecture in available_lectures:
                    # Check if this batch already has a class in this slot
                    batch_conflict = any(l for l in timetable
                                       if l['day'] == day and l['slot_index'] == slot_idx
                                       and l['batch_id'] == lecture['batch_id'])
                    if batch_conflict:
                        continue

                    # Check if this teacher already has a class in this slot
                    teacher_conflict = any(l for l in timetable
                                         if l['day'] == day and l['slot_index'] == slot_idx
                                         and l['teacher_id'] == lecture['teacher_id'])
                    if teacher_conflict:
                        continue

                    # Find available room for this slot
                    occupied_rooms = [l['room_id'] for l in timetable
                                    if l['day'] == day and l['slot_index'] == slot_idx]
                    available_rooms = [r for r in self.rooms if r['id'] not in occupied_rooms]

                    # Filter suitable rooms
                    suitable_rooms = [r for r in available_rooms if r['capacity'] >= lecture["batch_size"]]
                    if lecture["needs_lab"]:
                        suitable_rooms = [r for r in suitable_rooms if "LAB" in r['id'].upper()]
                    else:
                        suitable_rooms = [r for r in suitable_rooms if "LAB" not in r['id'].upper()]

                    # If no suitable rooms, try any available room
                    if not suitable_rooms:
                        suitable_rooms = available_rooms

                    if suitable_rooms:
                        # Schedule this lecture
                        assigned_lecture = lecture.copy()
                        assigned_lecture['day'] = day
                        assigned_lecture['slot_index'] = slot_idx
                        assigned_lecture['room_id'] = random.choice(suitable_rooms)['id']
                        timetable.append(assigned_lecture)
                        teacher_workload[lecture['teacher_id']] = teacher_workload.get(lecture['teacher_id'], 0) + 1
                        day_lectures.remove(lecture)  # Remove from available lectures
                        lecture_scheduled = True
                        break

                # If no lecture could be scheduled for this slot, continue to next slot
                # (Some slots might remain empty if no suitable lectures are available)

        # Second pass: Try to fill empty slots more aggressively
        remaining_lectures = []
        for day in self.config['DAYS_OF_WEEK']:
            remaining_lectures.extend(lectures_per_day[day])

        # Remove already scheduled lectures
        scheduled_lecture_ids = {(lec['subject_id'], lec['batch_id'], lec['teacher_id']) for lec in timetable}
        remaining_lectures = [lec for lec in remaining_lectures
                            if (lec['subject_id'], lec['batch_id'], lec['teacher_id']) not in scheduled_lecture_ids]

        # Try to fill empty slots with remaining lectures
        for day in self.config['DAYS_OF_WEEK']:
            teacher_workload = {lec['teacher_id']: len([t for t in timetable if t['day'] == day and t['teacher_id'] == lec['teacher_id']]) for lec in remaining_lectures}

            for slot_idx in range(self.config['SLOTS_PER_DAY']):
                # Check if this slot is already filled
                slot_filled = any(l for l in timetable if l['day'] == day and l['slot_index'] == slot_idx)
                if slot_filled:
                    continue

                # Try to schedule a remaining lecture in this empty slot
                random.shuffle(remaining_lectures)
                for lecture in remaining_lectures:
                    if teacher_workload.get(lecture['teacher_id'], 0) >= 4:
                        continue

                    # Check conflicts (relaxed for second pass)
                    batch_conflict = any(l for l in timetable
                                       if l['day'] == day and l['slot_index'] == slot_idx
                                       and l['batch_id'] == lecture['batch_id'])
                    if batch_conflict:
                        continue

                    teacher_conflict = any(l for l in timetable
                                         if l['day'] == day and l['slot_index'] == slot_idx
                                         and l['teacher_id'] == lecture['teacher_id'])
                    if teacher_conflict:
                        continue

                    # Find any available room
                    occupied_rooms = [l['room_id'] for l in timetable
                                    if l['day'] == day and l['slot_index'] == slot_idx]
                    available_rooms = [r for r in self.rooms if r['id'] not in occupied_rooms]

                    if available_rooms:
                        # Schedule this lecture
                        assigned_lecture = lecture.copy()
                        assigned_lecture['day'] = day
                        assigned_lecture['slot_index'] = slot_idx
                        assigned_lecture['room_id'] = random.choice(available_rooms)['id']
                        timetable.append(assigned_lecture)
                        teacher_workload[lecture['teacher_id']] = teacher_workload.get(lecture['teacher_id'], 0) + 1
                        remaining_lectures.remove(lecture)
                        break
        days_with_classes = set(slot['day'] for slot in timetable)
        if len(days_with_classes) < len(self.config['DAYS_OF_WEEK']) * 0.8:  # At least 80% of days
            return None

        if len(timetable) < len(all_lectures) * 0.5:  # At least 50% of lectures scheduled
            return None

        return timetable

    def run(self):
        harmony_memory = []
        for _ in range(self.hms * 3):
              if len(harmony_memory) >= self.hms: break
              new_harmony = self._generate_random_valid_timetable()
              if new_harmony: harmony_memory.append((new_harmony, self._calculate_dissonance(new_harmony)))
        if not harmony_memory: return None
        harmony_memory.sort(key=lambda x: x[1])
        harmony_memory = harmony_memory[:self.hms]
        for i in range(self.iterations):
            base_harmony = harmony_memory[0][0]
            mutated_harmony = copy.deepcopy(base_harmony)
            if random.random() < self.par and len(mutated_harmony) > 1:
                lec1_idx, lec2_idx = random.sample(range(len(mutated_harmony)), 2)
                lec1, lec2 = mutated_harmony[lec1_idx], mutated_harmony[lec2_idx]
                lec1['day'], lec2['day'] = lec2['day'], lec1['day']
                lec1['slot_index'], lec2['slot_index'] = lec2['slot_index'], lec1['slot_index']
            new_dissonance = self._calculate_dissonance(mutated_harmony)
            if new_dissonance < harmony_memory[-1][1]:
                harmony_memory[-1] = (mutated_harmony, new_dissonance)
                harmony_memory.sort(key=lambda x: x[1])
        return harmony_memory[0][0]

# Database initialization
def create_tables():
    """Create all database tables"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

def initialize_sample_data():
    """Initialize sample data for demonstration"""
    with app.app_context():
        # Only add if tables are empty
        if User.query.count() == 0:
            # Create admin user
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)

            # Create faculty users
            faculty_user = User(username='faculty1', role='faculty')
            faculty_user.set_password('faculty123')
            db.session.add(faculty_user)

        if Classroom.query.count() == 0:
            classrooms_data = [
                {"id": "C101", "name": "Room 101", "capacity": 40, "room_type": "Lecture", "department": "General"},
                {"id": "C102", "name": "Room 102", "capacity": 30, "room_type": "Lecture", "department": "General"},
                {"id": "LAB1", "name": "Chemistry Lab", "capacity": 25, "room_type": "Lab", "department": "Science"},
                {"id": "LAB2", "name": "Physics Lab", "capacity": 30, "room_type": "Lab", "department": "Science"}
            ]
            for c_data in classrooms_data:
                classroom = Classroom(**c_data)
                db.session.add(classroom)

        if Faculty.query.count() == 0:
            import json
            faculty_data = [
                {"id": "F1", "name": "Dr. Smith", "subjects": json.dumps(["Mathematics"]), "leaves_per_month": 1, "unavailable_slots": json.dumps([]), "department": "Mathematics", "email": "smith@university.edu"},
                {"id": "F2", "name": "Prof. Lee", "subjects": json.dumps(["Physics"]), "leaves_per_month": 2, "unavailable_slots": json.dumps(["Mon-2"]), "department": "Physics", "email": "lee@university.edu"},
                {"id": "F3", "name": "Ms. Patel", "subjects": json.dumps(["Chemistry"]), "leaves_per_month": 1, "unavailable_slots": json.dumps([]), "department": "Chemistry", "email": "patel@university.edu"}
            ]
            for f_data in faculty_data:
                faculty = Faculty(**f_data)
                db.session.add(faculty)

        if Subject.query.count() == 0:
            import json
            subjects_data = [
                {"id": "MATH101", "name": "Calculus I", "teacher_id": "F1", "batches": json.dumps(["CS1", "ME1"]), "per_week": 3, "needs_lab": False, "fixed_slots": json.dumps([]), "department": "Mathematics", "credits": 4},
                {"id": "PHYS101", "name": "Physics I", "teacher_id": "F2", "batches": json.dumps(["CS1"]), "per_week": 2, "needs_lab": True, "fixed_slots": json.dumps([{"day": "Mon", "slot_index": 2, "room_id": "C102"}]), "department": "Physics", "credits": 4},
                {"id": "CHEM101", "name": "Chemistry I", "teacher_id": "F3", "batches": json.dumps(["CS1"]), "per_week": 2, "needs_lab": True, "fixed_slots": json.dumps([]), "department": "Chemistry", "credits": 4}
            ]
            for s_data in subjects_data:
                subject = Subject(**s_data)
                db.session.add(subject)

        if Batch.query.count() == 0:
            import json
            batches_data = [
                {"id": "CS1", "name": "Computer Science Batch 1", "size": 35, "department": "Computer Science", "shift": "morning", "electives": json.dumps([])},
                {"id": "ME1", "name": "Mechanical Engineering Batch 1", "size": 30, "department": "Mechanical Engineering", "shift": "morning", "electives": json.dumps([])}
            ]
            for b_data in batches_data:
                batch = Batch(**b_data)
                db.session.add(batch)

        if Shift.query.count() == 0:
            shifts_data = [
                {"id": "MORNING", "name": "Morning Shift", "start_time": "09:00", "end_time": "17:00"},
                {"id": "EVENING", "name": "Evening Shift", "start_time": "14:00", "end_time": "22:00"}
            ]
            for sh_data in shifts_data:
                shift = Shift(**sh_data)
                db.session.add(shift)

        try:
            db.session.commit()
            print("Sample data initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error during initialization: {e}")

# Initialize database and sample data on startup
create_tables()
initialize_sample_data()

# Utility functions
def has_clashes(timetable):
    """Check for scheduling conflicts in a timetable"""
    room_usage = set()
    teacher_usage = set()
    batch_usage = set()
    day_batch_count = {}

    for slot in timetable:
        key_room = (slot['day'], slot['slot_index'], slot['room_id'])
        key_teacher = (slot['day'], slot['slot_index'], slot['teacher_id'])
        key_batch = (slot['day'], slot['slot_index'], slot['batch_id'])

        # Room clash
        if key_room in room_usage:
            return True
        room_usage.add(key_room)

        # Teacher clash
        if key_teacher in teacher_usage:
            return True
        teacher_usage.add(key_teacher)

        # Batch clash
        if key_batch in batch_usage:
            return True
        batch_usage.add(key_batch)

        # Max classes per day (relaxed to 6 classes max)
        batch_day = (slot['batch_id'], slot['day'])
        day_batch_count[batch_day] = day_batch_count.get(batch_day, 0) + 1
        if day_batch_count[batch_day] > 6:  # Increased from 4 to 6
            return True

    return False

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('serve_index'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('serve_index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'faculty')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# GET endpoints for frontend data fetching
@app.route('/api/classrooms', methods=['GET'])
def get_classrooms():
    classrooms = Classroom.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'capacity': c.capacity,
        'room_type': c.room_type,
        'department': c.department,
        'is_available': c.is_available
    } for c in classrooms]), 200

@app.route('/api/classrooms', methods=['POST'])
def add_classroom():
    data = request.get_json()
    classroom = Classroom(
        id=data['id'],
        name=data.get('name', data['id']),
        capacity=data['capacity'],
        room_type=data.get('room_type', 'Lecture'),
        department=data.get('department')
    )
    db.session.add(classroom)
    db.session.commit()
    return jsonify({'message': 'Classroom added'}), 200

@app.route('/api/classrooms/<classroom_id>', methods=['PUT'])
def update_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    data = request.get_json()
    classroom.name = data.get('name', classroom.name)
    classroom.capacity = data['capacity']
    classroom.room_type = data.get('room_type', classroom.room_type)
    classroom.department = data.get('department', classroom.department)
    db.session.commit()
    return jsonify({'message': 'Classroom updated'}), 200

@app.route('/api/faculty', methods=['GET'])
def get_faculty():
    faculty = Faculty.query.all()
    import json
    return jsonify([{
        'id': f.id,
        'name': f.name,
        'subjects': json.loads(f.subjects),
        'leaves_per_month': f.leaves_per_month,
        'unavailable': json.loads(f.unavailable_slots) if f.unavailable_slots else [],
        'department': f.department,
        'email': f.email
    } for f in faculty]), 200

@app.route('/api/faculty', methods=['POST'])
def add_faculty():
    data = request.get_json()
    import json
    faculty = Faculty(
        id=data['id'],
        name=data['name'],
        subjects=json.dumps(data['subjects']),
        leaves_per_month=data.get('leaves_per_month', 1),
        unavailable_slots=json.dumps(data.get('unavailable', [])),
        department=data.get('department'),
        email=data.get('email')
    )
    db.session.add(faculty)
    db.session.commit()
    return jsonify({'message': 'Faculty added'}), 200

@app.route('/api/faculty/<faculty_id>', methods=['PUT'])
def update_faculty(faculty_id):
    faculty_member = Faculty.query.get_or_404(faculty_id)
    data = request.get_json()
    import json
    faculty_member.name = data['name']
    faculty_member.subjects = json.dumps(data['subjects'])
    faculty_member.leaves_per_month = data.get('leaves_per_month', faculty_member.leaves_per_month)
    faculty_member.unavailable_slots = json.dumps(data.get('unavailable', []))
    faculty_member.department = data.get('department', faculty_member.department)
    faculty_member.email = data.get('email', faculty_member.email)
    db.session.commit()
    return jsonify({'message': 'Faculty updated'}), 200

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    subjects = Subject.query.all()
    import json
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'teacher': s.teacher_id,
        'batches': json.loads(s.batches),
        'per_week': s.per_week,
        'needs_lab': s.needs_lab,
        'fixed_slots': json.loads(s.fixed_slots) if s.fixed_slots else [],
        'department': s.department,
        'credits': s.credits
    } for s in subjects]), 200

@app.route('/api/subjects', methods=['POST'])
def add_subject():
    data = request.get_json()
    import json
    subject = Subject(
        id=data['id'],
        name=data['name'],
        teacher_id=data['teacher'],
        batches=json.dumps(data['batches']),
        per_week=data['per_week'],
        needs_lab=data.get('needs_lab', False),
        fixed_slots=json.dumps(data.get('fixed_slots', [])),
        department=data.get('department'),
        credits=data.get('credits', 1)
    )
    db.session.add(subject)
    db.session.commit()
    return jsonify({'message': 'Subject added'}), 200

@app.route('/api/subjects/<subject_id>', methods=['PUT'])
def update_subject(subject_id):
    data = request.get_json()
    import json
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify({'error': 'Subject not found'}), 404
    
    subject.name = data['name']
    subject.teacher_id = data['teacher']
    subject.batches = json.dumps(data['batches'])
    subject.per_week = data['per_week']
    subject.needs_lab = data.get('needs_lab', False)
    subject.fixed_slots = json.dumps(data.get('fixed_slots', []))
    subject.department = data.get('department')
    subject.credits = data.get('credits', 1)
    
    db.session.commit()
    return jsonify({'message': 'Subject updated'}), 200

@app.route('/api/batches', methods=['GET'])
def get_batches():
    batches = Batch.query.all()
    import json
    return jsonify([{
        'id': b.id,
        'name': b.name,
        'size': b.size,
        'department': b.department,
        'shift': b.shift,
        'electives': json.loads(b.electives) if b.electives else []
    } for b in batches]), 200

@app.route('/api/batches', methods=['POST'])
def add_batch():
    data = request.get_json()
    import json
    batch = Batch(
        id=data['id'],
        name=data['name'],
        size=data['size'],
        department=data.get('department'),
        shift=data.get('shift', 'morning'),
        electives=json.dumps(data.get('electives', []))
    )
    db.session.add(batch)
    db.session.commit()
    return jsonify({'message': 'Batch added'}), 200

@app.route('/api/batches/<batch_id>', methods=['PUT'])
def update_batch(batch_id):
    data = request.get_json()
    import json
    batch = Batch.query.get(batch_id)
    if not batch:
        return jsonify({'error': 'Batch not found'}), 404
    
    batch.name = data['name']
    batch.size = data['size']
    batch.department = data.get('department')
    batch.shift = data.get('shift', 'morning')
    batch.electives = json.dumps(data.get('electives', []))
    
    db.session.commit()
    return jsonify({'message': 'Batch updated'}), 200

# Data generation endpoint (database)
@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        required_keys = ['config', 'rooms', 'teachers', 'batches', 'subjects']
        for key in required_keys:
            if key not in data:
                return jsonify({"error": f"Missing key: {key}"}), 400

        # Validate data structure
        if not isinstance(data['rooms'], list) or not isinstance(data['teachers'], list) or not isinstance(data['batches'], list) or not isinstance(data['subjects'], list):
            return jsonify({"error": "Invalid data format. All data must be arrays."}), 400

        # Convert lists to dicts for lookup
        teachers = {t['id']: t for t in data['teachers']}
        batches = {b['id']: b for b in data['batches']}
        rooms = data['rooms']
        subjects = data['subjects']
        config = data['config']
        num_timetables = max(config.get('NUM_TIMETABLES', 3), 3)  # At least 3 timetables

        scheduler = TemporalHarmonyScheduler(config, rooms, teachers, batches, subjects)
        harmony_memory = []

        # Generate more harmony solutions with increased attempts for complete slot filling
        max_attempts = max(scheduler.hms * 300, 8000)  # Greatly increased attempts
        successful_generations = 0

        for attempt in range(max_attempts):
            if len(harmony_memory) >= scheduler.hms:
                break
            new_harmony = scheduler._generate_random_valid_timetable()
            if new_harmony:
                # Check for clashes and basic validity
                if not has_clashes(new_harmony) and len(new_harmony) > 0:
                    # Additional check: ensure all days have some classes and good slot utilization
                    days_with_classes = set(slot['day'] for slot in new_harmony)
                    total_slots = len(config['DAYS_OF_WEEK']) * config['SLOTS_PER_DAY']
                    slot_utilization = len(new_harmony) / total_slots

                    if (len(days_with_classes) >= len(config['DAYS_OF_WEEK']) and  # Use ALL days
                        slot_utilization >= 0.85):  # At least 85% of slots filled
                        harmony_memory.append((new_harmony, scheduler._calculate_dissonance(new_harmony)))
                        successful_generations += 1

        # If we still don't have enough timetables, try with more relaxed constraints
        if len(harmony_memory) < 3:
            print(f"Warning: Only generated {len(harmony_memory)} valid timetables. Using relaxed constraints...")
            for attempt in range(max_attempts // 10):
                if len(harmony_memory) >= 3:
                    break
                new_harmony = scheduler._generate_random_valid_timetable()
                if new_harmony and len(new_harmony) > 0:
                    # Accept even with fewer requirements
                    days_with_classes = set(slot['day'] for slot in new_harmony)
                    if len(days_with_classes) >= len(config['DAYS_OF_WEEK']) * 0.8:  # At least 80% of days
                        harmony_memory.append((new_harmony, scheduler._calculate_dissonance(new_harmony)))

        if not harmony_memory:
            return jsonify({"error": "Failed to generate timetables. The algorithm couldn't find valid schedules that fill the time slots properly. Try:\n• Adding more classrooms\n• Adding more faculty\n• Reducing classes per week for subjects\n• Increasing slots per day\n• Adding more days per week"}), 500

        harmony_memory.sort(key=lambda x: x[1])

        # Double-check generated timetables for conflicts
        validated_timetables = []
        for timetable, score in harmony_memory:
            if has_clashes(timetable):
                print(f"Warning: Generated timetable has conflicts, skipping...")
                continue
            validated_timetables.append((timetable, score))

        if not validated_timetables:
            return jsonify({"error": "Generated timetables contain conflicts. This may be due to insufficient resources or overly restrictive constraints. Try:\n• Adding more classrooms\n• Adding more faculty\n• Reducing classes per subject\n• Increasing time slots per day\n• Reducing the number of days per week"}), 500

        # Generate multiple optimized timetable options
        timetables_data = []
        for i in range(min(num_timetables, len(validated_timetables))):
            timetable, score = validated_timetables[i]

            # Save each timetable option to database with different versions
            db_timetable = Timetable(
                version=i+1,
                status='pending_approval',
                department=config.get('DEPARTMENT'),
                shift=config.get('SHIFT'),
                created_by_id=current_user.id if current_user.is_authenticated else None
            )
            db.session.add(db_timetable)
            db.session.flush()

            for slot_data in timetable:
                slot_data['approval_status'] = 'pending'
                slot_data['approved_by_id'] = None
                slot_data['change_reason'] = None

                db_slot = Slot(
                    timetable_id=db_timetable.id,
                    subject_id=slot_data['subject_id'],
                    subject_name=slot_data['subject_name'],
                    teacher_id=slot_data['teacher_id'],
                    teacher_name=slot_data['teacher_name'],
                    batch_id=slot_data['batch_id'],
                    batch_name=slot_data['batch_name'],
                    room_id=slot_data['room_id'],
                    day=slot_data['day'],
                    slot_index=slot_data['slot_index'],
                    approval_status='pending'
                )
                db.session.add(db_slot)

            timetables_data.append({
                'timetable_id': db_timetable.id,
                'version': i+1,
                'slots': timetable,
                'score': score,
                'department': config.get('DEPARTMENT'),
                'shift': config.get('SHIFT')
            })

        db.session.commit()
        result = {
            "message": f"Generated {len(timetables_data)} optimized timetable options!",
            "timetables": timetables_data
        }
        return jsonify(result), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Exception occurred: {str(e)}"}), 500

@app.route('/api/shifts', methods=['POST'])
def add_shift():
    data = request.get_json()
    shift = Shift(
        id=data['id'],
        name=data['name'],
        start_time=data['start_time'],
        end_time=data['end_time']
    )
    db.session.add(shift)
    db.session.commit()
    return jsonify({'message': 'Shift added'}), 200

@app.route('/')
def serve_index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def serve_dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    try:
        # Get all pending timetables (multiple options)
        pending_timetables = Timetable.query.filter_by(status='pending_approval').order_by(Timetable.created_at.desc()).all()

        if not pending_timetables:
            return jsonify({
                "timetables": [],
                "stats": {"approved_slots": 0, "total_slots": 0, "approval_progress": 0, "utilization": "0%", "load_status": "No data", "conflicts": 0},
                "users": []
            }), 200

        timetables_data = []
        for timetable in pending_timetables:
            slots = Slot.query.filter_by(timetable_id=timetable.id).all()
            timetable_data = [{
                'id': slot.id,
                'subject_id': slot.subject_id,
                'subject_name': slot.subject_name,
                'teacher_id': slot.teacher_id,
                'teacher_name': slot.teacher_name,
                'batch_id': slot.batch_id,
                'batch_name': slot.batch_name,
                'room_id': slot.room_id,
                'day': slot.day,
                'slot_index': slot.slot_index,
                'approval_status': slot.approval_status,
                'approved_by_id': slot.approved_by_id,
                'change_reason': slot.change_reason
            } for slot in slots]

            timetables_data.append({
                'id': timetable.id,
                'version': timetable.version,
                'department': timetable.department,
                'shift': timetable.shift,
                'slots': timetable_data,
                'total_slots': len(slots),
                'approved_slots': len([s for s in slots if s.approval_status == 'approved'])
            })

        # Calculate overall stats
        all_slots = []
        for t in timetables_data:
            all_slots.extend(t['slots'])

        total_slots = len(all_slots)
        approved_slots = len([s for s in all_slots if s['approval_status'] == 'approved'])
        approval_progress = (approved_slots / total_slots * 100) if total_slots > 0 else 0

        # Calculate utilization (simplified)
        unique_room_slots = set()
        for slot in all_slots:
            unique_room_slots.add((slot['room_id'], slot['day'], slot['slot_index']))
        utilization = f"{(len(unique_room_slots) / (5 * 4 * 3) * 100):.1f}%"  # Assuming 5 days, 4 slots, 3 rooms

        # Get users for leaderboard
        users = User.query.all()
        users_data = [{'username': u.username, 'points': u.approval_points} for u in users]

        stats = {
            "approved_slots": approved_slots,
            "total_slots": total_slots,
            "approval_progress": approval_progress,
            "utilization": utilization,
            "load_status": "Normal",  # Placeholder
            "conflicts": 0  # Placeholder
        }

        return jsonify({
            "timetables": timetables_data,
            "stats": stats,
            "users": users_data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch dashboard data: {str(e)}"}), 500

        stats = {
            "approved_slots": approved_slots,
            "total_slots": total_slots,
            "approval_progress": approval_progress,
            "utilization": utilization,
            "load_status": "Normal",
            "conflicts": 0  # Simplified
        }

        return jsonify({
            "timetables": timetables_data,
            "stats": stats,
            "users": users_data
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch dashboard data: {str(e)}"}), 500

@app.route('/api/approve/<int:slot_id>', methods=['POST'])
def approve_slot(slot_id):
    try:
        slot = Slot.query.get_or_404(slot_id)
        slot.approval_status = 'approved'
        slot.approved_at = datetime.utcnow()
        # In a real app, you'd get the current user from session
        # For now, we'll use a dummy user ID
        slot.approved_by_id = 1  # TODO: Get from current user session
        
        # Award points to the approver
        if slot.approved_by_id:
            user = User.query.get(slot.approved_by_id)
            if user:
                user.approval_points += 10
        
        db.session.commit()
        return jsonify({"message": "Slot approved successfully", "points_awarded": 10}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to approve slot: {str(e)}"}), 500

@app.route('/api/approve_all/<int:timetable_id>', methods=['POST'])
@login_required
def approve_all_slots(timetable_id):
    try:
        slots = Slot.query.filter_by(timetable_id=timetable_id, approval_status='pending').all()

        for slot in slots:
            slot.approval_status = 'approved'
            slot.approved_by_id = current_user.id
            slot.approved_at = datetime.utcnow()

            # Award points to the approver
            current_user.approval_points += 10

        db.session.commit()
        return jsonify({
            "message": f"Successfully approved {len(slots)} slots",
            "points_awarded": len(slots) * 10
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to approve slots: {str(e)}"}), 500


@app.route('/api/sample-data', methods=['POST'])
def populate_sample_data():
    try:
        import json
        # Clear existing data
        db.session.query(Slot).delete()
        db.session.query(Timetable).delete()
        db.session.query(Subject).delete()
        db.session.query(Faculty).delete()
        db.session.query(Classroom).delete()
        db.session.query(Batch).delete()
        db.session.query(Shift).delete()

        # Add sample classrooms
        classrooms_data = [
            {"id": "C101", "name": "Room 101", "capacity": 40, "room_type": "Lecture"},
            {"id": "C102", "name": "Room 102", "capacity": 30, "room_type": "Lecture"},
            {"id": "LAB1", "name": "Lab 1", "capacity": 40, "room_type": "Lab"}
        ]
        for c_data in classrooms_data:
            classroom = Classroom(**c_data)
            db.session.add(classroom)

        # Add sample faculty
        faculty_data = [
            {"id": "F1", "name": "Dr. Smith", "subjects": json.dumps(["Math"]), "leaves_per_month": 1, "unavailable_slots": json.dumps([])},
            {"id": "F2", "name": "Prof. Lee", "subjects": json.dumps(["Physics"]), "leaves_per_month": 2, "unavailable_slots": json.dumps(["Mon-2"])},
            {"id": "F3", "name": "Ms. Patel", "subjects": json.dumps(["Chemistry"]), "leaves_per_month": 1, "unavailable_slots": json.dumps([])}
        ]
        for f_data in faculty_data:
            faculty = Faculty(**f_data)
            db.session.add(faculty)

        # Add sample subjects
        subjects_data = [
            {"id": "S1", "name": "Math", "teacher_id": "F1", "batches": json.dumps(["B1"]), "per_week": 3, "needs_lab": False, "fixed_slots": json.dumps([])},
            {"id": "S2", "name": "Physics", "teacher_id": "F2", "batches": json.dumps(["B1"]), "per_week": 2, "needs_lab": False, "fixed_slots": json.dumps([{"day": "Mon", "slot_index": 2, "room_id": "C102"}])},
            {"id": "S3", "name": "Chemistry", "teacher_id": "F3", "batches": json.dumps(["B1"]), "per_week": 2, "needs_lab": True, "fixed_slots": json.dumps([])}
        ]
        for s_data in subjects_data:
            subject = Subject(**s_data)
            db.session.add(subject)

        # Add sample batches
        batches_data = [
            {"id": "B1", "name": "Batch 1", "size": 35, "electives": json.dumps([])}
        ]
        for b_data in batches_data:
            batch = Batch(**b_data)
            db.session.add(batch)

        # Add sample shifts
        shifts_data = [
            {"id": "SH1", "name": "Morning", "start_time": "09:00", "end_time": "12:00"}
        ]
        for sh_data in shifts_data:
            shift = Shift(**sh_data)
            db.session.add(shift)

        db.session.commit()
        return jsonify({"message": "Sample data populated in database."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to populate sample data: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
