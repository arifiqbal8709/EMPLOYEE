import cv2
import time
import logging
import threading
from datetime import datetime
from ultralytics import YOLO

from backend.app.core.database import SessionLocal
from backend.app.models.detection import CameraDetection
from backend.app.services.camera_source import OpenCVCameraSource

logger = logging.getLogger("backend.webcam_service")

class WebcamDetectionService:
    """
    Singleton service managing the laptop webcam capture process
    and running real-time YOLOv11 object analysis.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WebcamDetectionService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.camera_source = None
        
        # Telemetry metrics parsed in real-time
        self.status = "stopped"  # "stopped", "running", "no_device_error", "initializing"
        self.telemetry = {
            "camera_status": "Inactive",
            "person_detected": "No",
            "phone_detected": "No",
            "laptop_detected": "No",
            "chair_detected": "No",
            "confidence": "0%",
            "fps": 0
        }
        
        self.target_classes = {
            0: "person",
            56: "chair",
            63: "laptop",
            64: "mouse",
            66: "keyboard",
            67: "cell phone",
            39: "bottle",
            73: "book"
        }
        
        self.class_colors = {
            "person": (0, 255, 0),        # Green
            "cell phone": (0, 0, 255),    # Red
            "laptop": (255, 255, 0),      # Cyan
            "chair": (150, 0, 150),       # Purple
            "mouse": (255, 0, 255),       # Magenta
            "keyboard": (255, 0, 255),    # Magenta
            "bottle": (0, 165, 255),      # Orange
            "book": (200, 200, 200)       # Gray
        }

        # Initialize YOLOv11 model
        import os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        yolo11_path = os.path.join(base_dir, "yolo11n.pt")
        yolov8_path = os.path.join(base_dir, "yolov8n.pt")
        
        if not os.path.exists(yolo11_path):
            yolo11_path = "yolo11n.pt"
        if not os.path.exists(yolov8_path):
            yolov8_path = "yolov8n.pt"

        try:
            self.model = YOLO(yolo11_path)
            logger.info(f"YOLOv11 model initialized successfully in Webcam Service from: {yolo11_path}")
        except Exception as e:
            logger.error(f"Error loading YOLOv11 weights inside webcam service: {e}")
            self.model = YOLO(yolov8_path)

    def auto_detect_webcam(self) -> int:
        """
        Scan indices 0 through 5 to locate the built-in/default laptop webcam automatically.
        """
        for idx in range(6):
            logger.info(f"Scanning index {idx} for webcam presence...")
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                try:
                    cap = cv2.VideoCapture(idx, backend)
                    if cap and cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            cap.release()
                            logger.info(f"Auto-detected working default webcam at index {idx} with backend {backend}")
                            return idx
                        cap.release()
                except Exception as e:
                    logger.debug(f"Webcam scan failed at index {idx}: {e}")
        return 0

    def start(self) -> bool:
        """
        Boot the background processing capture thread.
        """
        if self.running:
            logger.info("Webcam YOLO service is already running.")
            return True

        self.running = True
        self.status = "initializing"
        self.telemetry["camera_status"] = "Initializing"
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> bool:
        """
        Stop the capture loop thread and release active device holds.
        """
        if not self.running:
            return False

        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None

        if self.camera_source:
            self.camera_source.release()
            self.camera_source = None

        self.status = "stopped"
        self.latest_frame = None
        self.telemetry["camera_status"] = "Inactive"
        self.telemetry["person_detected"] = "No"
        self.telemetry["phone_detected"] = "No"
        self.telemetry["laptop_detected"] = "No"
        self.telemetry["chair_detected"] = "No"
        self.telemetry["confidence"] = "0%"
        self.telemetry["fps"] = 0
        
        logger.info("Webcam YOLO service stopped successfully.")
        return True

    def _run_loop(self):
        """
        Real-time extraction and YOLO frame analysis loop.
        """
        webcam_idx = self.auto_detect_webcam()

        # Initialize our abstracted OpenCV capture object
        self.camera_source = OpenCVCameraSource(webcam_idx)
        self.status = "running"
        self.telemetry["camera_status"] = "Active Streaming"
        
        # Frame timers for FPS calculations
        prev_time = time.time()
        
        # Cooldown timer to prevent bloating SQL database
        last_db_save = 0.0
        db_save_cooldown = 1.0  # seconds

        while self.running:
            try:
                ret, frame = self.camera_source.read()
                if not ret or frame is None:
                    logger.warn("Webcam read return false. Reconnection watchdog alert...")
                    # Wait and try to reopen source index
                    self.camera_source.release()
                    time.sleep(1.0)
                    self.camera_source = OpenCVCameraSource(webcam_idx)
                    continue

                # Frame details size
                height, width, _ = frame.shape
                
                # Setup YOLO Inference with 60% confidence threshold constraint
                results = self.model(frame, verbose=False, conf=0.60)[0]
                
                detections = []
                confidences = []
                
                # Reset matches telemetry
                has_person = "No"
                has_phone = "No"
                has_laptop = "No"
                has_chair = "No"

                # Parse and render outputs
                for box in results.boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id not in self.target_classes:
                        continue

                    cls_name = self.target_classes[cls_id]
                    conf = float(box.conf[0].item())
                    confidences.append(conf)

                    # Mark triggers
                    if cls_name == "person":
                        has_person = "Yes"
                    elif cls_name == "cell phone":
                        has_phone = "Yes"
                    elif cls_name == "laptop":
                        has_laptop = "Yes"
                    elif cls_name == "chair":
                        has_chair = "Yes"

                    # Box coordinates extract
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)

                    detections.append({
                        "class": cls_name if cls_name != "cell phone" else "phone",
                        "confidence": round(conf, 2),
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h
                    })

                    # Draw colored bounding box
                    color = self.class_colors[cls_name]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                    # Box Header Text
                    label_text = f"{cls_name.upper()}: {int(conf * 100)}%"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x, y - th - 6), (x + tw + 4, y), color, -1)
                    cv2.putText(frame, label_text, (x + 2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

                # Compute frame rate FPS
                current_time = time.time()
                elapsed = current_time - prev_time
                prev_time = current_time
                fps = round(1.0 / elapsed, 1) if elapsed > 0 else 0

                # Render live FPS stats onto image
                fps_text = f"FPS: {fps}"
                cv2.putText(frame, fps_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

                # 3-Second Person Absence & Telemetry tracking
                now = time.time()
                if has_person == "Yes":
                    self.last_person_seen = now
                    self.telemetry["person_detected"] = "Yes"
                else:
                    if not hasattr(self, 'last_person_seen') or self.last_person_seen is None:
                        self.last_person_seen = now
                    elif now - self.last_person_seen >= 3.0:
                        self.telemetry["person_detected"] = "No"

                self.telemetry["phone_detected"] = has_phone
                self.telemetry["laptop_detected"] = has_laptop
                self.telemetry["chair_detected"] = has_chair
                self.telemetry["fps"] = fps
                
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    self.telemetry["confidence"] = f"{int(avg_conf * 100)}%"
                else:
                    self.telemetry["confidence"] = "0%"

                # Persist to database if object detections are found (or store empty heartbeat log every 1s)
                if current_time - last_db_save >= db_save_cooldown:
                    last_db_save = current_time
                    self._save_detection_record(detections)

                # Encode frame as JPEG byte-stream for MJPEG route
                ret_bytes, jpeg = cv2.imencode('.jpg', frame)
                if ret_bytes:
                    self.latest_frame = jpeg.tobytes()

            except Exception as e:
                logger.error(f"Inference error in webcam loop thread: {e}")
                time.sleep(0.05)

            # Cap loop processing limits (up to ~30 FPS)
            time.sleep(0.01)

    def _save_detection_record(self, detections: list):
        """
        Record log data into PostgreSQL telemetry structures.
        """
        db = SessionLocal()
        try:
            new_log = CameraDetection(
                camera_id="WEBCAM_DEFAULT",
                timestamp=datetime.utcnow(),
                detections_json=detections
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to insert webcam logs: {e}")
        finally:
            db.close()

    def get_frame(self) -> bytes:
        return self.latest_frame
