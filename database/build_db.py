import sys
import os
from datetime import datetime, timedelta, timezone

# Add parent directory to path so python can find backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User
from backend.app.models.camera import Camera
from backend.app.models.activity import KeyboardMouseActivity, ProductivityLog
from backend.app.models.ai_log import NotificationSettings, AlertLog

def build_and_seed_db():
    print("Connecting to PostgreSQL database...")
    try:
        # Create all tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Successfully created PostgreSQL tables.")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        print("Please verify that your PostgreSQL server is running and the database exists.")
        return

    db = SessionLocal()
    try:
        # 1. Seed default accounts
        print("Seeding default accounts...")
        users_to_seed = [
            {
                "username": "admin_user",
                "password": "AdminPass123",
                "role": "admin",
                "employee_id": "EMP-001",
                "department": "Security Operations",
                "camera_id": "0",
                "status": "active"
            },
            {
                "username": "manager_user",
                "password": "ManagerPass123",
                "role": "manager",
                "employee_id": "EMP-002",
                "department": "Engineering Manager",
                "camera_id": "1",
                "status": "active"
            },
            {
                "username": "employee_user",
                "password": "EmployeePass123",
                "role": "employee",
                "employee_id": "EMP-100",
                "department": "Frontend Engineering",
                "camera_id": "2",
                "status": "active"
            },
            {
                "username": "alice_dev",
                "password": "EmployeePass123",
                "role": "employee",
                "employee_id": "EMP-101",
                "department": "AI Development",
                "camera_id": "3",
                "status": "idle"
            },
            {
                "username": "bob_design",
                "password": "EmployeePass123",
                "role": "employee",
                "employee_id": "EMP-102",
                "department": "UI/UX Design",
                "camera_id": "4",
                "status": "absent"
            }
        ]

        db_users = []
        for u in users_to_seed:
            hashed_pwd = get_password_hash(u["password"])
            db_user = User(
                username=u["username"],
                password_hash=hashed_pwd,
                role=u["role"],
                employee_id=u["employee_id"],
                department=u["department"],
                camera_id=u["camera_id"],
                status=u["status"],
                is_active=True
            )
            db.add(db_user)
            db.flush() # populated database ID
            db_users.append(db_user)

            # Assign default settings
            settings_obj = NotificationSettings(
                user_id=db_user.id,
                desktop_enabled=True,
                email_enabled=True,
                email_recipient=f"{u['username']}@company.com",
                fcm_enabled=False,
                fcm_token=None
            )
            db.add(settings_obj)

        print("Seeded users and user settings.")

        # 2. Seed default cameras
        print("Seeding cameras configuration...")
        cameras_to_seed = [
            {"name": "Admin Primary USB", "type": "usb", "source": "0", "status": "connected", "user_id": db_users[0].id},
            {"name": "Manager Main RTSP", "type": "rtsp", "source": "rtsp://127.0.0.1:8554/live1", "status": "connected", "user_id": db_users[1].id},
            {"name": "Employee Desk Webcam", "type": "usb", "source": "0", "status": "connected", "user_id": db_users[2].id},
            {"name": "AI Lab Stream", "type": "rtsp", "source": "rtsp://192.168.1.100:554/stream1", "status": "disconnected", "user_id": db_users[3].id},
            {"name": "Design Studio Camera", "type": "usb", "source": "1", "status": "error", "user_id": db_users[4].id}
        ]

        for cam in cameras_to_seed:
            db_cam = Camera(
                name=cam["name"],
                type=cam["type"],
                source=cam["source"],
                status=cam["status"],
                user_id=cam["user_id"]
            )
            db.add(db_cam)

        print("Seeded cameras.")

        # 3. Seed historical reports data (For Daily, Weekly, Monthly Charts)
        print("Seeding historical activity and productivity logs...")
        now = datetime.utcnow()
        # Seed last 30 days of data
        for day in range(30):
            target_date = now - timedelta(days=day)
            
            for user in db_users:
                # Seed work/idle logs
                # Skip seed for days if user absent
                if user.username == "bob_design" and day % 5 == 0:
                    continue # Mock absent days
                
                # Mock keyboard/mouse activity count
                kb_strokes = 2000 + (day * 150) % 1500
                mouse_clicks = 800 + (day * 70) % 800
                activity = KeyboardMouseActivity(
                    user_id=user.id,
                    keyboard_strokes=kb_strokes,
                    mouse_clicks=mouse_clicks,
                    timestamp=target_date
                )
                db.add(activity)

                # Mock productivity logs
                avg_score = 65 + (user.id * 5 + day * 3) % 30 # Scores ranging 65-95
                if user.username == "alice_dev" and day % 4 == 0:
                    avg_score = 45 # phone distractions day

                prod_log = ProductivityLog(
                    user_id=user.id,
                    camera_id=1 if user.id % 2 == 0 else 3,
                    score=avg_score,
                    is_present=True,
                    looking_at_monitor=True if avg_score > 70 else False,
                    sleeping=False if avg_score > 50 else True,
                    phone_detected=True if avg_score < 60 else False,
                    keyboard_active=True if kb_strokes > 1000 else False,
                    mouse_active=True if mouse_clicks > 400 else False,
                    timestamp=target_date
                )
                db.add(prod_log)

        # 4. Seed some Alerts
        print("Seeding live alerts logs...")
        alerts = [
            ("employee_user", "Drowsiness Alert", "Employee signs of sleeping detected on camera", "system", "desktop"),
            ("employee_user", "Phone Usage Alert", "Mobile phone usage exceeded 5 minutes threshold", "phone", "email"),
            ("alice_dev", "Idle Time Alert", "No keyboard/mouse activity detected for over 10 minutes", "idle", "desktop"),
            ("bob_design", "Idle Time Alert", "Employee is away from desk for over 20 minutes", "idle", "email")
        ]

        for username, title, message, alert_type, channel in alerts:
            user_obj = db.query(User).filter(User.username == username).first()
            if user_obj:
                alert_log = AlertLog(
                    user_id=user_obj.id,
                    title=title,
                    message=message,
                    type=alert_type,
                    channel=channel,
                    timestamp=now - timedelta(hours=2)
                )
                db.add(alert_log)

        db.commit()
        print("Database initialized and populated successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    build_and_seed_db()
