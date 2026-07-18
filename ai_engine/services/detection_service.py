import os
import sys
import time
import logging
import threading
from datetime import datetime

# Setup parent path so we can import database configurations
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from backend.app.core.database import SessionLocal
from backend.app.models.detection import CameraDetection
from ai_engine.utils.camera import WebcamStream
from ai_engine.detectors.object_detector import YOLOObjectDetector

logger = logging.getLogger("ai_engine.detection_service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class DetectionService:
    """
    Main manager orchestrating camera threads, YOLO inferences, 
    and DB commits. Follows SOLID principles.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # Thread-safe Singleton pattern implementation
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DetectionService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.active_cameras = {}  # camera_id -> dict
        self.detector = YOLOObjectDetector()
        self.lock = threading.Lock()

    def start_camera(self, camera_id: str, source: str) -> bool:
        """
        Instantiate thread loop for selected camera.
        """
        with self.lock:
            if camera_id in self.active_cameras:
                logger.warn(f"Camera [{camera_id}] is already active.")
                return False

            logger.info(f"Starting AI Camera Worker [{camera_id}] for source [{source}]...")
            
            # Setup stream thread
            stream = WebcamStream(source=source)
            stream.start()

            camera_data = {
                "stream": stream,
                "camera_id": camera_id,
                "source": source,
                "running": True,
                "last_detections": [],
                "status": "initializing",
                "thread": None
            }

            self.active_cameras[camera_id] = camera_data
            
            # Spawn processing loop thread
            proc_thread = threading.Thread(
                target=self._process_camera_loop, 
                args=(camera_id,), 
                daemon=True
            )
            camera_data["thread"] = proc_thread
            proc_thread.start()
            
            return True

    def stop_camera(self, camera_id: str) -> bool:
        """
        Release video stream and stop thread loop.
        """
        with self.lock:
            if camera_id not in self.active_cameras:
                logger.warn(f"Stop Camera request failed: [{camera_id}] is not active.")
                return False

            logger.info(f"Stopping AI Camera Worker [{camera_id}]...")
            camera_data = self.active_cameras[camera_id]
            camera_data["running"] = False
            
            # Release cv2 resources
            camera_data["stream"].release()
            
            # Remove from list
            del self.active_cameras[camera_id]
            return True

    def get_status(self) -> list:
        """
        Returns list status description of active threads.
        """
        with self.lock:
            status_list = []
            for cid, data in self.active_cameras.items():
                stream = data["stream"]
                status_list.append({
                    "cameraId": cid,
                    "source": data["source"],
                    "isConnected": stream.connected,
                    "status": "connected" if stream.connected else "disconnected",
                    "running": data["running"]
                })
            return status_list

    def get_latest_detections(self, camera_id: str) -> list:
        """
        Yields frame detections json for active camera.
        """
        with self.lock:
            if camera_id in self.active_cameras:
                return self.active_cameras[camera_id]["last_detections"]
            return []

    def _process_camera_loop(self, camera_id: str):
        """
        Frame extraction loop running yolo classification calculations.
        """
        logger.info(f"Processing loop active for [{camera_id}]")
        
        # Cooldown intervals to throttle database insertions (save every 1 second)
        last_db_save = 0.0
        db_save_interval = 1.0 

        while True:
            # Check if camera still running
            with self.lock:
                if camera_id not in self.active_cameras:
                    break
                data = self.active_cameras[camera_id]
                if not data["running"]:
                    break
            
            stream = data["stream"]
            ret, frame = stream.read()

            if ret and frame is not None:
                # Update status
                data["status"] = "connected"
                
                # Detect target items (Person, Phone, Laptop, Chair)
                objects, annotated_frame = self.detector.detect(frame)
                
                # Update hot telemetry
                data["last_detections"] = objects

                # Dynamically write annotated stream to frame placeholder or log
                # Database commit
                now = time.time()
                if now - last_db_save >= db_save_interval:
                    last_db_save = now
                    # We save the detection event (even empty classes list to track attendance/idle)
                    self._save_to_database(camera_id, objects)
            else:
                data["status"] = "disconnected"

            # 30 FPS ceiling to prevent excessive thread execution
            time.sleep(0.033)

        logger.info(f"Processing thread loop terminated for [{camera_id}].")

    def _save_to_database(self, camera_id: str, objects: list):
        """
        Atomically persists telemetry in PostgreSQL table.
        """
        db = SessionLocal()
        try:
            log_item = CameraDetection(
                camera_id=camera_id,
                timestamp=datetime.utcnow(),
                detections_json=objects
            )
            db.add(log_item)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving camera detection index: {str(e)}")
        finally:
            db.close()
