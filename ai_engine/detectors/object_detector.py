import cv2
import logging
from ultralytics import YOLO

# Setup module logging
logger = logging.getLogger("ai_engine.yolo_detector")

class YOLOObjectDetector:
    """
    YOLOv11 Detector encapsulating inference and box drawing logic.
    Target classes: Person, Mobile Phone, Laptop, Chair.
    """
    def __init__(self, model_path: str = "yolo11n.pt"):
        logger.info(f"Loading YOLOv11 model from {model_path}...")
        try:
            self.model = YOLO(model_path)
            logger.info("YOLOv11 model loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading YOLO model weights: {str(e)}")
            # Try falling back to yolov8n if 11 is not resolvable
            self.model = YOLO("yolov8n.pt")
            logger.info("Flipped fallback weights yolov8n.")

        # Class maps to filter COCO classes
        # 0: person, 56: chair, 63: laptop, 67: cell phone
        self.target_classes = {
            0: "person",
            56: "chair",
            63: "laptop",
            67: "cell phone"
        }

        # Colors for target classes (BGR)
        self.class_colors = {
            "person": (255, 100, 0),       # Vibrant Light Blue
            "cell phone": (0, 0, 255),      # Warning Red
            "laptop": (0, 255, 0),          # Activity Green
            "chair": (150, 0, 150)          # Secondary Purple
        }

    def detect(self, frame, conf_threshold: float = 0.35):
        """
        Run YOLOv11 inference on the open CV image, drawing box boundaries
        and returning the objects list coords as JSON format.
        """
        if frame is None:
            return [], frame

        height, width, _ = frame.shape
        detections = []
        annotated_frame = frame.copy()

        try:
            # Run YOLO inference
            results = self.model(annotated_frame, verbose=False, conf=conf_threshold)[0]
            
            # Extract box data
            for box in results.boxes:
                cls_id = int(box.cls[0].item())
                if cls_id not in self.target_classes:
                    continue

                cls_name = self.target_classes[cls_id]
                conf = float(box.conf[0].item())
                
                # Get normalized/pixel coords
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x = int(x1)
                y = int(y1)
                w = int(x2 - x1)
                h = int(y2 - y1)

                detections.append({
                    "class": cls_name,
                    "confidence": round(conf, 2),
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h
                })

                # Draw bounding box
                color = self.class_colors[cls_name]
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)

                # Draw professional labels
                label_text = f"{cls_name.upper()} {int(conf * 100)}%"
                font_scale = 0.45
                thickness = 1
                
                # Text size extraction
                (text_width, text_height), baseline = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
                )
                
                # Draw text border box
                cv2.rectangle(
                    annotated_frame, 
                    (x, max(0, y - text_height - 6)), 
                    (x + text_width + 4, y), 
                    color, 
                    -1
                )
                
                cv2.putText(
                    annotated_frame, 
                    label_text, 
                    (x + 2, max(text_height + 2, y - 3)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    font_scale, 
                    (255, 255, 255), 
                    thickness, 
                    cv2.LINE_AA
                )

        except Exception as e:
            logger.error(f"Inference processing failure: {str(e)}")

        return detections, annotated_frame
