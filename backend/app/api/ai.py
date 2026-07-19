import httpx
import logging
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional

from backend.app.services.webcam_detection_service import WebcamDetectionService

logger = logging.getLogger("backend.ai_api")
router = APIRouter()

AI_ENGINE_URL = "http://localhost:8002"
webcam_service = WebcamDetectionService()

class AIStartCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001")
    source: str = Field(..., example="0")

class AIStopCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001")

@router.post("/start-camera", status_code=status.HTTP_200_OK)
async def start_camera(body: AIStartCameraBody):
    """
    Proxy route starting AI camera stream. Falls back to single WebcamDetectionService if standalone.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{AI_ENGINE_URL}/api/ai/start-camera",
                json={"camera_id": body.camera_id, "source": body.source},
                timeout=2.0
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

    # Fallback to local single WebcamDetectionService
    webcam_service.start()
    return {"status": "success", "message": "Webcam detection loop activated."}

@router.post("/stop-camera", status_code=status.HTTP_200_OK)
async def stop_camera(body: AIStopCameraBody):
    """
    Proxy route stopping AI camera stream loops.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{AI_ENGINE_URL}/api/ai/stop-camera",
                json={"camera_id": body.camera_id},
                timeout=2.0
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

    webcam_service.stop()
    return {"status": "success", "message": "Webcam detection loop stopped."}

@router.get("/status")
async def get_status():
    """
    Proxy route monitoring live status variables of active feeds.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{AI_ENGINE_URL}/api/ai/status", timeout=2.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

    # Return status directly from single WebcamDetectionService
    return {
        "status": webcam_service.status,
        "telemetry": webcam_service.get_telemetry()
    }
