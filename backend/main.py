import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.api import auth, employees, cameras, notifications
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

    # 3. Boot cameras marked as connected on last run
    print("Loading active camera streams threads...")
    db = SessionLocal()
    try:
        active_cams = db.query(Camera).filter(Camera.status == "connected").all()
        for cam in active_cams:
            camera_service_manager.start_camera(
                camera_id=cam.id,
                source=cam.source,
                camera_type=cam.type,
                user_id=cam.user_id
            )
        print(f"Triggered check for {len(active_cams)} camera connections.")
    except Exception as e:
        print(f"Error loading startup streams: {str(e)}")
    finally:
        db.close()

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

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "api_prefix": settings.API_V1_STR
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
