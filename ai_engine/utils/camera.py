import cv2
import time
import threading
import logging

logger = logging.getLogger("ai_engine.camera_stream")

class WebcamStream:
    """
    Optimized OpenCV Stream Capturing thread.
    Reads frames as fast as possible in the background to sustain real-time feeds,
    and handles automatic camera reconnects if disconnects occur.
    """
    def __init__(self, source):
        # Allow integer indices for USB, and URL strings for RTSP inputs
        try:
            self.source = int(source)
        except ValueError:
            self.source = source

        self.cap = None
        self.frame = None
        self.ret = False
        self.running = False
        self.connected = False
        self.lock = threading.Lock()
        
        # Thread parameters
        self.thread = None
        
        # Watchdog timing options
        self.reconnect_cooldown = 5.0 # seconds
        self.last_reconnect_attempt = 0.0

    def connect(self):
        """
        Create cv2.VideoCapture session.
        """
        logger.info(f"Opening connection to camera source: {self.source}...")
        self.last_reconnect_attempt = time.time()
        try:
            self.cap = cv2.VideoCapture(self.source)
            if self.cap.isOpened():
                # Read a test frame to ensure stream is working
                ret, frame = self.cap.read()
                if ret:
                    self.ret = True
                    self.frame = frame
                    self.connected = True
                    logger.info(f"Camera [{self.source}] connected successfully.")
                    return True
            
            logger.warn(f"Failed to open camera source: {self.source}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"Error opening camera source connection: {str(e)}")
            self.connected = False
            return False

    def start(self):
        """
        Launch loop thread.
        """
        if self.running:
            return
        
        self.running = True
        self.connect()
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        logger.info(f"Frame capture thread for source {self.source} started.")

    def _update(self):
        """
        Capture frames in background.
        """
        while self.running:
            if self.connected and self.cap is not None:
                try:
                    ret, frame = self.cap.read()
                    if ret:
                        with self.lock:
                            self.frame = frame
                            self.ret = True
                    else:
                        logger.error(f"Camera [{self.source}] disconnected! Frame read returned false.")
                        self.connected = False
                        with self.lock:
                            self.status = "disconnected"
                            self.ret = False
                except Exception as e:
                    logger.error(f"Error reading frame from capture stream: {str(e)}")
                    self.connected = False
                    with self.lock:
                        self.ret = False
            else:
                # Disconnected watchdog - retry reconnection periodically
                now = time.time()
                if now - self.last_reconnect_attempt >= self.reconnect_cooldown:
                    logger.info(f"Reconnection alert! Re-trying handshake on source: {self.source}...")
                    if self.cap is not None:
                        self.cap.release()
                    self.connect()

                # Sleep to prevent burning resources during downtime
                time.sleep(0.5)

            # Avoid tight polling loop bottlenecking CPU
            time.sleep(0.01)

    def read(self):
        """
        Returns latest buffered frame.
        """
        with self.lock:
            return self.ret, self.frame

    def release(self):
        """
        Stop worker thread and free capture stream.
        """
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.connected = False
        logger.info(f"Connection to camera source [{self.source}] closed.")
