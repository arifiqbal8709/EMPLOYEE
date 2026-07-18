import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Setup parent path so we can import database configurations
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.app.core.database import SessionLocal
from backend.app.models.detection import CameraDetection
from ai_engine.services.detection_service import DetectionService

# Setup logger configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai_engine.main")

app = FastAPI(
    title="AI Camera Engine Service",
    description="Handles multithreaded OpenCV captures and YOLOv11 inferences coordinates",
    version="1.0.0"
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Detection Service
service = DetectionService()

# Request validation schemas
class StartCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001", description="Camera unique alphanumeric label")
    source: str = Field(..., example="0", description="Integer index for USB webcams, or rtsp:// link for IP cameras")

class StopCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001", description="Camera unique identifier")


@app.post("/api/ai/start-camera", tags=["Controls"])
def start_camera(body: StartCameraBody):
    """
    Start inference stream captures on a specific source.
    """
    logger.info(f"Received request to start camera: {body.camera_id} from source: {body.source}")
    success = service.start_camera(body.camera_id, body.source)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to start camera {body.camera_id}. It may already be running.")
    return {"status": "success", "message": f"Camera worker for {body.camera_id} started."}


@app.post("/api/ai/stop-camera", tags=["Controls"])
def stop_camera(body: StopCameraBody):
    """
    Release inference stream captures on a specific camera.
    """
    logger.info(f"Received request to stop camera: {body.camera_id}")
    success = service.stop_camera(body.camera_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to stop camera {body.camera_id}. It may not be running.")
    return {"status": "success", "message": f"Camera worker for {body.camera_id} stopped."}


@app.get("/api/ai/status", tags=["Diagnostic"])
def get_status():
    """
    Returns diagnostic list of active camera capture loops.
    """
    return service.get_status()


@app.get("/api/ai/detections", tags=["Analytics"])
def get_detections(
    camera_id: Optional[str] = Query(None, description="Filter logs by Camera ID"),
    limit: int = Query(50, ge=1, le=500, description="Max logs limit lookup"),
    minutes_ago: Optional[int] = Query(None, description="Filter logs to last X minutes")
):
    """
    Yields historical camera detections persisted in PostgreSQL.
    """
    db = SessionLocal()
    try:
        query = db.query(CameraDetection)
        
        # Filter filters: camera_id
        if camera_id:
            query = query.filter(CameraDetection.camera_id == camera_id)
            
        # Filter filter: time range
        if minutes_ago:
            start_time = datetime.utcnow() - timedelta(minutes=minutes_ago)
            query = query.filter(CameraDetection.timestamp >= start_time)
            
        # Order logs chronologically (latest first)
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
        logger.error(f"Error reading database detections index: {str(e)}")
        raise HTTPException(status_code=500, detail="Database lookup failed.")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    # Standalone execution on port 8002
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
