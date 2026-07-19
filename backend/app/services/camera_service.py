import time
import logging
from typing import Dict, Generator, Optional

from backend.app.services.webcam_detection_service import WebcamDetectionService

logger = logging.getLogger("backend.camera_service")

class CameraServiceManager:
    """
    Manager facade routing all camera requests to the singleton WebcamDetectionService.
    Eliminates duplicate camera initialization, duplicate YOLO model loading, and hardware device locks.
    """
    def __init__(self):
        self.testing_mode: bool = True
        self.webcam_service = WebcamDetectionService()

    def set_testing_mode(self, enabled: bool):
        self.testing_mode = enabled

    def start_camera(self, camera_id: int, source: str, camera_type: str, user_id: Optional[int]) -> bool:
        return self.webcam_service.start()

    def stop_camera(self, camera_id: int):
        return self.webcam_service.stop()

    def get_stream(self, camera_id: int) -> Generator[bytes, None, None]:
        """
        Yields live MJPEG byte chunks from the single WebcamDetectionService pipeline.
        """
        if not self.webcam_service.running:
            self.webcam_service.start()

        time.sleep(0.2)
        while self.webcam_service.running:
            frame_bytes = self.webcam_service.get_frame()
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.05)
            time.sleep(0.033)  # ~30 FPS streaming yield

    def get_telemetry(self, camera_id: int) -> dict:
        return self.webcam_service.get_telemetry()

camera_service_manager = CameraServiceManager()
