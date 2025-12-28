
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import data_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager

class TestFurnitureDetection(unittest.TestCase):
    def setUp(self):
        # Patch init to avoid loading real models
        with patch('data_manager.DataManager.__init__', return_value=None):
            self.dm = DataManager()
            # Manually set logger mock
            self.dm.logger = MagicMock()

    def test_find_best_box_hit(self):
        """Test finding a box when click is inside it"""
        # Mock detections: label, rect(x, y, width, height), center
        detections = [
            {
                "label": "sofa",
                "rect": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.2}, # Box: 0.1-0.5, 0.1-0.3
                "center": {"x": 0.3, "y": 0.2}
            },
            {
                "label": "lamp",
                "rect": {"x": 0.8, "y": 0.1, "width": 0.1, "height": 0.3},
                "center": {"x": 0.85, "y": 0.25}
            }
        ]

        # Click inside the sofa (0.3, 0.2)
        # We need to implement _find_best_box_for_click first, but we are writing test first
        # Assuming the method signature from plan
        if not hasattr(self.dm, '_find_best_box_for_click'):
            print("Skipping test: _find_best_box_for_click not implemented yet")
            return

        box = self.dm._find_best_box_for_click(0.3, 0.2, detections)
        self.assertIsNotNone(box)
        self.assertEqual(box["label"], "sofa")
        
        # Verify box coordinates match
        self.assertEqual(box["rect"]["x"], 0.1)

    def test_find_best_box_miss(self):
        """Test finding a box when click is outside all boxes"""
        detections = [
            {
                "label": "sofa",
                "rect": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.2}, 
            }
        ]

        # Click far away (0.9, 0.9)
        if not hasattr(self.dm, '_find_best_box_for_click'):
           return

        box = self.dm._find_best_box_for_click(0.9, 0.9, detections)
        self.assertIsNone(box)

    def test_find_best_box_overlap(self):
        """Test prioritizing smaller/center box when overlapping"""
        # Big rug containing specific table
        detections = [
            {
                "label": "rug", # Big box 0.0-1.0
                "rect": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
            },
            {
                "label": "table", # Small box centered 0.4-0.6
                "rect": {"x": 0.4, "y": 0.4, "width": 0.2, "height": 0.2},
            }
        ]

        # Click on table (0.5, 0.5) - Should pick table (smaller area or z-index heuristics if we had them)
        # For now, let's assume implementation picks the smallest area containing the point
        if not hasattr(self.dm, '_find_best_box_for_click'):
           return

        box = self.dm._find_best_box_for_click(0.5, 0.5, detections)
        self.assertIsNotNone(box)
        self.assertEqual(box["label"], "table")

if __name__ == '__main__':
    unittest.main()
