from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.models.ai_log import NotificationSettings, AlertLog
from backend.app.models.activity import KeyboardMouseActivity
from backend.app.schemas.ai_log import NotificationSettingsResponse, NotificationSettingsUpdate, AlertLogResponse
from backend.app.schemas.activity import KeyboardMouseActivityCreate
from backend.app.api.auth import get_current_user, RoleChecker

router = APIRouter()

# 1. Retrieve current custom Notification Settings configurations
@router.get("/settings", response_model=NotificationSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == current_user.id).first()
    if not settings:
        # Create default settings if record missing
        settings = NotificationSettings(
            user_id=current_user.id,
            desktop_enabled=True,
            email_enabled=True,
            email_recipient=f"{current_user.username}@company.com",
            fcm_enabled=False
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


# 2. Modify Settings variables
@router.put("/settings", response_model=NotificationSettingsResponse)
def update_settings(
    settings_in: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == current_user.id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Notification settings profile not found")

    update_data = settings_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    return settings


# 3. List recent alert histories logs
@router.get("/logs", response_model=List[AlertLogResponse])
def get_alert_logs(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"]))
):
    # Manager and Admins view all alerts logs
    return db.query(AlertLog).order_by(AlertLog.timestamp.desc()).limit(limit).all()


# 4. API for desktop agent to log keyboard/mouse telemetry signals
@router.post("/activity", status_code=status.HTTP_201_CREATED)
def post_activity(
    activity_in: KeyboardMouseActivityCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Security check: Verify that user is not submitting logs for another individual
    if current_user.role == "employee" and current_user.id != activity_in.user_id:
         raise HTTPException(
             status_code=403, 
             detail="Forbidden. You cannot log telemetry for other employees."
         )

    activity = KeyboardMouseActivity(
        user_id=activity_in.user_id,
        keyboard_strokes=activity_in.keyboard_strokes,
        mouse_clicks=activity_in.mouse_clicks,
        timestamp=datetime.utcnow()
    )
    db.add(activity)
    db.commit()
    return {"status": "logged", "timestamp": activity.timestamp}
