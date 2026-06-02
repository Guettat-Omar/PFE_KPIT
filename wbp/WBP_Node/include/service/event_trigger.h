#pragma once
#include <stdbool.h>
#include <stdint.h>

bool event_trigger_has_changed(const uint8_t* current, const uint8_t* last, uint8_t len);
void event_trigger_update_last(const uint8_t* current, uint8_t* last, uint8_t len);