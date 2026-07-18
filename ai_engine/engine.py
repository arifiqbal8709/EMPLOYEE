import cv2
import time
import requests
import json
import websocket
import threading
from detectors.object_detector import YOLOObjectDetector
from detectors.pose_detector import AttentionTracker
from utils.camera import WebcamStream

# Configuration Defaults (falls back to local simulation if Backend server is unreachable)
BACKEND_HOST = "localhost:8000"
API_URL = f"http://{BACKEND_HOST}/api/v1"
WS_URL = f"ws://{BACKEND_HOST}/ws"

class AIEngineDaemon:
    """
    Main AI Service Loop coordinator.
    Logs in to backend, fetches detection settings, captures webcam,
    runs inference detectors, and dispatches logs to database.
    """
    def __init__(self, username: str = "alice", password: str = "Password123"):
        self.username = username
        self.password = password
        self.access_token = None
        self.headers = {}
        
        # Initialize submodules
        self.camera = WebcamStream(device_index=0)
        self.object_detector = YOLOObjectDetector()
        self.attention_tracker = AttentionTracker()
        
        # Engine execution parameters
        self.check_interval = 5.0      # check stream every X seconds
        self.alert_threshold = 0.70    # confidence threshold
        self.running = False
        self.ws = None
        self.offline_mode = False

    def login_to_backend(self) -> bool:
        """
        Authenticate with the FastAPI backend to verify credentials and fetch token.
        """
        print(f"Connecting to backend auth service at {API_URL}...")
        try:
            response = requests.post(
                f"{API_URL}/auth/login",
                json={"username": self.username, "password": self.password},
                timeout=5
            )
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
                self.headers = {"Authorization": f"Bearer {self.access_token}"}
                print("Authenticated successfully with backend!")
                self.offline_mode = False
                return True
            else:
                print(f"Authentication failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Backend offline or unreachable: {str(e)}")
            
        print("Backend server not reached. Starting AI Engine in Offline-diagnostic mode.")
        self.offline_mode = True
        return False

    def load_settings(self):
        """
        Fetch detection threshold parameters configured in backend.
        """
        if self.offline_mode:
            return
        
        try:
            response = requests.get(f"{API_URL}/ai/settings", headers=self.headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.check_interval = float(data.get("check_interval", 5))
                self.alert_threshold = float(data.get("alert_threshold", 0.70))
                camera_enabled = bool(data.get("camera_enabled", True))
                print(f"Loaded config: Interval={self.check_interval}s, Threshold={self.alert_threshold}, CameraEnabled={camera_enabled}")
                
                if not camera_enabled:
                    print("Monitoring Disabled by backend settings.")
            else:
                print("Failed to sync settings with backend, using defaults.")
        except Exception as e:
            print(f"Error fetching configuration schemas: {str(e)}")

    def send_alert_log(self, distraction_type: str, confidence: float, duration: float):
        """
        Send attention anomaly log to backend SQLite database.
        """
        payload = {
            "distraction_type": distraction_type,
            "confidence": confidence,
            "duration_seconds": duration
        }
        
        if self.offline_mode:
            print(f"[OFFLINE ALERT] Type: {distraction_type.upper()}, Confidence: {confidence}, Time: {duration}s")
            return

        try:
            response = requests.post(
                f"{API_URL}/ai/log",
                headers=self.headers,
                json=payload,
                timeout=3
            )
            if response.status_code == 200:
                print(f"[LOGGED] Dispatched alert detail: {distraction_type}")
            else:
                print(f"Backend transaction failed: {response.text}")
        except Exception as e:
            print(f"Network error reporting alert payload: {str(e)}")

    def setup_ws_socket(self):
        """
        Spawn WebSocket runner in background thread to sustain active connections mapping.
        """
        if self.offline_mode:
            return
        
        def run_ws():
            url = f"{WS_URL}/{self.username}/employee"
            print(f"Initializing websocket socket: {url}")
            try:
                self.ws = websocket.WebSocketApp(
                    url,
                    on_message=self.on_ws_message,
                    on_error=self.on_ws_error,
                    on_close=self.on_ws_close
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"WebSocket client crash: {str(e)}")

        wst = threading.Thread(target=run_ws, daemon=True)
        wst.start()

    def on_ws_message(self, ws, message):
        data = json.loads(message)
        print(f"[WS INCOMING] Message from server: {data}")

    def on_ws_error(self, ws, error):
        print(f"[WS ERROR] Socket transmission glitch: {str(error)}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        print("WebSocket tracking link terminated.")

    def run_inference_loop(self):
        """
        Activate tracking scan sequence.
        """
        self.running = True
        print(f"Starting tracking scan loop. Polling every {self.check_interval} seconds...")
        
        last_check = 0
        
        try:
            while self.running:
                current_time = time.time()
                ret, frame = self.camera.read()
                if not ret:
                    time.sleep(0.5)
                    continue

                # Run inference periodically based on check_interval
                if current_time - last_check >= self.check_interval:
                    last_check = current_time
                    
                    # Sync config from server
                    self.load_settings()

                    # 1. Check pose / gaze tracking (MediaPipe)
                    attention_alerts = self.attention_tracker.analyze_attention(frame)
                    # 2. Check object tracking (YOLO)
                    object_alerts = self.object_detector.detect_distractions(frame, self.alert_threshold)

                    all_alerts = attention_alerts + object_alerts

                    # Log active observations to console
                    if not all_alerts:
                        print(f"[{time.strftime('%H:%M:%S')}] User attentiveness level green. Eye focus normal.")
                    
                    # Process logged violations
                    for alert in all_alerts:
                        # Report to SQLite & sockets
                        self.send_alert_log(
                            distraction_type=alert["class"],
                            confidence=alert["confidence"],
                            # Mock duration calculation for telemetry logs
                            duration=round(random.uniform(5.0, 15.0), 1) if alert["class"] != "no_person" else 5.0
                        )

                # Small sleep to avoid eating up full process frames
                time.sleep(0.05)

        except KeyboardInterrupt:
            print("Processing loop terminated manually.")
        finally:
            self.camera.release()
            if self.ws:
                self.ws.close()
            print("AI Engine safely shutdown.")

    def start(self):
        self.login_to_backend()
        self.setup_ws_socket()
        self.run_inference_loop()

import random
if __name__ == "__main__":
    import argv
    # Allow logging in with custom options: python engine.py <username>
    import sys
    user = sys.argv[1] if len(sys.argv) > 1 else "alice"
    engine = AIEngineDaemon(username=user, password="Password123")
    engine.start()
