import httpx
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter()

# Target URI for the standalone AI Engine service
AI_ENGINE_URL = "http://localhost:8002"

class AIStartCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001")
    source: str = Field(..., example="0")

class AIStopCameraBody(BaseModel):
    camera_id: str = Field(..., example="CAM001")

@router.post("/start-camera", status_code=status.HTTP_200_OK)
async def start_camera(body: AIStartCameraBody):
    """
    Proxy route starting AI camera streams inside the AI Engine workspace.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{AI_ENGINE_URL}/api/ai/start-camera",
                json={"camera_id": body.camera_id, "source": body.source},
                timeout=10.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Error in AI Engine"))
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="AI Engine daemon is offline.")

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
                timeout=10.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.json().get("detail", "Error in AI Engine"))
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="AI Engine daemon is offline.")

@router.get("/status")
async def get_status():
    """
    Proxy route monitoring live status variables of active feeds.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{AI_ENGINE_URL}/api/ai/status", timeout=5.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Error getting status from AI Engine")
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="AI Engine daemon is offline.")

@router.get("/detections")
async def get_detections(
    camera_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    minutes_ago: Optional[int] = Query(None)
):
    """
    Proxy route querying historical database records for camera detections.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {"limit": limit}
            if camera_id:
                params["camera_id"] = camera_id
            if minutes_ago:
                params["minutes_ago"] = minutes_ago

            resp = await client.get(
                f"{AI_ENGINE_URL}/api/ai/detections",
                params=params,
                timeout=5.0
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Error querying detections database")
            return resp.json()
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="AI Engine daemon is offline.")
