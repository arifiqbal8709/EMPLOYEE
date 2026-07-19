import cv2
import time
import numpy as np
import threading
from datetime import datetime, timedelta
from typing import Dict, Generator, Optional
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.camera import Camera
from backend.app.models.user import User
from backend.app.models.activity import KeyboardMouseActivity, ProductivityLog

# Load computer vision libraries with safety fallbacks
try:
    from ultralytics import YOLO
    _has_yolo = True
except ImportError:
    _has_yolo = False

try:
    import mediapipe as mp
    _has_mediapipe = True
except ImportError:
    _has_mediapipe = False

class CameraThread(threading.Thread):
    def __init__(self, camera_id: int, source: str, camera_type: str, user_id: Optional[int]):
        super().__init__()
        self.camera_id = camera_id
        self.source = source
        self.camera_type = camera_type
        self.user_id = user_id
        
        self.running = True
        self.cap = None
        self.latest_frame = None
        
        # Latest telemetry parsed
        self.telemetry = {
            "is_present": False,
            "looking_at_monitor": True,
            "sleeping": False,
            "phone_detected": False,
            "keyboard_active": False,
            "mouse_active": False,
            "score": 100,
            "fps": 0
        }
        
        # Load YOLO model
        self.yolo_model = None
        if _has_yolo:
            try:
                # Load tiny model
                self.yolo_model = YOLO("yolo11n.pt")
            except Exception as e:
                print(f"Error loading YOLOv11 model: {str(e)}")
        
        # Load MediaPipe solution graph
        self.mp_face_mesh = None
        self.face_mesh = None
        self.mp_pose = None
        self.pose = None
        if _has_mediapipe:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.mp_pose = mp.solutions.pose
                self.pose = self.mp_pose.Pose(
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception as e:
                print(f"Error loading MediaPipe models: {str(e)}")

        self.last_db_save = time.time()
        self.closed_eyes_start = None

    def run(self):
        print(f"Starting camera thread for ID {self.camera_id} (source: {self.source})")
        
        # Resolve source value
        if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
            src_val = int(self.source)
        else:
            src_val = self.source

        try:
            if isinstance(src_val, int) or src_val == 0:
                cap = None
                for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                    try:
                        c = cv2.VideoCapture(src_val, backend)
                        if c and c.isOpened():
                            ret, frame = c.read()
                            if ret and frame is not None:
                                cap = c
                                break
                            c.release()
                    except Exception:
                        pass
                if cap is None:
                    cap = cv2.VideoCapture(src_val)
                self.cap = cap
            else:
                self.cap = cv2.VideoCapture(src_val)

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self._update_db_status("connected")
                else:
                    raise Exception("Could not retrieve frame")
            else:
                raise Exception("Could not open video capture")
        except Exception as e:
            print(f"Camera ID {self.camera_id} failed to connect: {str(e)}. Starting simulation mode.")
            self._update_db_status("disconnected")
            if self.cap:
                self.cap.release()
            self.cap = None

        frame_count = 0
        yolo_results = None
        
        while self.running:
            start_time = time.time()
            frame = None

            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    print(f"Camera ID {self.camera_id} disconnected.")
                    self._update_db_status("disconnected")
                    self.cap.release()
                    self.cap = None
            
            # Fallback to simulated animation scene if camera not active
            is_simulated = False
            if frame is None:
                is_simulated = True
                frame = self._generate_simulated_frame()

            # Process frame & run inference
            frame, yolo_results = self._process_frame(frame, frame_count, yolo_results, is_simulated)
            
            # Calculate productivity score dynamics
            self._calculate_productivity_and_save(start_time)
            
            # Store latest annotated frame
            ret_bytes, jpeg = cv2.imencode('.jpg', frame)
            if ret_bytes:
                self.latest_frame = jpeg.tobytes()

            frame_count += 1
            elapsed = time.time() - start_time
            self.telemetry["fps"] = round(1.0 / elapsed, 1) if elapsed > 0 else 0
            
            # Control frame rate (approx 15-20 FPS)
            delay = max(0.05 - elapsed, 0.001)
            time.sleep(delay)

        if self.cap:
            self.cap.release()
        if self.face_mesh:
            self.face_mesh.close()
        if self.pose:
            self.pose.close()

    def _update_db_status(self, status: str):
        db = SessionLocal()
        try:
            db_cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
            if db_cam:
                db_cam.status = status
                db.commit()
            if self.user_id:
                db_user = db.query(User).filter(User.id == self.user_id).first()
                if db_user:
                    db_user.status = "active" if status == "connected" else "absent"
                    db.commit()
        except Exception as e:
            print(f"Error updating status in DB: {str(e)}")
        finally:
            db.close()

    def _process_frame(self, frame, frame_count, cached_yolo_results, is_simulated):
        h, w, _ = frame.shape
        now = time.time()

        # Target COCO classes: Person (0), Chair (56), Laptop (63), Mouse (64), Keyboard (66), Cell Phone (67), Bottle (39), Book (73)
        target_classes = {
            0: "Person",
            67: "Cell Phone",
            63: "Laptop",
            66: "Keyboard",
            64: "Mouse",
            39: "Bottle",
            73: "Book",
            56: "Chair"
        }
        
        # 1. Resize small frame for real-time inference speed
        small_frame = cv2.resize(frame, (640, 480))
        sh, sw, _ = small_frame.shape

        raw_person_detected = False
        raw_phone_detected = False
        raw_laptop_detected = False

        # 2. RUN REAL YOLOV11 OBJECT DETECTION INFERENCE (conf >= 0.60)
        if self.yolo_model and frame_count % 2 == 0:
            try:
                cached_yolo_results = self.yolo_model.predict(small_frame, conf=0.60, verbose=False)
            except Exception as e:
                print(f"YOLOv11 real inference predict error: {e}")

        if cached_yolo_results:
            for result in cached_yolo_results:
                boxes = result.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf < 0.60:
                        continue

                    cls_id = int(box.cls[0])
                    if cls_id in target_classes:
                        xyxy = box.xyxy[0].tolist()
                        
                        # Scale coordinates back to original frame
                        rx1 = int(xyxy[0] * w / sw)
                        ry1 = int(xyxy[1] * h / sh)
                        rx2 = int(xyxy[2] * w / sw)
                        ry2 = int(xyxy[3] * h / sh)
                        
                        label_name = target_classes[cls_id]
                        label = f"{label_name} {round(conf * 100)}%"
                        
                        color = (0, 255, 0) # Green for Person / Chair
                        if cls_id == 67: # Cell Phone
                            color = (0, 0, 255) # Red
                            raw_phone_detected = True
                        elif cls_id == 63: # Laptop
                            color = (255, 255, 0) # Cyan
                            raw_laptop_detected = True
                        elif cls_id in [64, 66]: # Mouse / Keyboard
                            color = (255, 0, 255) # Magenta
                        elif cls_id == 0: # Person
                            raw_person_detected = True
                            color = (0, 255, 0)

                        # Draw live bounding box & confidence score on frame
                        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 2)
                        cv2.putText(frame, label, (rx1, max(ry1 - 10, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 3. CONTINUOUS ABSENCE / PRESENCE TRACKING (> 3 SECONDS)
        if raw_person_detected:
            self.last_db_save = now
            self.telemetry["is_present"] = True
        else:
            # If no person detected continuously for > 3 seconds, set missing
            if hasattr(self, 'closed_eyes_start') and self.closed_eyes_start and (now - self.closed_eyes_start > 3.0):
                self.telemetry["is_present"] = False

        # 4. CONTINUOUS PHONE USAGE TRACKING (> 2 SECONDS)
        if raw_phone_detected and self.telemetry["is_present"]:
            if not hasattr(self, 'phone_seen_start') or self.phone_seen_start is None:
                self.phone_seen_start = now
            elif now - self.phone_seen_start >= 2.0:
                self.telemetry["phone_detected"] = True
        else:
            self.phone_seen_start = None
            self.telemetry["phone_detected"] = False

        # 5. RUN REAL MEDIAPIPE FACE MESH INFERENCE
        raw_looking_monitor = True
        raw_sleeping = False

        if self.telemetry["is_present"]:
            frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            if self.face_mesh:
                fm_res = self.face_mesh.process(frame_rgb)
                if fm_res.multi_face_landmarks:
                    landmarks = fm_res.multi_face_landmarks[0].landmark
                    
                    # Eye Aspect Ratio (EAR) calculation for blinking & drowsiness
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
                        if not hasattr(self, 'closed_eyes_start') or self.closed_eyes_start is None:
                            self.closed_eyes_start = now
                        elif now - self.closed_eyes_start >= 2.0:
                            raw_sleeping = True
                    else:
                        self.closed_eyes_start = None

                    # Head Pose & Gaze Orientation Tracking
                    nose = landmarks[1]
                    left_eye = landmarks[33]
                    right_eye = landmarks[263]
                    chin = landmarks[152]
                    
                    eye_center_x = (left_eye.x + right_eye.x) / 2.0
                    eye_dist = abs(right_eye.x - left_eye.x)
                    
                    if eye_dist > 0:
                        yaw_ratio = (nose.x - eye_center_x) / eye_dist
                        pitch_ratio = (nose.y - eye_center_x) / abs(chin.y - nose.y) if abs(chin.y - nose.y) > 0 else 0

                        if abs(yaw_ratio) > 0.25 or pitch_ratio > 0.35:
                            raw_looking_monitor = False

                    # Render key face mesh landmarks
                    for lm in [33, 263, 1, 61, 291, 152]:
                        cx, cy = int(landmarks[lm].x * w), int(landmarks[lm].y * h)
                        cv2.circle(frame, (cx, cy), 2, (0, 255, 255), -1)

        self.telemetry["sleeping"] = raw_sleeping
        self.telemetry["looking_at_monitor"] = raw_looking_monitor
        self.telemetry["laptop_detected"] = raw_laptop_detected

        return frame, cached_yolo_results
                                
        return frame, cached_yolo_results

    def _generate_simulated_frame(self) -> np.ndarray:
        # Create clean standby canvas when camera stream is standby or offline
        canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(canvas, f"CAMERA STREAM STANDBY", (180, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)
        cv2.putText(canvas, f"Endpoint: {self.source}", (220, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)
        return canvas

    def _calculate_productivity_and_save(self, start_time):
        current_time = time.time()
        
        # Identify active keyboard/mouse clicks
        db = SessionLocal()
        keyboard_strokes = 0
        mouse_clicks = 0
        
        try:
            if self.user_id:
                # Query activity within past 10 seconds
                cutoff = datetime.utcnow() - timedelta(seconds=10)
                latest_acts = db.query(KeyboardMouseActivity).filter(
                    KeyboardMouseActivity.user_id == self.user_id,
                    KeyboardMouseActivity.timestamp >= cutoff
                ).all()
                for act in latest_acts:
                    keyboard_strokes += act.keyboard_strokes
                    mouse_clicks += act.mouse_clicks

            # Compute current score
            # Base = 100
            score = 100
            
            self.telemetry["keyboard_active"] = keyboard_strokes > 5
            self.telemetry["mouse_active"] = mouse_clicks > 3

            if not self.telemetry["is_present"]:
                score = 0
            elif self.telemetry["sleeping"]:
                score = 10 # Extremely low score
            else:
                # Penalties
                if self.telemetry["phone_detected"]:
                    score -= 40
                if not self.telemetry["looking_at_monitor"]:
                    score -= 25
                if not self.telemetry["keyboard_active"] and not self.telemetry["mouse_active"]:
                    score -= 15 # Idle penalty
                
                # Minimum bounds
                score = max(score, 0)

            self.telemetry["score"] = score

            # Save in database every 10 seconds to avoid flooding
            if current_time - self.last_db_save >= 10:
                self.last_db_save = current_time
                
                # Check status
                if self.user_id:
                    db_user = db.query(User).filter(User.id == self.user_id).first()
                    if db_user:
                        if not self.telemetry["is_present"]:
                            db_user.status = "absent"
                        elif self.telemetry["sleeping"] or (not self.telemetry["keyboard_active"] and not self.telemetry["mouse_active"] and not self.telemetry["looking_at_monitor"]):
                            db_user.status = "idle"
                        else:
                            db_user.status = "active"
                        db.commit()

                # Add log
                prod_log = ProductivityLog(
                    user_id=self.user_id if self.user_id else 1,
                    camera_id=self.camera_id,
                    score=self.telemetry["score"],
                    is_present=self.telemetry["is_present"],
                    looking_at_monitor=self.telemetry["looking_at_monitor"],
                    sleeping=self.telemetry["sleeping"],
                    phone_detected=self.telemetry["phone_detected"],
                    keyboard_active=self.telemetry["keyboard_active"],
                    mouse_active=self.telemetry["mouse_active"],
                    timestamp=datetime.utcnow()
                )
                db.add(prod_log)
                db.commit()
                
        except Exception as e:
            print(f"Error executing score calculations DB logs: {str(e)}")
            db.rollback()
        finally:
            db.close()


class CameraServiceManager:
    def __init__(self):
        self.threads: Dict[int, CameraThread] = {}
        self.testing_mode: bool = True  # Development / testing mode flag

    def set_testing_mode(self, enabled: bool):
        self.testing_mode = enabled
        # Update existing streams if testing mode changed
        for cam_id, thread in list(self.threads.items()):
            source = "0" if enabled else thread.source
            self.start_camera(cam_id, source, thread.camera_type, thread.user_id)

    def start_camera(self, camera_id: int, source: str, camera_type: str, user_id: Optional[int]) -> bool:
        """
        Starts an asynchronous capture thread for the given camera configurations.
        """
        # In testing mode, automatically override capture source to laptop webcam (0)
        active_source = "0" if self.testing_mode else source

        # Stop existing if running
        self.stop_camera(camera_id)
        
        thread = CameraThread(camera_id, active_source, camera_type, user_id)
        thread.daemon = True
        thread.start()
        
        self.threads[camera_id] = thread
        return True

    def stop_camera(self, camera_id: int):
        if camera_id in self.threads:
            thread = self.threads[camera_id]
            thread.running = False
            thread.join(timeout=2.0)
            del self.threads[camera_id]
            return True
        return False

    def get_stream(self, camera_id: int) -> Generator[bytes, None, None]:
        """
        MJPEG generator stream: yields encoded Jpegs sequentially.
        """
        # Ensure camera is running
        if camera_id not in self.threads:
            # Try to load camera profile from DB
            db = SessionLocal()
            try:
                db_cam = db.query(Camera).filter(Camera.id == camera_id).first()
                if db_cam:
                    self.start_camera(db_cam.id, db_cam.source, db_cam.type, db_cam.user_id)
                else:
                    # Generic fallback mock
                    self.start_camera(camera_id, "0", "usb", None)
            finally:
                db.close()

        # Wait a moment to retrieve first frame
        time.sleep(0.5)
        
        while camera_id in self.threads:
            thread = self.threads[camera_id]
            if thread.latest_frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + thread.latest_frame + b'\r\n')
            else:
                # Blank frame holding spinner
                time.sleep(0.1)

    def get_telemetry(self, camera_id: int) -> dict:
        if camera_id in self.threads:
            return self.threads[camera_id].telemetry
        return {
            "is_present": False,
            "looking_at_monitor": False,
            "sleeping": False,
            "phone_detected": False,
            "keyboard_active": False,
            "mouse_active": False,
            "score": 0,
            "fps": 0
        }

camera_service_manager = CameraServiceManager()
