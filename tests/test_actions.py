
import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.actions import perform_click, perform_type, perform_shortcut, smooth_move, apply_random_offset
from core.exceptions import ActionError


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
        """Works correctly with a 1x1 box (degenerate case, range collapses)."""
        # With w=1, h=1: int(1*0.1)=0, int(1*0.9)=0. randint(0,0)=0 always
        tx, ty = apply_random_offset(50, 50, 1, 1)
        self.assertEqual(tx, 50)
        self.assertEqual(ty, 50)


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


if __name__ == '__main__':
    unittest.main()
