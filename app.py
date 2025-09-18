from flask import Flask, render_template, request, jsonify
from models import db, User, Timetable, Slot
import random
import copy
from collections import defaultdict
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
basedir = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(basedir, 'timetable.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- Temporal Harmony Algorithm (Unchanged) ---
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
        for day, slot_idx in all_possible_slots:
            if tuple([day, slot_idx]) in teacher_info.get("unavailable", []): continue
            if any(l['teacher_id'] == lecture['teacher_id'] and l['day'] == day and l['slot_index'] == slot_idx for l in timetable): continue
            if any(l['batch_id'] == lecture['batch_id'] and l['day'] == day and l['slot_index'] == slot_idx for l in timetable): continue
            valid_slots.append((day, slot_idx))
        return valid_slots

    def _generate_random_valid_timetable(self):
        lectures_to_schedule = []
        for subject in self.subjects:
            for batch_id in subject["batches"]:
                for _ in range(subject["per_week"]):
                    teacher_id = subject["teacher"]
                    batch_info = self.batches.get(batch_id, {})
                    teacher_info = self.teachers.get(teacher_id, {})
                    lectures_to_schedule.append({
                        "subject_id": subject["id"], "teacher_id": teacher_id, "batch_id": batch_id,
                        "subject_name": subject["name"], "needs_lab": subject.get("needs_lab", False),
                        "teacher_name": teacher_info.get("name", "N/A"), "batch_name": batch_info.get("name", "N/A"),
                        "batch_size": batch_info.get("size", 0)
                    })
        random.shuffle(lectures_to_schedule)
        timetable = []
        for lecture in lectures_to_schedule:
            valid_slots = self._get_valid_slots_for_lecture(lecture, timetable)
            if not valid_slots: return None
            day, slot_idx = random.choice(valid_slots)
            occupied_rooms = [l['room_id'] for l in timetable if l['day'] == day and l['slot_index'] == slot_idx]
            available_rooms = [r for r in self.rooms if r['id'] not in occupied_rooms]
            suitable_rooms = [r for r in available_rooms if r['capacity'] >= lecture["batch_size"]]
            if lecture["needs_lab"]: suitable_rooms = [r for r in suitable_rooms if "LAB" in r['id'].upper()]
            else: suitable_rooms = [r for r in suitable_rooms if "LAB" not in r['id'].upper()]
            if not suitable_rooms: return None
            lecture['day'], lecture['slot_index'], lecture['room_id'] = day, slot_idx, random.choice(suitable_rooms)['id']
            timetable.append(lecture)
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

# --- HTML Serving Routes (Unchanged) ---
@app.route('/')
def serve_index(): return render_template('index.html')

@app.route('/dashboard')
def serve_dashboard(): return render_template('dashboard.html')

# --- API Routes ---
@app.route('/api/dashboard-data')
def get_dashboard_data():
    latest_timetable = Timetable.query.order_by(Timetable.id.desc()).first()
    users = User.query.order_by(User.approval_points.desc()).all()
    if not latest_timetable: return jsonify({"timetable": None, "users": [], "stats": {}})
    
    slots_data = [{"id": s.id, "day": s.day, "slot_index": s.slot_index, "subject_name": s.subject_name, "teacher_name": s.teacher_name, "batch_name": s.batch_name, "room_id": s.room_id, "approval_status": s.approval_status} for s in latest_timetable.slots]
    
    # --- NEW: Real Analytics Calculation ---
    total_slots = len(slots_data)
    approved_slots = sum(1 for s in slots_data if s['approval_status'] == 'approved')
    approval_progress = int((approved_slots / total_slots) * 100) if total_slots > 0 else 0
    
    # Room Utilization
    total_room_slots = 3 * 5 * 5 # Simplified: 3 rooms * 5 days * 5 slots
    occupied_room_slots = len(set((s['room_id'], s['day'], s['slot_index']) for s in slots_data))
    utilization = int((occupied_room_slots / total_room_slots) * 100) if total_room_slots > 0 else 0

    # Faculty Load
    teacher_loads = defaultdict(int)
    for s in slots_data: teacher_loads[s['teacher_name']] += 1
    load_status = "Balanced"
    if teacher_loads and (max(teacher_loads.values()) - min(teacher_loads.values()) > 4):
        load_status = "Uneven"

    return jsonify({
        "timetable": slots_data,
        "users": [{"username": u.username, "points": u.approval_points} for u in users],
        "stats": {
            "total_slots": total_slots, "approved_slots": approved_slots, "approval_progress": approval_progress,
            "utilization": utilization, "load_status": load_status, "conflicts": 0
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.get_json()
    scheduler = TemporalHarmonyScheduler(data['config'], data['rooms'], data['teachers'], data['batches'], data['subjects'])
    best_timetable_slots = scheduler.run()
    if not best_timetable_slots: return jsonify({"error": "Failed to generate. Constraints might be too tight."}), 500
    with app.app_context():
        # --- NEW: Don't delete old timetables, just create a new one ---
        new_timetable = Timetable()
        db.session.add(new_timetable)
        db.session.commit()
        for slot_data in best_timetable_slots:
            filtered_data = {k: v for k, v in slot_data.items() if k in Slot.__table__.columns}
            slot = Slot(timetable_id=new_timetable.id, **filtered_data)
            db.session.add(slot)
        db.session.commit()
    return jsonify({"message": "Timetable generated successfully!"})

@app.route('/api/approve/<int:slot_id>', methods=['POST'])
def approve_slot(slot_id):
    user_id = 1
    slot = Slot.query.get_or_404(slot_id)
    user = User.query.get_or_404(user_id)
    if slot.approval_status != 'approved':
        slot.approval_status = 'approved'; slot.approved_by_id = user.id; user.approval_points += 10
        db.session.commit()
    return jsonify({"message": "Slot approved!", "new_points": user.approval_points})

@app.route('/api/request_change/<int:slot_id>', methods=['POST'])
def request_change(slot_id):
    user_id = 1
    reason = request.json.get('reason', 'No reason provided.')
    slot = Slot.query.get_or_404(slot_id)
    user = User.query.get_or_404(user_id)
    slot.approval_status = 'change_requested'; slot.change_reason = reason; user.approval_points -= 2
    db.session.commit()
    return jsonify({"message": "Change request submitted.", "new_points": user.approval_points})

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        with app.app_context():
            print("Database not found. Creating database and initial users...")
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                db.session.add(User(username='admin', role='admin', approval_points=20))
            if not User.query.filter_by(username='prof_jones').first():
                db.session.add(User(username='prof_jones', role='faculty', approval_points=50))
            db.session.commit()
            print("Database created successfully.")
    app.run(debug=True)