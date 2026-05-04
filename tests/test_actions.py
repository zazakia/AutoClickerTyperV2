
import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.actions import perform_click, perform_type, perform_shortcut, smooth_move, apply_random_offset, get_target_window, perform_scroll, scroll_all_scrollbars
from core.exceptions import ActionError


class TestGetTargetWindow(unittest.TestCase):
    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.config_manager')
    @patch('pygetwindow.getAllWindows')
    def test_get_target_window_regex_found(self, mock_getAll, mock_cm):
        mock_cm.get.side_effect = lambda k, d="": "TestApp.*" if k == "TARGET_WINDOW_REGEX" else ""
        mock_win = MagicMock()
        mock_win.title = "TestApp123"
        mock_getAll.return_value = [mock_win]
        
        win = get_target_window()
        self.assertEqual(win, mock_win)

    @patch('core.actions.config_manager')
    @patch('pygetwindow.getAllWindows')
    def test_get_target_window_exception(self, mock_getAll, mock_cm):
        mock_cm.get.side_effect = lambda k, d="": "TestApp.*" if k == "TARGET_WINDOW_REGEX" else ""
        mock_getAll.side_effect = Exception("GW Error")
        win = get_target_window()
        self.assertIsNone(win)
        self.mock_logger.error.assert_called()

class TestSmoothMove(unittest.TestCase):
    """Tests for smooth_move()."""

    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.pyautogui')
    def test_smooth_move_success(self, mock_pyautogui):
        """smooth_move() calls pyautogui.moveTo with the correct coordinates."""
        smooth_move(200, 300)
        mock_pyautogui.moveTo.assert_called_once()
        args, kwargs = mock_pyautogui.moveTo.call_args
        self.assertEqual(args[0], 200)
        self.assertEqual(args[1], 300)
        self.assertIn('duration', kwargs)

    @patch('core.actions.pyautogui')
    def test_smooth_move_raises_action_error_on_exception(self, mock_pyautogui):
        """smooth_move() wraps pyautogui exceptions into ActionError."""
        mock_pyautogui.moveTo.side_effect = Exception("FailSafe triggered")
        with self.assertRaises(ActionError):
            smooth_move(0, 0)


class TestApplyRandomOffset(unittest.TestCase):
    """Tests for apply_random_offset()."""

    def test_offset_stays_within_central_bounds(self):
        """Returned coordinates are within the central 80% of the bounding box."""
        x, y, w, h = 100, 200, 60, 40
        for _ in range(50):  # Run many times to test randomness
            tx, ty = apply_random_offset(x, y, w, h)
            # Expect x + (0.1*w) <= tx <= x + (0.9*w)
            self.assertGreaterEqual(tx, x + int(w * 0.1))
            self.assertLessEqual(tx, x + int(w * 0.9))
            self.assertGreaterEqual(ty, y + int(h * 0.1))
            self.assertLessEqual(ty, y + int(h * 0.9))

    def test_offset_with_minimal_box(self):
        """Works correctly with a 1x1 box (degenerate case, offset can be slightly out)."""
        tx, ty = apply_random_offset(50, 50, 1, 1)
        self.assertIn(tx, [49, 50, 51])
        self.assertIn(ty, [49, 50, 51])


class TestPerformClick(unittest.TestCase):
    """Tests for perform_click()."""

    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_basic(self, mock_time, mock_pyautogui):
        """perform_click() moves to target and performs click within valid bounds."""
        box = (100, 100, 50, 50)
        target_x, target_y = perform_click(box)
        self.assertTrue(105 <= target_x <= 145)
        self.assertTrue(105 <= target_y <= 145)
        mock_pyautogui.moveTo.assert_called()
        mock_pyautogui.click.assert_called_once()
        self.assertTrue(mock_time.sleep.call_count >= 2)

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_failure_raises_action_error(self, mock_time, mock_pyautogui):
        """A PyAutoGUI error during moveTo raises ActionError."""
        mock_pyautogui.moveTo.side_effect = Exception("FailSafeTriggered")
        with self.assertRaises(ActionError):
            perform_click((0, 0, 10, 10))

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_moverel_called(self, mock_time, mock_pyautogui):
        """perform_click() calls moveRel to move mouse away after clicking."""
        perform_click((100, 100, 50, 50))
        mock_pyautogui.moveRel.assert_called_once()

    @patch('core.actions.get_target_window')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_activates_window(self, mock_time, mock_pyautogui, mock_get_win):
        mock_win = MagicMock()
        mock_win.isActive = False
        mock_win.title = "Target"
        mock_get_win.return_value = mock_win
        perform_click((10, 10, 10, 10))
        mock_win.activate.assert_called_once()

    @patch('core.actions.get_target_window')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_activate_window_exception(self, mock_time, mock_pyautogui, mock_get_win):
        mock_win = MagicMock()
        mock_win.isActive = False
        mock_win.activate.side_effect = Exception("Activate error")
        mock_get_win.return_value = mock_win
        perform_click((10, 10, 10, 10))
        self.assertTrue(self.mock_logger.debug.called)

    @patch('core.actions.get_target_window', return_value=None)
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_types(self, mock_time, mock_pyautogui, mock_get_win):
        perform_click((10, 10, 10, 10), click_type="double")
        mock_pyautogui.doubleClick.assert_called_once()
        perform_click((10, 10, 10, 10), click_type="right")
        mock_pyautogui.rightClick.assert_called_once()

    @patch('core.actions.get_target_window', return_value=None)
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_pixel_verify(self, mock_time, mock_pyautogui, mock_get_win):
        mock_pyautogui.pixel.side_effect = [(255, 255, 255), (0, 0, 0)]
        perform_click((10, 10, 10, 10))
        # Verify pixel was checked twice
        self.assertEqual(mock_pyautogui.pixel.call_count, 2)

    @patch('core.actions.get_target_window', return_value=None)
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_pixel_verify_exception(self, mock_time, mock_pyautogui, mock_get_win):
        mock_pyautogui.pixel.side_effect = Exception("Pixel read error")
        # Should catch and pass
        perform_click((10, 10, 10, 10))

    @patch('core.actions.get_target_window', return_value=None)
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_general_exception(self, mock_time, mock_pyautogui, mock_get_win):
        mock_pyautogui.click.side_effect = Exception("Random error")
        with self.assertRaises(ActionError):
            perform_click((10, 10, 10, 10))


class TestPerformType(unittest.TestCase):
    """Tests for perform_type()."""

    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.perform_click')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_type_success(self, mock_time, mock_pyautogui, mock_perform_click):
        """perform_type() clicks box, types keyword, presses enter, returns True."""
        box = (10, 10, 10, 10)
        keyword = "test input"
        result = perform_type(keyword, box)
        self.assertTrue(result)
        mock_perform_click.assert_called_with(box)
        mock_pyautogui.write.assert_called_with(keyword, interval=unittest.mock.ANY)
        mock_pyautogui.press.assert_called_with('enter')

    @patch('core.actions.perform_click')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_type_write_failure_raises_action_error(self, mock_time, mock_pyautogui, mock_perform_click):
        """When pyautogui.write raises, perform_type() wraps it in ActionError."""
        mock_pyautogui.write.side_effect = Exception("Typing error")
        with self.assertRaises(ActionError):
            perform_type("hello", (10, 10, 10, 10))

    @patch('core.actions.perform_click')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_type_propagates_action_error_from_click(self, mock_time, mock_pyautogui, mock_perform_click):
        """ActionError from perform_click() is re-raised unchanged."""
        mock_perform_click.side_effect = ActionError("click failed")
        with self.assertRaises(ActionError):
            perform_type("text", (0, 0, 10, 10))


class TestPerformShortcut(unittest.TestCase):
    """Tests for perform_shortcut()."""

    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.pyautogui')
    def test_perform_shortcut_success(self, mock_pyautogui):
        """perform_shortcut() calls hotkey with unpacked keys and returns True."""
        keys = ['ctrl', 'c']
        result = perform_shortcut(keys)
        self.assertTrue(result)
        mock_pyautogui.hotkey.assert_called_with('ctrl', 'c')

    @patch('core.actions.pyautogui')
    def test_perform_shortcut_failure_raises_action_error(self, mock_pyautogui):
        """A keyboard error during hotkey() raises ActionError."""
        mock_pyautogui.hotkey.side_effect = Exception("Keyboard error")
        with self.assertRaises(ActionError):
            perform_shortcut(['ctrl', 'v'])

    @patch('core.actions.pyautogui')
    def test_perform_shortcut_multi_key(self, mock_pyautogui):
        """perform_shortcut() works with 3-key combos."""
        result = perform_shortcut(['ctrl', 'shift', 'esc'])
        self.assertTrue(result)
        mock_pyautogui.hotkey.assert_called_with('ctrl', 'shift', 'esc')

class TestScrollActions(unittest.TestCase):
    def setUp(self):
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_scroll_success(self, mock_time, mock_pyautogui):
        result = perform_scroll((100, 100, 50, 50), -300)
        self.assertTrue(result)
        mock_pyautogui.moveTo.assert_called()
        mock_pyautogui.scroll.assert_called_with(-300)

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_scroll_exception(self, mock_time, mock_pyautogui):
        mock_pyautogui.moveTo.side_effect = Exception("Scroll Error")
        result = perform_scroll((100, 100, 50, 50))
        self.assertFalse(result)

    @patch('core.actions.detect_scrollbars')
    @patch('core.actions.perform_scroll')
    def test_scroll_all_scrollbars_success(self, mock_perform_scroll, mock_detect):
        mock_detect.return_value = [(10, 10, 10, 10), (20, 20, 10, 10)]
        mock_perform_scroll.return_value = True
        result = scroll_all_scrollbars()
        self.assertTrue(result)
        self.assertEqual(mock_perform_scroll.call_count, 2)

    @patch('core.actions.detect_scrollbars')
    def test_scroll_all_scrollbars_none(self, mock_detect):
        mock_detect.return_value = []
        result = scroll_all_scrollbars()
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
