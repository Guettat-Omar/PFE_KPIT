LIGHT_BUTTONS = {
        "left_btn"        : (2, 4),
        "right_btn"       : (2, 3),
        "hazard_btn"      : (3, 4),
        "low_beam_sw"     : (2, 6),
        "ftp_not_pressed" : (3, 6),  # normally 1, goes 0 when FTP stalk pulled
        "high_beam_sw"    : (3, 7),
        "brake_sw"        : (1, 6),
        "reverse_sw"      : (3, 5),
        "front_fog_sw"    : (2, 2),
        "rear_fog_sw"     : (2, 1),
        "parking_sw"      : (2, 5),
        "pwf_bit0"        : (4, 4),
        "pwf_bit1"        : (4, 5),
        "door_fl_btn"     : (3, 1),
        "door_fr_btn"     : (3, 0),
        "door_rl_btn"     : (4, 6),
        "door_rr_btn"     : (4, 7),
}
LIGHT_LEDS = {
    "trun_left" : ["Led_B0_0","Led_B1_2","Led_B1_3","Led_B1_4"],
    "trun_right" : ["Led_B0_0","Led_B3_4","Led_B3_5","Led_B3_6"],
    "low_beam" : ["Led_B1_1","Led_B3_7"],
    "high_beam" : ["Led_B0_7","Led_B4_6"],
    "front_fog" : ["Led_B0_3","Led_B2_1"],
    "rear_fog" : ["Led_B4_4","Led_B2_7"],
    "parking" : ["Led_B0_5","Led_B1_0","Led_B2_0","Led_B0_1"],
    "brake" : ["Led_B0_6","Led_B4_0","Led_B4_5"],
    "reverse" : ["Led_B3_1","Led_B1_7"],
    "drl" : ["Led_B2_0","Led_B4_7"],
    # Door status LEDs: green = door open, red = door closed
    # Physical HC595 positions after [::-1] reversal: B2_x → phys byte 4, B3_x → phys byte 3
    "door_fl_green": ["Led_B2_2"],
    "door_fl_red":   ["Led_B2_3"],
    "door_fr_green": ["Led_B2_4"],
    "door_fr_red":   ["Led_B2_5"],
    "door_rl_green": ["Led_B2_6"],
    "door_rl_red":   ["Led_B3_0"],
    "door_rr_green": ["Led_B3_2"],
    "door_rr_red":   ["Led_B3_3"],
    }

def get_button_state(lin_data: bytes, button_name: str) -> bool:
    byte_index, bit_index = LIGHT_BUTTONS[button_name]
    return bool((lin_data[byte_index] >> bit_index) & 1)