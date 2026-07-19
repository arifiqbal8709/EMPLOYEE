import cv2
import time
import logging
import threading
import numpy as np
import mediapipe as mp
from datetime import datetime
from ultralytics import YOLO

from backend.app.core.database import SessionLocal
from backend.app.models.detection import CameraDetection
from backend.app.services.camera_source import OpenCVCameraSource

logger = logging.getLogger("backend.webcam_service")

class WebcamDetectionService:
    """
    Singleton service managing laptop webcam capture, YOLOv11 ByteTrack object tracking,
    MediaPipe Face Mesh telemetry calculations, and real event state logging.
    
    Rates:
    - Camera Capture: ~30 FPS (33ms loop)
    - YOLO & ByteTrack Detection: 15 FPS (every 2nd frame)
    - Telemetry Updates: 5 FPS (200ms interval)
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
        
        # Telemetry metrics parsed in real-time from real inference ONLY
        self.status = "stopped"
        self.telemetry = {
            "camera_status": "Inactive",
            "person_detected": "No",
            "employee_status": "Employee Missing",
            "tracked_person_id": "None",
            "is_present": False,
            "face_detected": "No",
            "eyes_closed": False,
            "sleeping": False,
            "drowsiness_status": "Eyes Open",
            "yawning": False,
            "yawn_status": "Normal",
            "head_direction": "Looking At Screen",
            "looking_at_monitor": True,
            "phone_detected": "No",
            "phone_status": "Phone Not Detected",
            "laptop_detected": "No",
            "chair_detected": "No",
            "score": 0,
            "confidence": "0%",
            "fps": 0
        }

        # Event state transition trackers (prevents logging duplicate or random events)
        self.prev_is_present = False
        self.prev_phone_detected = "No"
        self.prev_looking_at_monitor = True

        # Validation timers & consecutive frame state for Person
        self.missing_start_time = None
        self.consecutive_person_frames = 0
        self.consecutive_missing_frames = 0

        # Phone Detection Timers & Consecutive Frame State
        self.phone_visible_start_time = None
        self.phone_missing_start_time = None
        self.consecutive_phone_frames = 0
        self.consecutive_no_phone_frames = 0

        # Drowsiness Timer
        self.closed_eyes_start_time = None
        
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
            logger.info(f"YOLOv11 model initialized successfully from: {yolo11_path}")
        except Exception as e:
            logger.error(f"Error loading YOLOv11 weights inside webcam service: {e}")
            self.model = YOLO(yolov8_path)

        # Initialize MediaPipe Face Mesh
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe Face Mesh initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing MediaPipe Face Mesh: {e}")
            self.face_mesh = None

    def auto_detect_webcam(self) -> int:
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
        if not self.running:
            return False

        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None

        if self.camera_source:
            self.camera_source.release()
            self.camera_source = None

        if hasattr(self, 'face_mesh') and self.face_mesh:
            try:
                self.face_mesh.close()
            except Exception:
                pass

        self.status = "stopped"
        self.latest_frame = None
        self.telemetry["camera_status"] = "Inactive"
        self.telemetry["person_detected"] = "No"
        self.telemetry["employee_status"] = "Employee Missing"
        self.telemetry["is_present"] = False
        self.telemetry["phone_detected"] = "No"
        self.telemetry["phone_status"] = "Phone Not Detected"
        self.telemetry["laptop_detected"] = "No"
        self.telemetry["chair_detected"] = "No"
        self.telemetry["score"] = 0
        self.telemetry["confidence"] = "0%"
        self.telemetry["fps"] = 0
        
        logger.info("Webcam YOLO service stopped successfully.")
        return True

    def _record_event(self, event_name: str, details: str):
        """
        Record ONLY real state transition events with timestamp into database.
        Examples: Person Detected, Phone Usage Detected, Employee Missing, Looking Away, Return.
        """
        db = SessionLocal()
        try:
            event_log = CameraDetection(
                camera_id="WEBCAM_DEFAULT",
                timestamp=datetime.utcnow(),
                detections_json={
                    "event": event_name,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            db.add(event_log)
            db.commit()
            logger.info(f"[REAL AI EVENT RECORDED] {event_name}: {details}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record real AI event: {e}")
        finally:
            db.close()

    def _run_loop(self):
        webcam_idx = self.auto_detect_webcam()

        self.camera_source = OpenCVCameraSource(webcam_idx)
        self.status = "running"
        self.telemetry["camera_status"] = "Active Streaming"
        
        prev_time = time.time()
        
        # Optimized Rate Limiting Timers
        last_telemetry_update = 0.0
        telemetry_update_interval = 0.20  # 5 FPS (200ms interval)
        frame_count = 0
        cached_results = None

        while self.running:
            try:
                start_loop = time.time()
                ret, frame = self.camera_source.read()
                if not ret or frame is None:
                    logger.warn("Webcam read return false. Reconnection watchdog alert...")
                    time.sleep(0.05)
                    continue

                height, width, _ = frame.shape
                now = time.time()
                frame_count += 1

                # 1. DETECTION RATE LIMIT (15 FPS): Run YOLO & ByteTrack every 2nd frame
                if frame_count % 2 == 0 or cached_results is None:
                    try:
                        cached_results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False, conf=0.65)[0]
                    except Exception as track_err:
                        logger.debug(f"ByteTrack fallback to predict: {track_err}")
                        cached_results = self.model(frame, verbose=False, conf=0.65)[0]

                results = cached_results
                detections = []
                confidences = []
                
                has_person = "No"
                has_phone = "No"
                has_laptop = "No"
                has_chair = "No"
                tracked_person_id = "None"

                # Parse and render ByteTrack tracking outputs
                for box in results.boxes:
                    cls_id = int(box.cls[0].item())
                    if cls_id not in self.target_classes:
                        continue

                    cls_name = self.target_classes[cls_id]
                    conf = float(box.conf[0].item())
                    if conf < 0.65:
                        continue

                    confidences.append(conf)

                    # Extract ByteTrack tracking ID
                    track_id = None
                    if hasattr(box, 'id') and box.id is not None:
                        try:
                            track_id = int(box.id[0].item())
                        except Exception:
                            track_id = None

                    # Mark triggers
                    if cls_name == "person":
                        has_person = "Yes"
                        if track_id is not None:
                            tracked_person_id = f"Employee #{track_id}"
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
                        "track_id": track_id,
                        "confidence": round(conf, 2),
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h
                    })

                    # Draw colored bounding box with ByteTrack ID label
                    color = self.class_colors[cls_name]
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

                    label_text = f"#{track_id} {cls_name.upper()}: {int(conf * 100)}%" if track_id else f"{cls_name.upper()}: {int(conf * 100)}%"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(frame, (x, y - th - 6), (x + tw + 4, y), color, -1)
                    cv2.putText(frame, label_text, (x + 2, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

                # Compute frame rate FPS
                current_time = time.time()
                elapsed_fps = current_time - prev_time
                prev_time = current_time
                fps = round(1.0 / elapsed_fps, 1) if elapsed_fps > 0 else 0

                # Render live FPS stats onto image
                cv2.putText(frame, f"FPS: {fps}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

                # 2. TELEMETRY RATE LIMIT (5 FPS): Throttled telemetry state calculations & real event logging
                if now - last_telemetry_update >= telemetry_update_interval:
                    last_telemetry_update = now

                    # Person Absence Tracking (3s timer)
                    if has_person == "Yes":
                        self.consecutive_person_frames += 1
                        self.consecutive_missing_frames = 0
                        self.missing_start_time = None

                        if self.consecutive_person_frames >= 2:
                            self.telemetry["person_detected"] = "Yes"
                            self.telemetry["employee_status"] = "Employee Present"
                            self.telemetry["is_present"] = True
                            self.telemetry["tracked_person_id"] = tracked_person_id
                    else:
                        self.consecutive_missing_frames += 1
                        self.consecutive_person_frames = 0

                        if self.consecutive_missing_frames >= 2:
                            if self.missing_start_time is None:
                                self.missing_start_time = now
                            elif now - self.missing_start_time >= 3.0:
                                self.telemetry["person_detected"] = "No"
                                self.telemetry["employee_status"] = "Employee Missing"
                                self.telemetry["is_present"] = False
                                self.telemetry["tracked_person_id"] = "None"

                    # Phone Detection Timer Tracking (2s timers)
                    if has_phone == "Yes":
                        self.consecutive_phone_frames += 1
                        self.consecutive_no_phone_frames = 0
                        self.phone_missing_start_time = None

                        if self.consecutive_phone_frames >= 2:
                            if self.phone_visible_start_time is None:
                                self.phone_visible_start_time = now
                            elif now - self.phone_visible_start_time >= 2.0:
                                self.telemetry["phone_detected"] = "Yes"
                                self.telemetry["phone_status"] = "Phone Usage Detected"
                    else:
                        self.consecutive_no_phone_frames += 1
                        self.consecutive_phone_frames = 0
                        self.phone_visible_start_time = None

                        if self.consecutive_no_phone_frames >= 2:
                            if self.phone_missing_start_time is None:
                                self.phone_missing_start_time = now
                            elif now - self.phone_missing_start_time >= 2.0:
                                self.telemetry["phone_detected"] = "No"
                                self.telemetry["phone_status"] = "Phone Not Detected"

                    # MediaPipe Face Mesh Telemetry
                    face_detected_val = "No"
                    eyes_closed_val = False
                    sleeping_val = False
                    drowsiness_status_val = "Eyes Open"
                    yawning_val = False
                    yawn_status_val = "Normal"
                    head_direction_val = "Looking At Screen"
                    looking_at_monitor_val = True

                    if self.telemetry["is_present"] and self.face_mesh:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        fm_res = self.face_mesh.process(frame_rgb)

                        if fm_res and fm_res.multi_face_landmarks:
                            face_detected_val = "Yes"
                            landmarks = fm_res.multi_face_landmarks[0].landmark

                            # Eye Aspect Ratio (EAR)
                            def calculate_ear(eye_indices):
                                p1 = np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y])
                                p2 = np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y])
                                p3 = np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y])
                                p4 = np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y])
                                p5 = np.array([landmarks[eye_indices[4]].x, landmarks[eye_indices[4]].y])
                                p6 = np.array([landmarks[eye_indices[5]].x, landmarks[eye_indices[5]].y])
                                v1 = np.linalg.norm(p2 - p6)
                                v2 = np.linalg.norm(p3 - p5)
                                h_dist = np.linalg.norm(p1 - p4)
                                return (v1 + v2) / (2.0 * h_dist) if h_dist > 0 else 0.0

                            left_ear = calculate_ear([362, 385, 387, 263, 373, 380])
                            right_ear = calculate_ear([33, 160, 158, 133, 153, 144])
                            avg_ear = (left_ear + right_ear) / 2.0

                            if avg_ear < 0.20:
                                eyes_closed_val = True
                                if self.closed_eyes_start_time is None:
                                    self.closed_eyes_start_time = now
                                elif now - self.closed_eyes_start_time >= 2.0:
                                    sleeping_val = True
                                    drowsiness_status_val = "Eyes Closed (Sleeping Alert)"
                            else:
                                self.closed_eyes_start_time = None
                                eyes_closed_val = False
                                sleeping_val = False
                                drowsiness_status_val = "Eyes Open"

                            # Mouth Aspect Ratio (MAR)
                            p13 = np.array([landmarks[13].x, landmarks[13].y])
                            p14 = np.array([landmarks[14].x, landmarks[14].y])
                            p78 = np.array([landmarks[78].x, landmarks[78].y])
                            p308 = np.array([landmarks[308].x, landmarks[308].y])
                            mar = np.linalg.norm(p13 - p14) / np.linalg.norm(p78 - p308) if np.linalg.norm(p78 - p308) > 0 else 0
                            if mar > 0.60:
                                yawning_val = True
                                yawn_status_val = "Yawning Detected"
                            else:
                                yawning_val = False
                                yawn_status_val = "Normal"

                            # Head Direction & Looking Away
                            nose = landmarks[1]
                            left_eye = landmarks[33]
                            right_eye = landmarks[263]
                            chin = landmarks[152]

                            eye_center_x = (left_eye.x + right_eye.x) / 2.0
                            eye_dist = abs(right_eye.x - left_eye.x)
                            
                            if eye_dist > 0:
                                yaw_ratio = (nose.x - eye_center_x) / eye_dist
                                pitch_ratio = (nose.y - eye_center_x) / abs(chin.y - nose.y) if abs(chin.y - nose.y) > 0 else 0

                                if yaw_ratio > 0.25:
                                    head_direction_val = "Looking Right"
                                    looking_at_monitor_val = False
                                elif yaw_ratio < -0.25:
                                    head_direction_val = "Looking Left"
                                    looking_at_monitor_val = False
                                elif pitch_ratio > 0.35:
                                    head_direction_val = "Looking Down"
                                    looking_at_monitor_val = False
                                else:
                                    head_direction_val = "Looking At Screen"
                                    looking_at_monitor_val = True

                            for lm in [33, 263, 1, 61, 291, 152]:
                                cx, cy = int(landmarks[lm].x * width), int(landmarks[lm].y * height)
                                cv2.circle(frame, (cx, cy), 2, (0, 255, 255), -1)

                    self.telemetry["face_detected"] = face_detected_val
                    self.telemetry["eyes_closed"] = eyes_closed_val
                    self.telemetry["sleeping"] = sleeping_val
                    self.telemetry["drowsiness_status"] = drowsiness_status_val
                    self.telemetry["yawning"] = yawning_val
                    self.telemetry["yawn_status"] = yawn_status_val
                    self.telemetry["head_direction"] = head_direction_val
                    self.telemetry["looking_at_monitor"] = looking_at_monitor_val

                    # REAL MATHEMATICAL PRODUCTIVITY SCORE FORMULA (0 - 100)
                    score = 0
                    if not self.telemetry["is_present"]:
                        score = 0
                    else:
                        score = 40  # Base score for Person Present
                        if looking_at_monitor_val:
                            score += 30  # + Looking At Screen
                        else:
                            score -= 20  # - Looking Away
                        
                        if has_laptop == "Yes":
                            score += 30  # + Laptop Present
                            
                        if self.telemetry["phone_detected"] == "Yes":
                            score -= 35  # - Phone Usage
                            
                        if sleeping_val:
                            score -= 30  # - Drowsiness penalty
                            
                        score = max(min(score, 100), 0)

                    self.telemetry["score"] = score
                    self.telemetry["laptop_detected"] = has_laptop
                    self.telemetry["chair_detected"] = has_chair
                    self.telemetry["fps"] = fps
                    
                    if confidences:
                        avg_conf = sum(confidences) / len(confidences)
                        self.telemetry["confidence"] = f"{int(avg_conf * 100)}%"
                    else:
                        self.telemetry["confidence"] = "0%"

                    # 3. REAL STATE TRANSITION EVENT LOGGING TO DATABASE
                    if self.telemetry["is_present"] != self.prev_is_present:
                        if self.telemetry["is_present"]:
                            self._record_event("Return", "Employee Present (Person Detected)")
                        else:
                            self._record_event("Employee Missing", "Employee absent continuously for 3+ seconds")
                        self.prev_is_present = self.telemetry["is_present"]

                    if self.telemetry["phone_detected"] == "Yes" and self.prev_phone_detected != "Yes":
                        self._record_event("Phone Usage Detected", "Cell Phone detected continuously for 2+ seconds (conf >= 0.65)")
                        self.prev_phone_detected = "Yes"
                    elif self.telemetry["phone_detected"] == "No" and self.prev_phone_detected != "No":
                        self._record_event("Phone Disappeared", "Cell Phone absent for 2+ seconds")
                        self.prev_phone_detected = "No"

                    if not self.telemetry["looking_at_monitor"] and self.prev_looking_at_monitor:
                        self._record_event("Looking Away", f"Head direction shifted: {self.telemetry['head_direction']}")
                        self.prev_looking_at_monitor = False
                    elif self.telemetry["looking_at_monitor"] and not self.prev_looking_at_monitor:
                        self._record_event("Gaze Restored", "Gaze restored to screen")
                        self.prev_looking_at_monitor = True

                # Encode frame as JPEG byte-stream for MJPEG route
                ret_bytes, jpeg = cv2.imencode('.jpg', frame)
                if ret_bytes:
                    self.latest_frame = jpeg.tobytes()

                # CAMERA SPEED (30 FPS): Control loop rate to ~33ms per frame
                loop_elapsed = time.time() - start_loop
                delay = max(0.033 - loop_elapsed, 0.001)
                time.sleep(delay)

            except Exception as e:
                logger.error(f"Inference error in webcam loop thread: {e}")
                time.sleep(0.05)

    def get_frame(self) -> bytes:
        return self.latest_frame

    def get_telemetry(self) -> dict:
        return self.telemetry
