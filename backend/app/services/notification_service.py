import os
import smtplib
import json
import threading
import asyncio
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from backend.app.core.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.activity import KeyboardMouseActivity, ProductivityLog
from backend.app.models.ai_log import NotificationSettings, AlertLog

class NotificationService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_sender = os.getenv("EMAIL_SENDER", "notifications@productivity-engine.com")
        
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._check_rules_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _check_rules_loop(self):
        print("Starting rules checker background daemon...")
        while self.running:
            try:
                self.check_activity_rules()
            except Exception as e:
                print(f"Error in notification checker: {str(e)}")
            time.sleep(30) # Run check every 30 seconds

    def check_activity_rules(self):
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True, User.role == "employee").all()
            now = datetime.utcnow()
            
            for user in users:
                settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user.id).first()
                if not settings:
                    continue

                # 1. IDLE CHECK
                # Find last keyboard/mouse activity
                last_activity = db.query(KeyboardMouseActivity).filter(
                    KeyboardMouseActivity.user_id == user.id
                ).order_by(KeyboardMouseActivity.timestamp.desc()).first()

                idle_seconds = 0
                if last_activity:
                    idle_seconds = (now - last_activity.timestamp).total_seconds()
                else:
                    # No logs at all means idle since start or registration
                    idle_seconds = 9999

                # Check thresholds (10 minutes = 600s, 20 minutes = 1200s)
                # To prevent spamming, verify if we already sent a notification within the last hour
                if idle_seconds >= 1200: # 20 minutes
                    self._trigger_alert(
                        db, user, settings, 
                        title="Critical Idle Warning", 
                        message=f"Employee {user.username} has been idle for {round(idle_seconds / 60)} minutes.", 
                        alert_type="idle",
                        notify_manager=True
                    )
                elif idle_seconds >= 600: # 10 minutes
                    self._trigger_alert(
                        db, user, settings, 
                        title="Idle Alert", 
                        message="You have been inactive for over 10 minutes. Please check-in.", 
                        alert_type="idle",
                        notify_manager=False
                    )

                # 2. PHONE USAGE CHECK (usage for > 15 minutes = 900s)
                # Query recent productivity logs where phone was active
                cutoff_phone = now - timedelta(minutes=20)
                phone_logs = db.query(ProductivityLog).filter(
                    ProductivityLog.user_id == user.id,
                    ProductivityLog.timestamp >= cutoff_phone
                ).order_by(ProductivityLog.timestamp.desc()).all()

                phone_duration_seconds = 0
                # Approximate duration: sum logs in filter (since they are logged every 10s)
                phone_active_count = sum(1 for log in phone_logs if log.phone_detected)
                phone_duration_seconds = phone_active_count * 10
                
                if phone_duration_seconds >= 900: # 15 minutes
                    self._trigger_alert(
                        db, user, settings, 
                        title="Phone Usage Violation", 
                        message=f"Mobile phone usage detected for more than 15 minutes.", 
                        alert_type="phone",
                        notify_manager=True
                    )

        finally:
            db.close()

    def _trigger_alert(self, db: Session, user: User, settings: NotificationSettings, title: str, message: str, alert_type: str, notify_manager: bool = False):
        now = datetime.utcnow()
        
        # Check if identical alert logged in past 15 mins to avoid duplicate alerts
        prev_cutoff = now - timedelta(minutes=15)
        exist = db.query(AlertLog).filter(
            AlertLog.user_id == user.id,
            AlertLog.title == title,
            AlertLog.timestamp >= prev_cutoff
        ).first()

        if exist:
            return # Skip duplicate spam

        print(f"[TRIGGER ALERT] {title} for {user.username}: {message}")

        # Determine target notification email
        recipient = settings.email_recipient if settings.email_recipient else f"{user.username}@company.com"
        if notify_manager:
            # Query manager email
            manager = db.query(User).filter(User.role == "manager", User.department == user.department).first()
            if manager:
                m_settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == manager.id).first()
                if m_settings and m_settings.email_recipient:
                    recipient = m_settings.email_recipient

        # Dispatch Desktop
        if settings.desktop_enabled:
            alert = AlertLog(user_id=user.id, title=title, message=message, type=alert_type, channel="desktop")
            db.add(alert)
        
        # Dispatch Email
        if settings.email_enabled:
            alert = AlertLog(user_id=user.id, title=title, message=message, type=alert_type, channel="email")
            db.add(alert)
            self.send_email(recipient, title, message)

        # Dispatch FCM
        if settings.fcm_enabled and settings.fcm_token:
            alert = AlertLog(user_id=user.id, title=title, message=message, type=alert_type, channel="fcm")
            db.add(alert)
            self.send_fcm(settings.fcm_token, title, message)

        db.commit()

    def send_email(self, to_email: str, subject: str, content: str):
        """
        Sends e-mail warning. If SMTP details are empty, prints locally.
        """
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = self.email_sender
        msg['To'] = to_email

        if not self.smtp_user or not self.smtp_password:
            # Local simulation fallback
            log_dir = "tmp/sent_emails"
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"email_{int(time.time())}.txt")
            with open(log_file, "w") as f:
                f.write(f"TO: {to_email}\nSUBJECT: {subject}\nCONTENT: \n{content}\n")
            print(f"[SIMULATED EMAIL SENT] File written: {log_file}")
            return

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            print(f"[EMAIL SENT] Successfully sent to {to_email}")
        except Exception as e:
            print(f"[EMAIL FAILED] smtp error: {str(e)}")

    def send_fcm(self, token: str, title: str, message: str):
        """
        Simulates Firebase Push notification dispatcher.
        """
        log_dir = "tmp/sent_fcm"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"fcm_{int(time.time())}.json")
        payload = {
            "token": token,
            "title": title,
            "body": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=4)
        print(f"[SIMULATED FCM SENT] Push payload to token {token} saved: {log_file}")

import time
notification_service = NotificationService()
