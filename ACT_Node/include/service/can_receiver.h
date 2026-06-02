#pragma once
#include <stdint.h>
#include <stdbool.h>

bool can_receiver_poll(uint32_t* out_id, uint8_t* out_data, uint8_t* out_len);