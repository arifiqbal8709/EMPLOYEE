from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.ai_log import NotificationSettings
from backend.app.core.security import get_password_hash
from backend.app.schemas.user import UserCreate, UserUpdate, UserResponse
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.services.report_service import report_service

router = APIRouter()

# 1. Search & List Employees
@router.get("/", response_model=List[UserResponse])
def list_employees(
    username: Optional[str] = Query(None, description="Filter by name"),
    employee_id: Optional[str] = Query(None, description="Filter by Employee ID"),
    department: Optional[str] = Query(None, description="Filter by Department"),
    status: Optional[str] = Query(None, description="Filter by Status (active/idle/absent)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "manager"]))
):
    query = db.query(User).filter(User.role == "employee")
    
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if employee_id:
        query = query.filter(User.employee_id.ilike(f"%{employee_id}%"))
    if department:
        query = query.filter(User.department.ilike(f"%{department}%"))
    if status:
        query = query.filter(User.status == status)

    return query.all()


# 2. Add Employee
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    user_in: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "manager"]))
):
    # Verify if user exists
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    if user_in.employee_id:
        existing_id = db.query(User).filter(User.employee_id == user_in.employee_id).first()
        if existing_id:
            raise HTTPException(
                status_code=400,
                detail="Employee ID already exists"
            )

    hashed_pwd = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        password_hash=hashed_pwd,
        role="employee", # Hardcoded to employee
        employee_id=user_in.employee_id,
        department=user_in.department,
        camera_id=user_in.camera_id,
        status=user_in.status if user_in.status else "absent",
        is_active=True
    )
    db.add(db_user)
    db.flush() # Retrieves ID

    # Create default notification settings
    settings_obj = NotificationSettings(
        user_id=db_user.id,
        desktop_enabled=True,
        email_enabled=True,
        email_recipient=f"{db_user.username}@company.com",
        fcm_enabled=False,
        fcm_token=None
    )
    db.add(settings_obj)
    db.commit()
    db.refresh(db_user)
    
    return db_user


# 3. Update Employee details
@router.put("/{id}", response_model=UserResponse)
def update_employee(
    id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce RBAC: Managers and Admins can update any; Employees can only update themselves
    if current_user.role == "employee" and current_user.id != id:
        raise HTTPException(
            status_code=403,
            detail="Permission denied. You can only update your own details."
        )

    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Perform updates
    update_data = user_in.dict(exclude_unset=True)
    if 'password' in update_data and update_data['password']:
        db_user.password_hash = get_password_hash(update_data['password'])
        del update_data['password']

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)
    return db_user


# 4. Delete Employee profile
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin"]))
):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(db_user)
    db.commit()
    return None


# 5. Export Reports Excel
@router.get("/reports/excel")
def export_excel(
    start_date: str = Query(..., description="Start Date YYYY-MM-DD"),
    end_date: str = Query(..., description="End Date YYYY-MM-DD"),
    employee_id: Optional[int] = Query(None, description="Optional Employee DB ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "manager"]))
):
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    excel_file = report_service.generate_excel_report(db, sd, ed, employee_id)
    filen = f"productivity_report_{start_date}_to_{end_date}.xlsx"
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filen}"}
    )


# 6. Export Reports PDF
@router.get("/reports/pdf")
def export_pdf(
    start_date: str = Query(..., description="Start Date YYYY-MM-DD"),
    end_date: str = Query(..., description="End Date YYYY-MM-DD"),
    employee_id: Optional[int] = Query(None, description="Optional Employee DB ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker(["admin", "manager"]))
):
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    pdf_file = report_service.generate_pdf_report(db, sd, ed, employee_id)
    filen = f"productivity_report_{start_date}_to_{end_date}.pdf"
    return StreamingResponse(
        pdf_file,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filen}"}
    )
