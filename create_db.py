from flask import Flask
from models import db, User, Classroom, Faculty, Subject, Batch, Shift, Timetable, Slot

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db
db.init_app(app)

def create_all_tables():
    with app.app_context():
        print("Creating all database tables...")
        print(f"Models imported: {[cls.__name__ for cls in [User, Classroom, Faculty, Subject, Batch, Shift, Timetable, Slot]]}")

        # Check what models are registered
        from sqlalchemy import inspect
        print(f"Tables in metadata before create_all: {list(db.metadata.tables.keys())}")

        # Check if models have __tablename__
        for model_cls in [User, Classroom, Faculty, Subject, Batch, Shift, Timetable, Slot]:
            print(f"{model_cls.__name__}: __tablename__ = {getattr(model_cls, '__tablename__', 'NOT SET')}")

        db.create_all()

        # List all tables
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")

        print("Database tables created successfully!")

if __name__ == "__main__":
    create_all_tables()