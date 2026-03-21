
import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.exceptions import OCRError




# We patch the heavy external deps at the module level before importing core.ocr
# so the import itself doesn't fail in headless environments.
_mss_mock = MagicMock()
_cv2_mock = MagicMock()
_pytesseract_mock = MagicMock()
_gw_mock = MagicMock()
_fuzz_mock = MagicMock()
# Important: fuzzy matching functions must return integers for comparisons like >= 98
_fuzz_mock.partial_ratio.return_value = 0
_fuzz_mock.ratio.return_value = 0

for _mod_name, _mock_obj in [
    ('mss', _mss_mock),
    ('cv2', _cv2_mock),
    ('pytesseract', _pytesseract_mock),
    ('pygetwindow', _gw_mock),
]:
    sys.modules.setdefault(_mod_name, _mock_obj)

# Patch thefuzz.fuzz used inside ocr.py
_thefuzz_mock = MagicMock()
_thefuzz_mock.fuzz = _fuzz_mock
sys.modules.setdefault('thefuzz', _thefuzz_mock)
sys.modules.setdefault('thefuzz.fuzz', _fuzz_mock)


# ---------------------------------------------------------------------------
# TestCaptureScreen
# ---------------------------------------------------------------------------

class TestCaptureScreen(unittest.TestCase):
    """Tests for capture_screen()."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.ocr.mss')
    def test_capture_screen_success_full(self, mock_mss):
        """capture_screen() returns a PIL Image on success (full screen)."""
        from PIL import Image
        from core.ocr import capture_screen

        # Build a mock sct_img
        mock_sct_img = MagicMock()
        mock_sct_img.size = (10, 10)
        # bgra bytes: 10*10*4 bytes
        mock_sct_img.bgra = bytes([0] * 400)

        mock_sct = MagicMock()
        mock_sct.monitors = [None, {'top': 0, 'left': 0, 'width': 10, 'height': 10}]
        mock_sct.grab.return_value = mock_sct_img

        mock_mss.mss.return_value.__enter__.return_value = mock_sct

        with patch('core.ocr.Image') as mock_image:
            fake_pil = MagicMock()
            mock_image.frombytes.return_value = fake_pil
            result = capture_screen()

        self.assertEqual(result, fake_pil)

    @patch('core.ocr.mss')
    def test_capture_screen_with_region(self, mock_mss):
        """capture_screen() passes correct monitor dict when region provided."""
        from core.ocr import capture_screen

        mock_sct_img = MagicMock()
        mock_sct_img.size = (100, 50)
        mock_sct_img.bgra = bytes([0] * (100 * 50 * 4))

        mock_sct = MagicMock()
        mock_sct.grab.return_value = mock_sct_img

        mock_mss.mss.return_value.__enter__.return_value = mock_sct

        with patch('core.ocr.Image') as mock_image:
            mock_image.frombytes.return_value = MagicMock()
            capture_screen(region=(50, 60, 100, 50))

        called_with = mock_sct.grab.call_args[0][0]
        self.assertEqual(called_with['left'], 50)
        self.assertEqual(called_with['top'], 60)
        self.assertEqual(called_with['width'], 100)
        self.assertEqual(called_with['height'], 50)

    @patch('core.ocr.mss')
    def test_capture_screen_failure_raises_ocr_error(self, mock_mss):
        """capture_screen() wraps mss exceptions into OCRError."""
        from core.ocr import capture_screen

        mock_sct = MagicMock()
        mock_sct.grab.side_effect = Exception("MSS Error")
        mock_mss.mss.return_value.__enter__.return_value = mock_sct

        with self.assertRaises(OCRError):
            capture_screen()


# ---------------------------------------------------------------------------
# TestColorFilters
# ---------------------------------------------------------------------------

class TestColorFilters(unittest.TestCase):
    """Tests for detect_blue_regions() and detect_neutral_regions()."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.ocr.config_manager')
    def test_detect_blue_regions_disabled_returns_none(self, mock_cfg):
        """detect_blue_regions() returns None when ENABLE_COLOR_FILTER is False."""
        mock_cfg.get.return_value = False
        from core.ocr import detect_blue_regions
        result = detect_blue_regions(MagicMock())
        self.assertIsNone(result)

    @patch('core.ocr.config_manager')
    @patch('core.ocr.cv2')
    def test_detect_blue_regions_success(self, mock_cv2, mock_cfg):
        """detect_blue_regions() returns a mask array on the happy path."""
        mock_cfg.get.side_effect = lambda key, default=None: {
            'ENABLE_COLOR_FILTER': True,
            'BLUE_HSV_LOWER': [100, 50, 50],
            'BLUE_HSV_UPPER': [130, 255, 255],
        }.get(key, default)

        fake_mask = np.zeros((100, 100), dtype=np.uint8)
        mock_cv2.cvtColor.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cv2.inRange.return_value = fake_mask
        mock_cv2.morphologyEx.return_value = fake_mask
        mock_cv2.MORPH_CLOSE = 3
        mock_cv2.MORPH_OPEN = 2

        mock_screenshot = MagicMock()
        # np.array(screenshot) must return a valid array
        with patch('core.ocr.np.array', return_value=np.zeros((100, 100, 3), dtype=np.uint8)):
            from core.ocr import detect_blue_regions
            result = detect_blue_regions(mock_screenshot)

        self.assertIsNotNone(result)

    @patch('core.ocr.config_manager')
    @patch('core.ocr.cv2')
    def test_detect_blue_regions_exception_raises_ocr_error(self, mock_cv2, mock_cfg):
        """detect_blue_regions() raises OCRError on cv2 failures."""
        mock_cfg.get.return_value = True
        mock_cv2.cvtColor.side_effect = Exception("CV2 Error")

        from core.ocr import detect_blue_regions
        with self.assertRaises(OCRError):
            detect_blue_regions(MagicMock())

    @patch('core.ocr.config_manager')
    def test_detect_neutral_regions_disabled_returns_none(self, mock_cfg):
        """detect_neutral_regions() returns None when ENABLE_NEUTRAL_FILTER is False."""
        mock_cfg.get.return_value = False
        from core.ocr import detect_neutral_regions
        result = detect_neutral_regions(MagicMock())
        self.assertIsNone(result)

    @patch('core.ocr.config_manager')
    @patch('core.ocr.cv2')
    def test_detect_neutral_regions_exception_returns_none(self, mock_cv2, mock_cfg):
        """detect_neutral_regions() swallows exceptions and returns None (soft fail)."""
        mock_cfg.get.return_value = True
        mock_cv2.cvtColor.side_effect = Exception("CV2 neutral error")

        from core.ocr import detect_neutral_regions
        result = detect_neutral_regions(MagicMock())
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# TestIsOnColoredBackground
# ---------------------------------------------------------------------------

class TestIsOnColoredBackground(unittest.TestCase):
    """Tests for is_on_colored_background()."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    def test_none_mask_always_true(self):
        """When no mask is provided, every box is considered 'on colored background'."""
        from core.ocr import is_on_colored_background
        self.assertTrue(is_on_colored_background((10, 10, 20, 20), None))

    def test_negative_coordinates_returns_false(self):
        """Box coordinates that fall outside the mask boundary → False."""
        from core.ocr import is_on_colored_background
        mask = np.zeros((100, 100), dtype=np.uint8)
        # box at negative offset relative to region_offset
        # mask_x = 5 - 10 = -5 → invalid
        self.assertFalse(is_on_colored_background((5, 5, 10, 10), mask, region_offset=(10, 0)))

    def test_out_of_bounds_box_returns_false(self):
        """Box that exceeds mask dimensions → False."""
        from core.ocr import is_on_colored_background
        mask = np.zeros((50, 50), dtype=np.uint8)
        # box starts at x=40, w=30 → 40+30=70 > 50
        self.assertFalse(is_on_colored_background((40, 0, 30, 20), mask))

    def test_zero_size_box_returns_false(self):
        """Zero-area box → total_pixels==0 → False."""
        from core.ocr import is_on_colored_background
        mask = np.zeros((100, 100), dtype=np.uint8)
        self.assertFalse(is_on_colored_background((10, 10, 0, 0), mask))

    def test_overlap_above_threshold_returns_true(self):
        """If enough colored pixels in ROI, returns True."""
        from core.ocr import is_on_colored_background
        # 10x10 mask, all white (colored)
        mask = np.full((100, 100), 255, dtype=np.uint8)
        # Patch config_manager to return threshold 0.5
        with patch('core.ocr.config_manager') as mock_cfg:
            mock_cfg.get.return_value = 0.5
            result = is_on_colored_background((0, 0, 10, 10), mask)
        self.assertTrue(result)

    def test_overlap_below_threshold_returns_false(self):
        """If insufficient colored pixels in ROI, returns False."""
        from core.ocr import is_on_colored_background
        # 100x100 mask, all black (no color)
        mask = np.zeros((100, 100), dtype=np.uint8)
        with patch('core.ocr.config_manager') as mock_cfg:
            mock_cfg.get.return_value = 0.5
            result = is_on_colored_background((0, 0, 10, 10), mask)
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# TestIsBoxInAppWindow
# ---------------------------------------------------------------------------

class TestIsBoxInAppWindow(unittest.TestCase):
    """Tests for is_box_in_app_window()."""

    def test_none_app_bounds_returns_false(self):
        """No app bounds means we can't restrict → False."""
        from core.ocr import is_box_in_app_window
        self.assertFalse(is_box_in_app_window((10, 10, 20, 20), None))

    def test_center_inside_window_returns_true(self):
        """Box whose center lies within app window bounds → True."""
        from core.ocr import is_box_in_app_window
        # app window: (0, 0, 100, 100); box: (20, 20, 20, 20), center=(30,30)
        self.assertTrue(is_box_in_app_window((20, 20, 20, 20), (0, 0, 100, 100)))

    def test_center_outside_window_returns_false(self):
        """Box whose center is outside app window bounds → False."""
        from core.ocr import is_box_in_app_window
        # app window: (0, 0, 50, 50); box: (80, 80, 20, 20) center=(90,90)
        self.assertFalse(is_box_in_app_window((80, 80, 20, 20), (0, 0, 50, 50)))

    def test_box_partially_overlapping_window(self):
        """Box partially overlaps window but center is outside → False."""
        from core.ocr import is_box_in_app_window
        # app: (0,0,50,50); box: (40,40,30,30) center=(55,55) → outside
        self.assertFalse(is_box_in_app_window((40, 40, 30, 30), (0, 0, 50, 50)))


# ---------------------------------------------------------------------------
# TestGetTargetRegion
# ---------------------------------------------------------------------------

class TestGetTargetRegion(unittest.TestCase):
    """Tests for get_target_region()."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.ocr.config_manager')
    def test_no_title_returns_none(self, mock_cfg):
        """When TARGET_WINDOW_TITLE is empty/falsy, returns None."""
        mock_cfg.get.return_value = ''
        from core.ocr import get_target_region
        self.assertIsNone(get_target_region())

    @patch('core.ocr.gw')
    @patch('core.ocr.config_manager')
    def test_window_not_found_returns_none(self, mock_cfg, mock_gw):
        """When no matching window is found, returns None."""
        mock_cfg.get.return_value = 'MyApp'
        mock_gw.getWindowsWithTitle.return_value = []
        from core.ocr import get_target_region
        result = get_target_region()
        self.assertIsNone(result)

    @patch('core.ocr.gw')
    @patch('core.ocr.config_manager')
    def test_exact_match_returns_bounds(self, mock_cfg, mock_gw):
        """Exact title match returns (left, top, width, height) of the window."""
        mock_cfg.get.return_value = 'MyApp'
        fake_win = MagicMock()
        fake_win.title = 'MyApp'
        fake_win.visible = True
        fake_win.left = 10
        fake_win.top = 20
        fake_win.width = 800
        fake_win.height = 600
        mock_gw.getWindowsWithTitle.return_value = [fake_win]
        from core.ocr import get_target_region
        result = get_target_region()
        self.assertEqual(result, (10, 20, 800, 600))

    @patch('core.ocr.gw')
    @patch('core.ocr.config_manager')
    def test_partial_match_fallback(self, mock_cfg, mock_gw):
        """When no exact match, falls back to partial title match."""
        mock_cfg.get.return_value = 'MyApp'
        fake_win = MagicMock()
        fake_win.title = 'MyApp - Workspace'  # Not exact, but contains 'myapp'
        fake_win.visible = True
        fake_win.left = 5
        fake_win.top = 15
        fake_win.width = 400
        fake_win.height = 300
        mock_gw.getWindowsWithTitle.return_value = [fake_win]
        from core.ocr import get_target_region
        result = get_target_region()
        self.assertEqual(result, (5, 15, 400, 300))

    @patch('core.ocr.gw')
    @patch('core.ocr.config_manager')
    def test_exception_returns_zero_tuple(self, mock_cfg, mock_gw):
        """An exception from pygetwindow returns (0, 0, 0, 0)."""
        mock_cfg.get.return_value = 'MyApp'
        mock_gw.getWindowsWithTitle.side_effect = Exception("win32 crash")
        from core.ocr import get_target_region
        result = get_target_region()
        self.assertEqual(result, (0, 0, 0, 0))


# ---------------------------------------------------------------------------
# TestProcessTextMatch
# ---------------------------------------------------------------------------

class TestProcessTextMatch(unittest.TestCase):
    """Tests for process_text_match() – the core keyword matching logic."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    def _run(self, text, click_kws=None, type_kws=None, app_bounds=None):
        """Helper to call process_text_match with common defaults."""
        from core.ocr import process_text_match
        matches = []
        process_text_match(
            text, text.lower(), 90, (10, 10, 50, 20),
            click_kws or [], type_kws or [], matches, app_bounds
        )
        return matches

    def test_exact_click_keyword_match(self):
        """Exact keyword match appends a CLICK entry."""
        matches = self._run('Accept', click_kws=['Accept'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['keyword'], 'Accept')
        self.assertEqual(matches[0]['type'], 'CLICK')

    def test_ocr_alias_substitution(self):
        """OCR alias 'expand <' is mapped to 'Expand' before matching."""
        matches = self._run('expand <', click_kws=['Expand'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['keyword'], 'Expand')

    def test_special_char_plus_match(self):
        """The '+' keyword is matched when it appears inside the text."""
        matches = self._run('3+', click_kws=['+'])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['keyword'], '+')

    def test_no_match_returns_empty_list(self):
        """Text that doesn't match any keyword returns empty matches."""
        matches = self._run('Hello World', click_kws=['Accept', 'Allow'])
        self.assertEqual(matches, [])

    def test_skip_if_in_app_window(self):
        """A box inside the app window is skipped entirely."""
        from core.ocr import process_text_match, is_box_in_app_window
        matches = []
        # box (10,10,50,20) center=(35,20); app bounds encompass it
        app_bounds = (0, 0, 100, 100)
        from core.ocr import process_text_match
        process_text_match('Accept', 'accept', 90, (10, 10, 50, 20),
                           ['Accept'], [], matches, app_bounds)
        self.assertEqual(matches, [])

    @patch('core.ocr.fuzz')
    def test_type_keyword_fuzzy_match(self, mock_fuzz):
        """TYPE keyword is matched via fuzz.ratio if > 90."""
        mock_fuzz.ratio.return_value = 95
        mock_fuzz.partial_ratio.return_value = 95
        from core.ocr import process_text_match
        matches = []
        process_text_match('procede', 'procede', 90, (0, 0, 30, 15),
                           [], ['proceed'], matches)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['type'], 'TYPE')

    @patch('core.ocr.fuzz')
    def test_click_keyword_not_matched_when_keyword_too_long(self, mock_fuzz):
        """If keyword is much longer than found text, it is skipped."""
        # 'and' in 'expand' – but 'and' keyword is > text length? No, test reversed:
        # keyword='ExpandToMatchLongKeyword' vs text='exp'
        mock_fuzz.partial_ratio.return_value = 99  # Would match if not blocked
        matches = self._run('exp', click_kws=['ExpandToMatchLongKeyword'])
        # keyword len (24) > text len (3) + 3, so should be skipped
        self.assertEqual(matches, [])


# ---------------------------------------------------------------------------
# TestProximityMatches
# ---------------------------------------------------------------------------

class TestProximityMatches(unittest.TestCase):
    """Tests for _add_proximity_matches()."""

    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.log_patcher.start()
        # Patch fuzz so partial_ratio works predictably
        self.fuzz_patcher = patch('core.ocr.fuzz', None)
        self.fuzz_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()
        self.fuzz_patcher.stop()

    def _call(self, matches, segments, anchors=None, direction='BOTH', max_dist=300):
        from core.ocr import _add_proximity_matches
        with patch('core.ocr.config_manager') as mock_cfg:
            mock_cfg.get.side_effect = lambda k, d=None: {
                'ANCHOR_KEYWORDS': anchors or ['Bell'],
                'PROXIMITY_MAX_DISTANCE': max_dist,
                'PROXIMITY_DIRECTION': direction,
            }.get(k, d)
            _add_proximity_matches(matches, segments)
        return matches

    def test_left_direction_finds_left_neighbor(self):
        """LEFT direction finds a segment to the left of the anchor."""
        # anchor 'Bell' at x=200; target at x=100 (to left, right edge at 170 < 200)
        anchor_seg = ('Bell', (200, 50, 30, 20), 90)
        target_seg = ('SomeText', (80, 52, 90, 16), 85)  # right edge=170, left of anchor center=215
        matches = []
        self._call(matches, [anchor_seg, target_seg], anchors=['Bell'], direction='LEFT')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['found_text'], 'SomeText')
        self.assertEqual(matches[0]['type'], 'CLICK')

    def test_right_direction_finds_right_neighbor(self):
        """RIGHT direction finds a segment to the right of the anchor."""
        anchor_seg = ('Bell', (50, 50, 30, 20), 90)
        target_seg = ('RightText', (200, 52, 60, 16), 85)  # to the right
        matches = []
        self._call(matches, [anchor_seg, target_seg], anchors=['Bell'], direction='RIGHT')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['found_text'], 'RightText')

    def test_both_direction_finds_both_sides(self):
        """BOTH direction finds segments on both sides of the anchor."""
        anchor_seg = ('Bell', (200, 50, 30, 20), 90)
        left_seg = ('LeftText', (80, 52, 90, 16), 85)
        right_seg = ('RightText', (260, 52, 60, 16), 85)
        matches = []
        self._call(matches, [anchor_seg, left_seg, right_seg], anchors=['Bell'], direction='BOTH')
        texts = {m['found_text'] for m in matches}
        self.assertIn('LeftText', texts)
        self.assertIn('RightText', texts)

    def test_duplicate_suppression(self):
        """Same box+keyword pair is only added once to matches."""
        anchor_seg = ('Bell', (200, 50, 30, 20), 90)
        target_seg = ('SomeText', (80, 52, 90, 16), 85)
        # Pre-populate match with the same box and keyword
        pre_existing = {'keyword': 'Proximity(Bell)', 'box': (80, 52, 90, 16), 'type': 'CLICK', 'found_text': 'SomeText', 'conf': 85}
        matches = [pre_existing]
        self._call(matches, [anchor_seg, target_seg], anchors=['Bell'], direction='LEFT')
        # Should still only have 1 entry
        self.assertEqual(len(matches), 1)

    def test_different_row_segment_is_skipped(self):
        """Segment on a very different Y row is excluded by vertical overlap check."""
        anchor_seg = ('Bell', (200, 50, 30, 20), 90)
        # y_diff = |60 - 600| = 540 >> (ah + th) = 20+20=40
        far_seg = ('FarAway', (80, 590, 90, 20), 85)
        matches = []
        self._call(matches, [anchor_seg, far_seg], anchors=['Bell'], direction='BOTH')
        self.assertEqual(matches, [])

    def test_max_distance_filter(self):
        """Segment beyond max_dist is excluded."""
        anchor_seg = ('Bell', (200, 50, 30, 20), 90)
        # distance from anchor right edge (230) to target left (600) = 370 > max_dist=50
        far_seg = ('FarText', (600, 52, 60, 16), 85)
        matches = []
        self._call(matches, [anchor_seg, far_seg], anchors=['Bell'], direction='RIGHT', max_dist=50)
        self.assertEqual(matches, [])


# ---------------------------------------------------------------------------
# TestOCRAliases
# ---------------------------------------------------------------------------

class TestOCRAliases(unittest.TestCase):
    """Validates that the OCR_ALIASES dict contains all expected corrections."""

    def test_expand_variant_aliases(self):
        """Expand misread variants are all mapped to 'Expand'."""
        from core.ocr import OCR_ALIASES
        for key in ('expand <', 'expand<', 'expand (', 'expand [', 'expand{'):
            with self.subTest(key=key):
                self.assertEqual(OCR_ALIASES[key], 'Expand')

    def test_common_aliases_exist(self):
        """Core OCR fixes for 'Confirm', 'Allow', 'Accept' exist."""
        from core.ocr import OCR_ALIASES
        self.assertIn('conten', OCR_ALIASES)
        self.assertEqual(OCR_ALIASES['conten'], 'Confirm')
        self.assertIn('alow', OCR_ALIASES)
        self.assertEqual(OCR_ALIASES['alow'], 'Allow')
        self.assertIn('acce', OCR_ALIASES)
        self.assertEqual(OCR_ALIASES['acce'], 'Accept')


if __name__ == '__main__':
    unittest.main()
