import unittest
from core.actions import apply_random_offset

class TestClickTargeting(unittest.TestCase):
    def test_apply_random_offset_bounds(self):
        # Test a 100x100 box at (10, 10). Center is 60, 60.
        # Max offset is 5% of 100 = 5. Loop 100 times.
        x, y, w, h = 10, 10, 100, 100
        center_x, center_y = x + w/2, y + h/2
        max_offset_x = w * 0.05
        max_offset_y = h * 0.05
        
        for _ in range(100):
            tx, ty = apply_random_offset(x, y, w, h)
            self.assertTrue(center_x - max_offset_x <= tx <= center_x + max_offset_x)
            self.assertTrue(center_y - max_offset_y <= ty <= center_y + max_offset_y)

    def test_apply_random_offset_small_box(self):
        # A 10x10 box at (0, 0). Center is 5, 5. Max offset = max(1, 10*0.05) = 1.
        x, y, w, h = 0, 0, 10, 10
        center_x, center_y = 5, 5
        max_offset_x = 1
        max_offset_y = 1
        
        for _ in range(100):
            tx, ty = apply_random_offset(x, y, w, h)
            self.assertTrue(center_x - max_offset_x <= tx <= center_x + max_offset_x)
            self.assertTrue(center_y - max_offset_y <= ty <= center_y + max_offset_y)

if __name__ == '__main__':
    unittest.main()
