LIGHT_BUTTONS = {
        "left_btn"        : (4, 4),
        "right_btn"       : (4, 5),
        "hazard_btn"      : (0, 0),
        "low_beam_sw"     : (4, 6),  # additive rotary: also set at fog positions
        "ftp_not_pressed" : (4, 0),  # normally 1, goes 0 when FTP stalk pulled
        "high_beam_sw"    : (3, 7),
        "brake_sw"        : (4, 1),
        "reverse_sw"      : (1, 4),
        "front_fog_sw"    : (4, 3),  # additive rotary: also set at rear fog
        "rear_fog_sw"     : (4, 2),
        "parking_sw"      : (4, 7),  # additive rotary: also set at low beam and fog
        "pwf_bit0"        : (1, 6),
        "pwf_bit1"        : (1, 5),
        "door_fl_btn"     : (1, 3),
        "door_fr_btn"     : (1, 1),
        "door_rl_btn"     : (1, 2),
        "door_rr_btn"     : (1, 0),
}
LIGHT_LEDS = {
    "trun_left"  : ["Led_B2_6", "Led_B1_6", "Led_B0_7", "Led_B0_0"],
    "trun_right" : ["Led_B4_5", "Led_B3_5", "Led_B4_0", "Led_B0_0"],
    "low_beam"   : ["Led_B4_4", "Led_B1_5"],
    "high_beam"  : ["Led_B4_1", "Led_B1_7"],
    "front_fog"  : ["Led_B4_2", "Led_B0_5"],
    "rear_fog"   : ["Led_B2_5", "Led_B1_0"],
    "parking"    : ["Led_B4_3", "Led_B3_0"],
    "brake"      : ["Led_B3_1", "Led_B3_3", "Led_B0_6"],
    "reverse"    : ["Led_B3_2", "Led_B2_7"],
    "drl"        : [],
    # Door status LEDs — IC3 (DBC byte 2) and IC2 (DBC byte 3)
    "door_fl_green": ["Led_B3_7"],
    "door_fl_red":   ["Led_B2_0"],
    "door_fr_green": ["Led_B2_2"],
    "door_fr_red":   ["Led_B3_4"],
    "door_rl_green": ["Led_B3_6"],
    "door_rl_red":   ["Led_B2_1"],
    "door_rr_green": ["Led_B2_3"],
    "door_rr_red":   ["Led_B2_4"],
    # PWF state LEDs — IC5 (DBC byte 0) and IC4 (DBC byte 1)
    "pwf_parken" : ["Led_B0_4"],
    "pwf_wohnen" : ["Led_B1_3"],
    "pwf_fahren" : ["Led_B1_4"],
    }

def get_button_state(lin_data: bytes, button_name: str) -> bool:
    byte_index, bit_index = LIGHT_BUTTONS[button_name]
    return bool((lin_data[byte_index] >> bit_index) & 1)