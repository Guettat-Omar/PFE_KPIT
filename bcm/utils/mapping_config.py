LIGHT_BUTTONS = { 
        "left_btn": (3,6), 
        "right_btn":(3,5), 
        "hazard_btn": (4,3),
        "low_beam_sw"  : (2,3), # byte 2, bit 3
        "ftp_not_pressed" : (2,6),
        "high_beam_sw" : (2,2),  # byte 4, bit 2 (momentary, raw)
        "brake_sw"     : (1,6), # Used to be byte 3 bit 5, moved it away to let rear fog use it
        "reverse_sw"   : (1,1),
        "front_fog_sw" : (3,7),  # fog ring engaged
        "rear_fog_sw"  : (2,0),
        "parking_sw"   : (2,4),
        "pwf_bit0" : (4,4),
        "pwf_bit1" : (4,5)
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
    "drl" : ["Led_B2_0","Led_B4_7"]
    }

def get_button_state(lin_data: bytes, button_name: str) -> bool:
    byte_index, bit_index = LIGHT_BUTTONS[button_name]
    return bool((lin_data[byte_index] >> bit_index) & 1)