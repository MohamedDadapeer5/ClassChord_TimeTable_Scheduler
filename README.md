# ClassChord: Higher Education Timetable Scheduler

ClassChord is an intelligent timetable scheduling system for higher education institutions. It uses advanced algorithms to generate optimized timetables while considering various constraints like room availability, faculty schedules, and batch requirements.

## Features

- **Intelligent Timetable Generation**: Automatically creates optimized schedules using the TemporalHarmony algorithm
- **Entity Management**: Create, read, update, and delete subjects, batches, faculty, and classrooms
- **User Authentication**: Secure login and registration system with role-based access
- **Interactive Dashboard**: View and manage generated timetables
- **Constraint Management**: Set specific constraints for scheduling

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Algorithm**: Custom TemporalHarmony Scheduler

## Quick Start

1. Clone the repository
   ```
   git clone https://github.com/MohamedDadapeer5/ClassChord_TimeTable_Scheduler.git
   cd ClassChord_TimeTable_Scheduler
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Run the application
   ```
   python app.py
   ```

5. Access the application at `http://127.0.0.1:5000`

## Default Credentials

- Username: admin, Password: admin123
- Username: faculty1, Password: faculty123

## Project Structure

- `app.py` - Main Flask application with routes and TemporalHarmony algorithm
- `models.py` - Database models and schema definitions
- `static/` - CSS, JavaScript, and other static assets
- `templates/` - HTML templates
- `timetable.db` - SQLite database file

## API Endpoints

The application provides RESTful API endpoints for managing entities:

- `/api/subjects` - Manage subjects
- `/api/batches` - Manage batches
- `/api/faculty` - Manage faculty
- `/api/classrooms` - Manage classrooms
- `/api/generate-timetable` - Generate timetables

## License

[MIT License](LICENSE)