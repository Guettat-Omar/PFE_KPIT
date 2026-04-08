import unittest
from drivers.hc595_driver import write_all_chips
from hal.gpio_hal import init_gpio, cleanup_gpio
import time

class TestHC595Driver(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """This runs ONCE before the tests start. We must initialize the real Pins!"""
        print("Setting up physical Raspberry Pi GPIOs for Hardware Testing...")
        init_gpio()

    @classmethod
    def tearDownClass(cls):
        """This runs ONCE after all tests finish. Clean up the pins safely."""
        print("Cleaning up GPIOs...")
        cleanup_gpio()

    def test_write_valid_data(self):
        """Test that sending normal, valid bytes works perfectly and flashes LEDs."""
        # Arrange: 5 valid bytes (Alternating pattern 10101010 = 0xAA)
        valid_payload = [0xAA, 0xAA, 0xAA, 0xAA, 0xAA]
        
        # Act & Assert
        try:
            write_all_chips(valid_payload)
            # Sleep for 1 second so you can actually see the LEDs light up!
            time.sleep(1) 
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"write_all_chips crashed unexpectedly with valid data: {e}")

    def test_write_invalid_type(self):
        """Test that sending a string instead of bytes is blocked."""
        invalid_payload = "11110000"
        with self.assertRaises(TypeError):
            write_all_chips(invalid_payload)

    def test_write_out_of_bounds_byte(self):
        """Test that sending a number larger than 255 is blocked."""
        invalid_payload = [0x00, 256, 0x10, 0x00, 0x00]
        with self.assertRaises(ValueError):
            write_all_chips(invalid_payload)

if __name__ == '__main__':
    unittest.main()