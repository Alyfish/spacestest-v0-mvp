

import unittest
from unittest.mock import MagicMock, patch, ANY
import math
from PIL import Image

# Use a mockup of the FurnitureDetector to avoid importing Ultralytics if missing
from furniture_detector import FurnitureDetector

class TestFurnitureDetector(unittest.TestCase):
    def setUp(self):
        # Mock the YOLO model
        self.mock_model = MagicMock()
        
        # Patch the YOLO import/class usage inside __init__
        with patch('furniture_detector.YOLO', return_value=self.mock_model):
            self.detector = FurnitureDetector()
            self.detector.model = self.mock_model
        
        self.image = Image.new('RGB', (1000, 1000), color='white')

    def test_score_candidate_basic(self):
        """Test the weighted scoring formula"""
        det = {
            "bbox": [400, 400, 600, 600],
            "center": {"x": 500, "y": 500},
            "conf": 0.9,
            "mask": None
        }
        
        # Click center
        # Dist=0, Conf=0.9, Area=Small
        score_center = self.detector._score_candidate(det, 500, 500)
        
        # Click edge
        score_edge = self.detector._score_candidate(det, 500, 400)
        
        self.assertGreater(score_center, score_edge)

    def test_score_mask_bonus_penalty(self):
        """Test mask specific bonuses"""
        # Define a simplistic 100x100 box mask
        # Points: (400,400), (500,400), (500,500), (400,500)
        mask_poly = [[400, 400], [500, 400], [500, 500], [400, 500]]
        
        det = {
            "bbox": [400, 400, 600, 600], # Box is larger 200x200
            "center": {"x": 500, "y": 500},
            "conf": 0.8,
            "mask": mask_poly
        }
        
        # 1. Click Inside Mask (450, 450)
        score_in = self.detector._score_candidate(det, 450, 450)
        
        # 2. Click Outside Mask but Inside Box (550, 550)
        score_out = self.detector._score_candidate(det, 550, 550)
        
        # Difference should be significantly favored to inside
        # Base scores roughly similar (distance diffs aside), but bonus/penalty applies
        self.assertGreater(score_in, score_out)

    def test_ambiguity_boundary(self):
        """Test boundary proximity triggers ambiguity"""
        # Two boxes side by side
        # Box A: 0-500, Box B: 500-1000
        box_a = {
            "id": "A", "label": "A", "bbox": [0, 0, 500, 500],
            "center": {"x": 250, "y": 250}, "conf": 0.9, "score": 0.0 # Placeholder
        }
        box_b = {
            "id": "B", "label": "B", "bbox": [500, 0, 1000, 500],
            "center": {"x": 750, "y": 250}, "conf": 0.85, "score": 0.0
        }
        
        # Pre-calc scores artificially to be distinct enough to NOT trigger score ambiguity
        # but we testing boundary ambiguity
        detections = [box_a, box_b]
        
        # Click exactly on boundary 500 
        # Both boxes are inclusive [0, 500] and [500, 1000]
        # So both should be candidates.
        # And distance to edge (500) is 0 < 10.
        res = self.detector.select_at_click(0.5, 0.25, self.image, detections=detections)
        
        self.assertTrue(res.needs_disambiguation)
        self.assertEqual(res.reason, "ambiguous_boundary")

    def test_micro_inference_trigger(self):
        """Test that micro-inference only runs when valid candidates range are empty/weak"""
        # 1. Strong candidate exists -> No micro inference
        strong_det = {
            "bbox": [400, 400, 600, 600],
            "center": {"x": 500, "y": 500},
            "conf": 0.9
        }
        self.detector._micro_inference = MagicMock(return_value=[])
        
        res = self.detector.select_at_click(0.5, 0.5, self.image, detections=[strong_det])
        
        self.detector._micro_inference.assert_not_called()
        self.assertEqual(res.method, "smart_select")
        
        # 2. No candidates -> Run micro inference
        res = self.detector.select_at_click(0.1, 0.1, self.image, detections=[strong_det]) # Click far away
        
        self.detector._micro_inference.assert_called_once()


if __name__ == '__main__':
    unittest.main()
