import logging
import math
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image

# Try to import YOLO, handle absence gracefully
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

@dataclass
class SelectionResult:
    selected: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    needs_disambiguation: bool
    crop: Image.Image
    method: str  # "smart_select", "fallback_micro", "fallback_blind"
    reason: str
    disambiguation_options: List[Dict[str, Any]]

class FurnitureDetector:
    """
    Advanced furniture detection pipeline using YOLOv8-seg.
    Handles object detection, smart selection scoring, ambiguity resolution,
    and adaptive cropping with segmentation masks.
    """

    def __init__(self, model_path: str = "yolov8n-seg.pt"):
        self.logger = logging.getLogger("spaces_ai.detector")
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(model_path)
                self.logger.info(f"Loaded YOLO model: {model_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load YOLO model {model_path}: {e}")
        else:
            self.logger.warning("ultralytics not installed, furniture detection disabled")

    def detect(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Run global inference on the image.
        Returns a list of raw detections.
        """
        if not self.model:
            return []

        try:
            # Run inference
            # imgsz=640 is standard for YOLOv8
            results = self.model.predict(image, imgsz=640, conf=0.15, verbose=False)
            
            if not results:
                return []

            r = results[0]
            names = r.names
            
            detections = []
            
            # Helper to safely get boxes and masks
            boxes = r.boxes
            masks = r.masks
            
            if boxes is None:
                return []
                
            width, height = image.size

            for i, box in enumerate(boxes):
                # BBox Coords (pixels)
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = names[cls_id] if names else str(cls_id)
                
                # Mask (if available)
                mask_poly = None
                if masks is not None and len(masks) > i:
                    # masks.xy is a list of segments (polygons)
                    # We take the first segment for this object
                    try:
                        # masks.xy[i] returns array of points [[x,y], ...]
                        poly = masks.xy[i]
                        if len(poly) > 0:
                            mask_poly = poly
                    except Exception:
                        pass

                detections.append({
                    "id": f"det_{i}",
                    "label": label,
                    "conf": conf,
                    "bbox": [x1, y1, x2, y2], # Pixel coords
                    "mask": mask_poly,        # Polygon points (pixels) or None
                    "rect_norm": {            # Normalized rect for easy UI usage
                        "x": x1 / width,
                        "y": y1 / height,
                        "width": (x2 - x1) / width,
                        "height": (y2 - y1) / height
                    }, 
                    "center": {
                        "x": (x1 + x2) / 2,
                        "y": (y1 + y2) / 2
                    }
                })

            return detections

        except Exception as e:
            self.logger.error(f"Detection failed: {e}")
            return []

    def select_at_click(
        self, 
        click_x_norm: float, 
        click_y_norm: float, 
        image: Image.Image,
        detections: Optional[List[Dict[str, Any]]] = None
    ) -> SelectionResult:
        """
        Main entry point for handling a user click.
        """
        width, height = image.size
        click_x = click_x_norm * width
        click_y = click_y_norm * height
        
        if detections is None:
            detections = self.detect(image)
            
        # 1. candidate Search
        candidates = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            if x1 <= click_x <= x2 and y1 <= click_y <= y2:
                score = self._score_candidate(det, click_x, click_y)
                det["score"] = score
                candidates.append(det)
                
        # Scored sorting
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        selected = None
        needs_disambiguation = False
        options = []
        method = "smart_select"
        reason = "best_score"

        # 2. Logic Selection
        if candidates:
            # Check for ambiguity
            if len(candidates) > 1:
                # Rule A: Close scores
                if (candidates[0]["score"] - candidates[1]["score"]) < 0.08:
                    needs_disambiguation = True
                    reason = "ambiguous_score"
                
                # Rule B: Boundary Proximity
                # Check if click is near edges of top 2 candidates
                if self._is_near_boundary(click_x, click_y, candidates[0], 10) or \
                   self._is_near_boundary(click_x, click_y, candidates[1], 10):
                    needs_disambiguation = True
                    reason = "ambiguous_boundary"
                    
                if needs_disambiguation:
                    options = candidates[:3]

            selected = candidates[0]
            
            # Confidence Floor check for top candidate
            if selected["conf"] < 0.25:
                # If ALL candidates are weak, maybe force micro-inference?
                # For now just use it but log warning, or maybe trigger fallback?
                pass 

        # 3. Micro-Inference Fallback
        # Trigger if NO candidates OR all candidates are very weak (<0.25)
        all_weak = all(c["conf"] < 0.25 for c in candidates)
        
        if not candidates or all_weak:
            self.logger.info("Low confidence or no candidates, attempting micro-inference...")
            micro_res = self._micro_inference(click_x, click_y, image)
            if micro_res:
                selected = micro_res[0] 
                candidates = micro_res
                method = "fallback_micro"
                reason = "micro_inference_hit"
                needs_disambiguation = False # Reset if micro found something solid
            elif not candidates:
                 method = "fallback_blind"
                 reason = "no_detection"

        # 4. Compute Crop
        crop_image = self._compute_crop(image, selected, click_x, click_y)
        
        return SelectionResult(
            selected=selected,
            candidates=candidates,
            needs_disambiguation=needs_disambiguation,
            disambiguation_options=options,
            crop=crop_image,
            method=method,
            reason=reason
        )

    def _score_candidate(self, det: Dict[str, Any], cx: float, cy: float) -> float:
        """
        Score = 0.55*conf + 0.35*(1 - dist) + 0.10*(1 - area)
        + Bonus for mask hit
        - Penalty for mask miss (bbox only hit)
        """
        conf = det.get("conf", 0.0)
        
        # 1. Dist Norm
        bx1, by1, bx2, by2 = det["bbox"]
        bw, bh = bx2 - bx1, by2 - by1
        bbox_cx, bbox_cy = det["center"]["x"], det["center"]["y"]
        max_dist = math.sqrt((bw/2)**2 + (bh/2)**2) or 1.0
        dist = math.sqrt((cx - bbox_cx)**2 + (cy - bbox_cy)**2)
        dist_norm = min(1.0, dist / max_dist)
        
        # 2. Area Norm (heuristic)
        area_val = bw * bh
        area_norm = min(1.0, area_val / (2000*2000))

        base_score = (0.55 * conf) + (0.35 * (1.0 - dist_norm)) + (0.10 * (1.0 - area_norm))
        
        # 3. Mask Check
        if det.get("mask") is not None and len(det["mask"]) > 0:
            # Check if point inside polygon
            # cv2.pointPolygonTest requires float32 array
            poly = np.array(det["mask"], dtype=np.float32)
            # dist > 0 inside, < 0 outside, = 0 on edge
            inside = cv2.pointPolygonTest(poly, (cx, cy), False) 
            
            if inside >= 0:
                base_score += 0.15 # Bonus
            else:
                base_score -= 0.10 # Penalty (clicked in bbox void)
                
        # 4. Confidence Floor
        if conf < 0.25:
             base_score *= 0.5 # Heavy penalty for low confidence
             
        return base_score

    def _is_near_boundary(self, cx: float, cy: float, det: Dict[str, Any], threshold: float = 10.0) -> bool:
        """Check if click is within threshold pixels of bounding box edge"""
        x1, y1, x2, y2 = det["bbox"]
        # Distances to each edge
        d_left = abs(cx - x1)
        d_right = abs(cx - x2)
        d_top = abs(cy - y1)
        d_bottom = abs(cy - y2)
        
        min_dist = min(d_left, d_right, d_top, d_bottom)
        return min_dist < threshold

    def _compute_crop(
        self, 
        image: Image.Image, 
        det: Optional[Dict[str, Any]], 
        cx: float, 
        cy: float
    ) -> Image.Image:
        """Adaptive crop with padding."""
        width, height = image.size
        
        if not det:
            # Fallback blind crop (10%)
            box_size = 0.1
            left = max(0, int(cx - (width * box_size / 2)))
            top = max(0, int(cy - (height * box_size / 2)))
            right = min(width, int(cx + (width * box_size / 2)))
            bottom = min(height, int(cy + (height * box_size / 2)))
            return image.crop((left, top, right, bottom))
            
        x1, y1, x2, y2 = det["bbox"]
        w = x2 - x1
        h = y2 - y1
        
        # Adaptive Padding
        p = 0.04
        aspect = w / h if h > 0 else 1.0
        
        pad_l = pad_r = w * p
        pad_t = pad_b = h * p
        
        if aspect > 1.6: # Wide
            pad_t = h * (p * 1.6)
            pad_b = h * (p * 1.6)
        elif aspect < 0.625: # Tall
            pad_l = w * (p * 1.6)
            pad_r = w * (p * 1.6)
            
        label = det.get("label", "").lower()
        if any(x in label for x in ["sofa", "couch", "bed", "table"]):
            pad_b += h * 0.05
        
        nx1 = max(0, int(x1 - pad_l))
        ny1 = max(0, int(y1 - pad_t))
        nx2 = min(width, int(x2 + pad_r))
        ny2 = min(height, int(y2 + pad_b))
        
        return image.crop((nx1, ny1, nx2, ny2))

    def _micro_inference(self, cx: float, cy: float, full_image: Image.Image) -> List[Dict[str, Any]]:
        """Run high-res inference on a crop."""
        if not self.model:
            return []
            
        width, height = full_image.size
        crop_size = 640
        x1 = max(0, int(cx - crop_size//2))
        y1 = max(0, int(cy - crop_size//2))
        x2 = min(width, int(cx + crop_size//2))
        y2 = min(height, int(cy + crop_size//2))
        
        micro_crop = full_image.crop((x1, y1, x2, y2))
        
        try:
            results = self.model.predict(micro_crop, imgsz=640, conf=0.10, verbose=False)
            if not results or not results[0].boxes:
                return []
                
            detections = []
            names = results[0].names
            
            for box in results[0].boxes:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                
                # Check containment
                rel_cx = cx - x1
                rel_cy = cy - y1
                
                if bx1 <= rel_cx <= bx2 and by1 <= rel_cy <= by2:
                    detections.append({
                        "label": names[int(box.cls[0])],
                        "conf": float(box.conf[0]),
                        "bbox": [bx1 + x1, by1 + y1, bx2 + x1, by2 + y1],
                        "center": {
                            "x": (bx1 + bx2)/2 + x1,
                            "y": (by1 + by2)/2 + y1
                        },
                        "score": float(box.conf[0])
                    })
            return detections
            
        except Exception as e:
            self.logger.warning(f"Micro-inference failed: {e}")
            return []

furniture_detector = FurnitureDetector()
