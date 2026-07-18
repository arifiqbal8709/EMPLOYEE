import cv2
import time
import numpy as np
import threading
from datetime import datetime
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
        
        # Attempt to open Video Capture
        if self.source.isdigit():
            src_val = int(self.source)
        else:
            src_val = self.source

        try:
            self.cap = cv2.VideoCapture(src_val)
            # Try to grab a frame to check connect status
            ret, frame = self.cap.read()
            if not ret:
                raise Exception("Could not retrieve frame")
            
            # Update camera status in DB
            self._update_db_status("connected")
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
        # Target classes: Person (0), Chair (56), Laptop (63), Cell phone (67)
        target_classes = {0: "Person", 56: "Chair", 63: "Laptop", 67: "Mobile Phone"}
        
        # 1. Resize for performance optimization
        small_frame = cv2.resize(frame, (640, 480))
        sh, sw, _ = small_frame.shape

        # Reset current frame detections
        self.telemetry["is_present"] = False
        self.telemetry["phone_detected"] = False
        self.telemetry["sleeping"] = False
        self.telemetry["looking_at_monitor"] = True

        # Simulating detections or running actual YOLO
        if is_simulated:
            # Create simulated bounding boxes
            sim_time = time.time()
            # Person present
            self.telemetry["is_present"] = True
            cv2.rectangle(frame, (80, 50), (560, 470), (0, 255, 0), 2)
            cv2.putText(frame, "Person (Simulated 98%)", (80, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Laptop present
            cv2.rectangle(frame, (150, 300), (450, 460), (255, 100, 0), 2)
            cv2.putText(frame, "Laptop (Simulated 99%)", (150, 290), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)

            # Interactive phone trigger (cycling usage state)
            if int(sim_time / 6) % 3 == 0:
                self.telemetry["phone_detected"] = True
                cv2.rectangle(frame, (420, 220), (480, 280), (0, 0, 255), 2)
                cv2.putText(frame, "Mobile Phone (Simulated 94%)", (380, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Simulated Head direction checking (looking away)
            gaze_state = int(sim_time / 10) % 3
            if gaze_state == 1:
                self.telemetry["looking_at_monitor"] = False
                color = (0, 165, 255)
                cv2.line(frame, (320, 180), (120, 150), color, 3) # Vector looking away
                cv2.putText(frame, "Diverted Gaze: Looking Left", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            elif gaze_state == 2:
                # sleeping state
                self.telemetry["sleeping"] = True
                cv2.putText(frame, "Drowsiness Alert: Eyes Closed", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                cv2.line(frame, (320, 180), (320, 180 + 80), (0, 255, 0), 3) # Vector pointing straight
                cv2.putText(frame, "Gaze Status: Looking at Monitor", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Draw basic stick-face meshes & grid to look cool
            cv2.circle(frame, (320, 180), 60, (200, 200, 200), 1)
            # Eyes
            cv2.circle(frame, (300, 170), 8, (255, 100, 0), -1 if not self.telemetry["sleeping"] else 1)
            cv2.circle(frame, (340, 170), 8, (255, 100, 0), -1 if not self.telemetry["sleeping"] else 1)
            # Pose lines
            cv2.line(frame, (320, 240), (320, 360), (200, 200, 200), 2)
            cv2.line(frame, (320, 260), (220, 290), (200, 200, 200), 2)
            cv2.line(frame, (320, 260), (420, 290), (200, 200, 200), 2)

        else:
            # 2. RUN REAL YOLO INFERENCE
            if self.yolo_model and frame_count % 3 == 0:
                try:
                    cached_yolo_results = self.yolo_model.predict(small_frame, conf=0.4, verbose=False)
                except Exception as e:
                    print(f"YOLO predict error: {e}")

            if cached_yolo_results:
                for result in cached_yolo_results:
                    boxes = result.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        if cls_id in target_classes:
                            conf = float(box.conf[0])
                            xyxy = box.xyxy[0].tolist()
                            
                            # Scale coordinates back to original frame
                            rx1 = int(xyxy[0] * w / sw)
                            ry1 = int(xyxy[1] * h / sh)
                            rx2 = int(xyxy[2] * w / sw)
                            ry2 = int(xyxy[3] * h / sh)
                            
                            label = f"{target_classes[cls_id]} ({round(conf * 100)}%)"
                            color = (0, 255, 0) # Green for Person/Chair
                            if cls_id == 67: # Phone
                                color = (0, 0, 255) # Red
                                self.telemetry["phone_detected"] = True
                            elif cls_id == 63: # Laptop
                                color = (255, 100, 0) # Blue
                            
                            if cls_id == 0:
                                self.telemetry["is_present"] = True

                            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), color, 2)
                            cv2.putText(frame, label, (rx1, max(ry1 - 10, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 3. RUN REAL MEDIAPIPE INFRASTRUCTURE (mesh and pose skeleton)
            if self.telemetry["is_present"]:
                frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Face Mesh for eyes and orientation tracking
                if self.face_mesh:
                    fm_res = self.face_mesh.process(frame_rgb)
                    if fm_res.multi_face_landmarks:
                        landmarks = fm_res.multi_face_landmarks[0].landmark
                        
                        # EAR blinking calculation values base spots
                        # Left Eye: 362, 385, 387, 263, 373, 380
                        # Right Eye: 33, 160, 158, 133, 153, 144
                        def ear_calc(eye_landmarks, landmarks):
                            # vertical distances
                            v1 = np.linalg.norm(np.array([landmarks[eye_landmarks[1]].x, landmarks[eye_landmarks[1]].y]) - 
                                                np.array([landmarks[eye_landmarks[5]].x, landmarks[eye_landmarks[5]].y]))
                            v2 = np.linalg.norm(np.array([landmarks[eye_landmarks[2]].x, landmarks[eye_landmarks[2]].y]) - 
                                                np.array([landmarks[eye_landmarks[4]].x, landmarks[eye_landmarks[4]].y]))
                            # horizontal distance
                            h = np.linalg.norm(np.array([landmarks[eye_landmarks[0]].x, landmarks[eye_landmarks[0]].y]) - 
                                               np.array([landmarks[eye_landmarks[3]].x, landmarks[eye_landmarks[3]].y]))
                            return (v1 + v2) / (2.0 * h) if h > 0 else 0.0

                        left_ear = ear_calc([362, 385, 387, 263, 373, 380], landmarks)
                        right_ear = ear_calc([33, 160, 158, 133, 153, 144], landmarks)
                        avg_ear = (left_ear + right_ear) / 2.0
                        
                        # Threshold status closed eyes
                        if avg_ear < 0.21:
                            if self.closed_eyes_start is None:
                                self.closed_eyes_start = time.time()
                            elif time.time() - self.closed_eyes_start > 2.0:
                                self.telemetry["sleeping"] = True
                        else:
                            self.closed_eyes_start = None

                        # Head orientation direction simple projection
                        # Using relative coordinates of nose tip (1) vs left/right temples (127, 356)
                        nose = landmarks[1]
                        left_temple = landmarks[127]
                        right_temple = landmarks[356]
                        
                        # Horizontal yaw offset ratios
                        dist_left = nose.x - left_temple.x
                        dist_right = right_temple.x - nose.x
                        total_width = right_temple.x - left_temple.x
                        
                        if total_width > 0:
                            ratio = (dist_left - dist_right) / total_width
                            # If ratio exceeds threshold, head is looking away
                            if abs(ratio) > 0.18:
                                self.telemetry["looking_at_monitor"] = False
                                
                        # Render Face mesh contours on frame
                        for lm in [33, 263, 1, 61, 291, 199]: # Draw main anchors
                            cx, cy = int(lm_x := landmarks[lm].x * w), int(landmarks[lm].y * h)
                            cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)

                # Pose model for skeleton
                if self.pose:
                    pose_res = self.pose.process(frame_rgb)
                    if pose_res.pose_landmarks:
                        joints = pose_res.pose_landmarks.landmark
                        # Draw upper body pose connections
                        connections = [(11, 12), (11, 23), (12, 24), (23, 24), (11, 13), (12, 14), (13, 15), (14, 16)]
                        for link in connections:
                            pl1 = joints[link[0]]
                            pl2 = joints[link[1]]
                            if pl1.visibility > 0.5 and pl2.visibility > 0.5:
                                p1 = (int(pl1.x * w), int(pl1.y * h))
                                p2 = (int(pl2.x * w), int(pl2.y * h))
                                cv2.line(frame, p1, p2, (255, 0, 255), 2)
                                
        return frame, cached_yolo_results

    def _generate_simulated_frame(self) -> np.ndarray:
        # Create solid canvas with high-end matching dashboard color
        canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        # Deep blue background gradient
        for y in range(480):
            canvas[y, :] = [int(15 + y * 0.05), int(10 + y * 0.03), int(40 + y * 0.08)]
        
        # Grid lines looking like telemetry tracking HUD
        for gx in range(0, 640, 80):
            cv2.line(canvas, (gx, 0), (gx, 480), (35, 30, 75), 1)
        for gy in range(0, 480, 80):
            cv2.line(canvas, (0, gy), (640, gy), (35, 30, 75), 1)

        # Technical info Overlay
        cv2.putText(canvas, f"CAMERA SERVICE: {self.source.upper()}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(canvas, f"STATUS: SIMULATION ACTIVE", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(canvas, f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        
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

    def start_camera(self, camera_id: int, source: str, camera_type: str, user_id: Optional[int]) -> bool:
        """
        Starts an asynchronous capture thread for the given camera configurations.
        """
        # Stop existing if running
        self.stop_camera(camera_id)
        
        thread = CameraThread(camera_id, source, camera_type, user_id)
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
