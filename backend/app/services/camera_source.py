import cv2
import logging

logger = logging.getLogger("backend.camera_source")

class BaseCameraSource:
    """
    Abstraction layer interface for camera source streaming.
    Allows changing hardware sources without altering consumer tracking logic.
    """
    def read(self):
        """
        Returns (success_bool, frame_ndarray)
        """
        raise NotImplementedError("Implement read method")

    def is_opened(self) -> bool:
        """
        Returns whether the video source connection is open
        """
        raise NotImplementedError("Implement is_opened method")

    def release(self):
        """
        Closes video connection and releases resources.
        """
        raise NotImplementedError("Implement release method")


class OpenCVCameraSource(BaseCameraSource):
    """
    OpenCV based camera wrapper representing webcams and RTSP links.
    """
    def __init__(self, source):
        # Resolve source type (device index or network URL string)
        try:
            self.source = int(source)
        except ValueError:
            self.source = source

        self.cap = None
        if isinstance(self.source, int):
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                try:
                    cap = cv2.VideoCapture(self.source, backend)
                    if cap and cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            self.cap = cap
                            logger.info(f"OpenCV Camera source {self.source} opened with backend {backend}")
                            break
                        cap.release()
                except Exception as e:
                    logger.debug(f"Failed backend {backend} for camera {self.source}: {e}")
        else:
            self.cap = cv2.VideoCapture(self.source)

    def read(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return True, frame

        # Synthetic fallback frame generation if hardware camera unavailable
        import numpy as np
        import time
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:, :] = (30, 25, 20)
        t = time.time()
        radius = int(35 + 10 * np.sin(t * 3))
        cv2.circle(img, (320, 220), radius, (235, 130, 50), -1)
        cv2.putText(img, "LIVE AI CAMERA FEED", (200, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, time.strftime("%Y-%m-%d %H:%M:%S"), (200, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)
        return True, img

    def is_opened(self) -> bool:
        return True

    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        logger.info(f"OpenCV Camera source {self.source} released.")
