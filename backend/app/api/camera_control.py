import time
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from datetime import datetime, timedelta

from backend.app.core.database import SessionLocal
from backend.app.models.detection import CameraDetection
from backend.app.services.webcam_detection_service import WebcamDetectionService

logger = logging.getLogger("backend.camera_control")

router = APIRouter()
service = WebcamDetectionService()

@router.post("/start", status_code=status.HTTP_200_OK)
def start_camera():
    """
    POST route initializing the built-in laptop webcam YOLO capture thread.
    """
    logger.info("Webcam activation requested.")
    success = service.start()
    if not success:
         raise HTTPException(status_code=400, detail="Could not trigger webcam thread activation.")
    return {"status": "success", "message": "Webcam detection loop activated."}


@router.post("/stop", status_code=status.HTTP_200_OK)
def stop_camera():
    """
    POST route releasing webcam device allocation.
    """
    logger.info("Webcam deactivation requested.")
    success = service.stop()
    if not success:
         return {"status": "warning", "message": "Feedback already offline."}
    return {"status": "success", "message": "Webcam detection loop stopped."}


@router.get("/status")
def get_camera_status():
    """
    GET route reporting active telemetry variables, detected occurrences, and FPS.
    """
    # Return formatted schema matching side-panel specifications
    return {
        "status": service.status,
        "camera_status": service.telemetry["camera_status"],
        "person_detected": service.telemetry["person_detected"],
        "phone_detected": service.telemetry["phone_detected"],
        "laptop_detected": service.telemetry["laptop_detected"],
        "chair_detected": service.telemetry["chair_detected"],
        "confidence": service.telemetry["confidence"],
        "fps": service.telemetry["fps"]
    }


@router.get("/detections")
def get_camera_detections(
    limit: int = Query(50, ge=1, le=500),
    minutes_ago: Optional[int] = Query(None)
):
    """
    GET route retrieving historical log telemetry records from PostgreSQL.
    """
    db = SessionLocal()
    try:
        query = db.query(CameraDetection).filter(CameraDetection.camera_id == "WEBCAM_DEFAULT")
        
        if minutes_ago:
            start_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            query = query.filter(CameraDetection.timestamp >= start_time)
            
        results = query.order_by(CameraDetection.timestamp.desc()).limit(limit).all()
        
        detections_list = []
        for r in results:
            detections_list.append({
                "id": r.id,
                "cameraId": r.camera_id,
                "timestamp": r.timestamp.isoformat(),
                "objects": r.detections_json
            })
            
        return detections_list
    except Exception as e:
        logger.error(f"Error loading camera detections registry: {e}")
        raise HTTPException(status_code=500, detail="Database extraction query failure.")
    finally:
        db.close()


def generate_webcam_frames():
    """
    Yields JPEG boundaries iteratively.
    """
    # Wait for the device to handshake the first frame
    time.sleep(0.5)
    
    # Track when the loop starts to avoid infinite loops if it doesn't initialize
    start_wait = time.time()
    
    while service.running:
        if service.status == "no_device_error":
            break
            
        frame_bytes = service.get_frame()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            # Throttling to prevent excessive cpu context switching
            time.sleep(0.03)
        else:
            # If no frame is ready yet, wait briefly
            time.sleep(0.05)
            if time.time() - start_wait > 5.0:
                logger.warn("Stream handshake timeout.")
                break


@router.get("/stream")
def stream_webcam_feed():
    """
    GET route providing multipart/x-mixed-replace streaming channel.
    """
    if not service.running:
        # Auto-start if not running
        service.start()
        
    return StreamingResponse(
        generate_webcam_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
