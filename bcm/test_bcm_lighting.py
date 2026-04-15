import unittest
import sys
import os

# Ensure the app module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))

from headlight_sm import headlightSM

class TestHeadlightStateMachine(unittest.TestCase):
    def setUp(self):
        """Creates a fresh instance of the State Machine before every test."""
        self.sm = headlightSM()

    def test_req_park_001_and_002(self):
        """Test Parking Lights Logic: Should turn ON when parking is True OR low_beam is True."""
        # Stalk Position 1 (Parking)
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=True, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        self.assertTrue(self.sm.parking_active)

        # Stalk Position 2 (Low Beam)
        self.sm.update(low_beam_on=True, high_beam_on=False, parking_on=False, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        self.assertTrue(self.sm.parking_active)

        # Stalk OFF
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=False, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        self.assertFalse(self.sm.parking_active)

    def test_req_low_001_and_req_high_edge_detection(self):
        """Test Low Beam prerequisite and High Beam Toggle (Edge Detection)."""
        # 1. Turn on Low Beams
        self.sm.update(low_beam_on=True, high_beam_on=False, parking_on=True, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        self.assertTrue(self.sm.low_beam_active)

        # 2. Press High Beam button (Edge: False -> True)
        self.sm.update(low_beam_on=True, high_beam_on=True, parking_on=True, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        outs = self.sm.get_light_cmd_bits(ftp_on=False)
        self.assertEqual(outs["HighBeamLed"], 1)

        # 3. Release High Beam button (No Toggle should happen)
        self.sm.update(low_beam_on=True, high_beam_on=False, parking_on=True, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        outs = self.sm.get_light_cmd_bits(ftp_on=False)
        self.assertEqual(outs["HighBeamLed"], 1) # Should remain ON

        # 4. Turn OFF Low Beam (High Beam must auto-drop)
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=False, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        outs = self.sm.get_light_cmd_bits(ftp_on=False)
        self.assertEqual(outs["HighBeamLed"], 0)
        self.assertEqual(outs["LowBeamLed"], 0)

    def test_req_fog_dependent_on_parking(self):
        """Test Fog lights only work if Parking lights are ON."""
        # Try turning on Fog without parking
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=False, front_fog_on=True, rear_fog_on=False, ftp_on=False)
        self.assertFalse(self.sm.front_fog_active)

        # Turn on Parking + Fog
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=True, front_fog_on=True, rear_fog_on=False, ftp_on=False)
        self.assertTrue(self.sm.front_fog_active)

    def test_ftp_override(self):
        """Test Flash-To-Pass overrides High Beam even when everything is OFF."""
        # Everything OFF
        self.sm.update(low_beam_on=False, high_beam_on=False, parking_on=False, front_fog_on=False, rear_fog_on=False, ftp_on=False)
        
        # FTP pressed
        outs = self.sm.get_light_cmd_bits(ftp_on=True)
        self.assertEqual(outs["HighBeamLed"], 1)
        
        # FTP released
        outs = self.sm.get_light_cmd_bits(ftp_on=False)
        self.assertEqual(outs["HighBeamLed"], 0)

if __name__ == '__main__':
    unittest.main(verbosity=2)