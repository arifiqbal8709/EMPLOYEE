import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
# Patch torch.load to default weights_only to False to support YOLO model unpickling on PyTorch 2.6+
if hasattr(torch, '_original_load'):
    torch.load = torch._original_load
else:
    torch._original_load = torch.load

def patched_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return torch._original_load(*args, **kwargs)
torch.load = patched_load
print("MONKEYPATCH: torch.load monkeypatched successfully", torch.load)

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.api import auth, employees, cameras, notifications, ai
from backend.app.api.camera_control import router as camera_control_router
from backend.app.services.camera_service import camera_service_manager
from backend.app.services.notification_service import notification_service
from backend.app.models.camera import Camera

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronous lifecycle context manager.
    Handles startup configuration and shutdown cleanups.
    """
    # 1. Initialize Tables (PostgreSQL schema sync)
    print("Synching database schemas on startup...")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Schema synchronization failed: {str(e)}")

    # 2. Start Rules Notification checker daemon
    print("Initiating notification alerts daemon...")
    notification_service.start()

    # 3. Boot single webcam detection service
    print("Booting webcam detection service...")
    try:
        from backend.app.services.webcam_detection_service import WebcamDetectionService
        WebcamDetectionService().start()
        print("Webcam detection service started successfully.")
    except Exception as e:
        print(f"Error starting webcam service: {str(e)}")

    yield  # Runs application

    # --- SHUTDOWN LOGIC ---
    print("Stopping application threads parameters...")
    notification_service.stop()
    
    # Release camera locks
    for cam_id in list(camera_service_manager.threads.keys()):
        camera_service_manager.stop_camera(cam_id)
    print("Lifecycle thread shutdowns completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full-stack AI Employee Productivity Monitoring System backend API.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configurations matching settings namespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router paths
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(employees.router, prefix=f"{settings.API_V1_STR}/employees", tags=["Employee Directory"])
app.include_router(cameras.router, prefix=f"{settings.API_V1_STR}/cameras", tags=["Camera Controls"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["Notification Center"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Camera Engine"])
app.include_router(camera_control_router, prefix="/api/camera", tags=["Webcam AI Control"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "api_prefix": settings.API_V1_STR
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
