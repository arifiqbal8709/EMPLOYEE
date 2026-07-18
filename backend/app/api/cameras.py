from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.camera import Camera
from backend.app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from backend.app.api.auth import get_current_user, RoleChecker
from backend.app.services.camera_service import camera_service_manager

router = APIRouter()

# 1. List all cameras
@router.get("/", response_model=List[CameraResponse])
def get_cameras(
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"]))
):
    return db.query(Camera).all()


# 2. Register new camera
@router.post("/", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    camera_in: CameraCreate,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"]))
):
    db_cam = Camera(
        name=camera_in.name,
        type=camera_in.type,
        source=camera_in.source,
        status="disconnected",
        user_id=camera_in.user_id
    )
    db.add(db_cam)
    db.commit()
    db.refresh(db_cam)
    
    # Intuitively start camera feed thread in background manager
    camera_service_manager.start_camera(
        camera_id=db_cam.id,
        source=db_cam.source,
        camera_type=db_cam.type,
        user_id=db_cam.user_id
    )
    
    return db_cam


# 3. Update Camera settings
@router.put("/{id}", response_model=CameraResponse)
def update_camera(
    id: int,
    camera_in: CameraUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin", "manager"]))
):
    db_cam = db.query(Camera).filter(Camera.id == id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    update_data = camera_in.dict(exclude_unset=True)
    source_changed = 'source' in update_data and update_data['source'] != db_cam.source
    user_changed = 'user_id' in update_data and update_data['user_id'] != db_cam.user_id

    for field, value in update_data.items():
        setattr(db_cam, field, value)

    db.commit()
    db.refresh(db_cam)
    
    # If source or linked profile changed, reload the camera thread
    if source_changed or user_changed:
        camera_service_manager.start_camera(
            camera_id=db_cam.id,
            source=db_cam.source,
            camera_type=db_cam.type,
            user_id=db_cam.user_id
        )
        
    return db_cam


# 4. Remove camera configuration profile
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(
    id: int,
    db: Session = Depends(get_db),
    current_user = Depends(RoleChecker(["admin"]))
):
    db_cam = db.query(Camera).filter(Camera.id == id).first()
    if not db_cam:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    # Stop background thread first
    camera_service_manager.stop_camera(id)
    
    db.delete(db_cam)
    db.commit()
    return None


# 5. Connect and stream live annotated MJPEG video streaming channel
@router.get("/{id}/stream")
def stream_camera(id: int):
    # Returns standard video stream yielding Multipart content frame boundaries
    return StreamingResponse(
        camera_service_manager.get_stream(id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# 6. Retrieve latest parsed JSON bounding coordinates and landmarks telemetry
@router.get("/{id}/telemetry")
def get_camera_telemetry(id: int):
    return camera_service_manager.get_telemetry(id)
