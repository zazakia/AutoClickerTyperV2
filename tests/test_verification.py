
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.verification import verify_action, boxes_overlap


# ---------------------------------------------------------------------------
# Test boxes_overlap
# ---------------------------------------------------------------------------

class TestBoxesOverlap(unittest.TestCase):
    """Unit tests for the boxes_overlap() helper function."""

    def test_identical_boxes_fully_overlap(self):
        """Two identical boxes have 100% overlap → True."""
        self.assertTrue(boxes_overlap((10, 10, 50, 50), (10, 10, 50, 50)))

    def test_no_overlap_returns_false(self):
        """Completely separated boxes → False."""
        self.assertFalse(boxes_overlap((0, 0, 10, 10), (100, 100, 10, 10)))

    def test_touching_edges_no_intersection(self):
        """Boxes that touch at a single edge have zero intersection → False."""
        # box1 ends at x=10, box2 starts at x=10 — no interior overlap
        self.assertFalse(boxes_overlap((0, 0, 10, 10), (10, 0, 10, 10)))

    def test_partial_overlap_above_threshold(self):
        """Partial overlap that is > 50% of the smaller box → True."""
        # box1: (0,0,10,10) area=100; box2: (5,0,10,10) overlap=(5x10)=50
        # overlap / min_area = 50/100 = 0.5, NOT > 0.5 yet
        # Use (4,0,10,10): overlap = 6*10=60 / 100 = 0.6 > 0.5
        self.assertTrue(boxes_overlap((0, 0, 10, 10), (4, 0, 10, 10)))

    def test_partial_overlap_below_threshold(self):
        """Very small overlap (< 50% of smaller box) → False."""
        # box1: (0,0,10,10) area=100; box2: (8,0,10,10) overlap=(2x10)=20 / 100 = 0.2
        self.assertFalse(boxes_overlap((0, 0, 10, 10), (8, 0, 10, 10)))

    def test_custom_threshold_lower(self):
        """Custom threshold of 0.2 accepts a smaller overlap."""
        # 2x10=20 overlap / 100 area = 0.2, exactly at threshold (not strictly >)
        # Use threshold=0.15 so 0.2 > 0.15
        self.assertTrue(boxes_overlap((0, 0, 10, 10), (8, 0, 10, 10), threshold=0.15))

    def test_zero_area_box_returns_false(self):
        """A zero-area box triggers divide-by-zero guard → False."""
        self.assertFalse(boxes_overlap((5, 5, 0, 0), (5, 5, 50, 50)))

    def test_malformed_input_returns_false(self):
        """Non-iterable input is handled gracefully → False."""
        self.assertFalse(boxes_overlap(None, (0, 0, 10, 10)))
        self.assertFalse(boxes_overlap((0, 0, 10, 10), None))

    def test_small_box_inside_large_box(self):
        """Small box fully contained within large box → True (100% of small box overlaps)."""
        large = (0, 0, 100, 100)
        small = (10, 10, 20, 20)
        self.assertTrue(boxes_overlap(large, small))


# ---------------------------------------------------------------------------
# Test verify_action  (existing tests, kept and improved)
# ---------------------------------------------------------------------------

class TestVerifyAction(unittest.TestCase):
    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_success_button_gone(self, mock_sleep, mock_scan):
        """When the keyword is no longer found at original location → success."""
        mock_scan.return_value = []
        verified, reason = verify_action("Accept", (100, 100, 50, 50))
        self.assertTrue(verified)
        self.assertIn("is gone", reason)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_failure_button_still_present(self, mock_sleep, mock_scan):
        """When keyword is found with strong overlap at original spot → failure."""
        mock_scan.return_value = [{'keyword': 'Accept', 'box': (105, 105, 40, 40)}]
        verified, reason = verify_action("Accept", (100, 100, 50, 50), timeout=0.1)
        self.assertFalse(verified)
        self.assertIn("Verification Warning", reason)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_found_elsewhere_is_success(self, mock_sleep, mock_scan):
        """Keyword found at a far-away location means the original is gone → success."""
        mock_scan.return_value = [{'keyword': 'Accept', 'box': (500, 500, 50, 50)}]
        verified, reason = verify_action("Accept", (100, 100, 50, 50))
        self.assertTrue(verified)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_ocr_error_ignored(self, mock_sleep, mock_scan):
        """An OCRError during scan is swallowed; verification eventually times out."""
        from core.exceptions import OCRError
        mock_scan.side_effect = OCRError("scan failed")
        verified, reason = verify_action("Accept", (100, 100, 50, 50), timeout=0.1)
        # Should time out and return False with a warning message
        self.assertFalse(verified)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_generic_exception_ignored(self, mock_sleep, mock_scan):
        """A generic exception during scan is swallowed; verification eventually times out."""
        mock_scan.side_effect = RuntimeError("random crash")
        verified, reason = verify_action("Accept", (100, 100, 50, 50), timeout=0.1)
        self.assertFalse(verified)


if __name__ == '__main__':
    unittest.main()
