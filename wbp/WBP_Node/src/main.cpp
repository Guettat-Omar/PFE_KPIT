#include "window_switch.h"
#include "lin_slave.h"

// ── External variables from lin_slave.cpp ────────────────────
extern volatile uint8_t window_states[5];

volatile bool break_received_flag = false;
volatile bool response_sent_flag = false;

// ── Pin definitions ──────────────────────────────────────────
#define LED_BREAK      4
#define LED_SYNC       5
#define LED_RESPONSE   6
#define BTN_CHILD_SAFETY A4
#define BTN_DOOR_LOCK    A5

// ── Door lock ADC thresholds ─────────────────────────────────
#define DOOR_UNLOCK_MAX  35
#define DOOR_LOCK_MIN    35
#define DOOR_LOCK_MAX    200
#define CHILD_PRESSED_MAX 200

// ── Door lock states ─────────────────────────────────────────
#define DOOR_IDLE    0
#define DOOR_LOCK    1
#define DOOR_UNLOCK  2

// ── ADC pins ─────────────────────────────────────────────────
const uint8_t ADC_PINS[4] = {A0, A1, A2, A3};
windowState pending_state[4] = {windowState::WINDOW_OFF};
uint8_t debounce_count[4] = {0};
const uint8_t DEBOUNCE_THRESHOLD = 150;

// ── Door lock debounce ───────────────────────────────────────
uint8_t door_pending_state   = DOOR_IDLE;
uint8_t door_stable_state    = DOOR_IDLE;
uint8_t door_debounce_count  = 0;
uint8_t door_last_sent       = DOOR_IDLE; // track last sent state

// ── Child safety debounce ────────────────────────────────────
uint8_t child_debounce_count = 0;
bool    child_stable         = false;
bool    child_pending        = false;

// ── Timers ───────────────────────────────────────────────────
unsigned long last_sample_time = 0;

// ── Helpers ──────────────────────────────────────────────────
void all_leds(bool on) {
    digitalWrite(LED_BREAK,    on);
    digitalWrite(LED_SYNC,     on);
    digitalWrite(LED_RESPONSE, on);
}

void reset_leds() {
    digitalWrite(LED_BREAK,    LOW);
    digitalWrite(LED_SYNC,     LOW);
    digitalWrite(LED_RESPONSE, LOW);
}

// ── Startup pattern ──────────────────────────────────────────
void startup_sequence() {
    all_leds(true);  delay(1000); all_leds(false); delay(200);
    for (int r = 0; r < 3; r++) {
        digitalWrite(LED_BREAK, HIGH); delay(150); digitalWrite(LED_BREAK, LOW);
        digitalWrite(LED_SYNC,  HIGH); delay(150); digitalWrite(LED_SYNC,  LOW);
        digitalWrite(LED_RESPONSE, HIGH); delay(150); digitalWrite(LED_RESPONSE, LOW);
        delay(100);
    }
    for (int r = 0; r < 3; r++) {
        digitalWrite(LED_RESPONSE, HIGH); delay(150); digitalWrite(LED_RESPONSE, LOW);
        digitalWrite(LED_SYNC,     HIGH); delay(150); digitalWrite(LED_SYNC,     LOW);
        digitalWrite(LED_BREAK,    HIGH); delay(150); digitalWrite(LED_BREAK,    LOW);
        delay(100);
    }
    for (int i = 0; i < 5; i++) { all_leds(true); delay(80); all_leds(false); delay(80); }
    delay(200);
    digitalWrite(LED_BREAK,    HIGH); delay(300);
    digitalWrite(LED_SYNC,     HIGH); delay(300);
    digitalWrite(LED_RESPONSE, HIGH); delay(300);
    delay(400); all_leds(false); delay(300);
    all_leds(true); delay(500); all_leds(false); delay(500);
}

// ── Setup ────────────────────────────────────────────────────
void setup() {
    pinMode(LED_BREAK,    OUTPUT);
    pinMode(LED_SYNC,     OUTPUT);
    pinMode(LED_RESPONSE, OUTPUT);
    pinMode(BTN_CHILD_SAFETY, INPUT_PULLUP);
    pinMode(13, OUTPUT);
    reset_leds();
    startup_sequence();
    lin_slave_init();
}

// ── Loop ─────────────────────────────────────────────────────
void loop() {
    static unsigned long ready_at = millis() + 1000;
    if (millis() < ready_at) return;

    unsigned long now = millis();
    if (now - last_sample_time >= 1) {
        last_sample_time = now;

        // ── Door lock — ADC read on A5 ───────────────────────
        int door_adc = analogRead(BTN_DOOR_LOCK);
        uint8_t raw_door_state;
        if (door_adc < DOOR_UNLOCK_MAX) {
            raw_door_state = DOOR_UNLOCK;
        } else if (door_adc >= DOOR_LOCK_MIN && door_adc <= DOOR_LOCK_MAX) {
            raw_door_state = DOOR_LOCK;
        } else {
            raw_door_state = DOOR_IDLE;
        }

        // Debounce door lock
        if (raw_door_state == door_pending_state) {
            door_debounce_count++;
            if (door_debounce_count >= DEBOUNCE_THRESHOLD) {
                door_stable_state    = raw_door_state;
                door_debounce_count  = DEBOUNCE_THRESHOLD; // clamp
            }
        } else {
            door_pending_state  = raw_door_state;
            door_debounce_count = 0;
        }

        // Encode door lock into byte 4:
        // bit 0 = LOCK active (1 when in LOCK position)
        // bit 1 = UNLOCK active (1 when in UNLOCK position)
        // bit 2 = child safety
        uint8_t door_lock_bit   = (door_stable_state == DOOR_LOCK)   ? 1 : 0;
        uint8_t door_unlock_bit = (door_stable_state == DOOR_UNLOCK) ? 1 : 0;

        // ── Child safety — digital read on A4 ───────────────
        int child_adc = (door_stable_state == DOOR_IDLE) ? analogRead(BTN_CHILD_SAFETY) : 1023;
        bool raw_child = (child_adc < CHILD_PRESSED_MAX);
        if (raw_child == child_pending) {
            child_debounce_count++;
            if (child_debounce_count >= DEBOUNCE_THRESHOLD) {
                child_stable         = raw_child;
                child_debounce_count = DEBOUNCE_THRESHOLD;
            }
        } else {
            child_pending        = raw_child;
            child_debounce_count = 0;
        }

        // ── Pack byte 4 ──────────────────────────────────────
        // bit 0 = door LOCK
        // bit 1 = door UNLOCK
        // bit 2 = child safety
        window_states[4] = (door_lock_bit)
                         | (door_unlock_bit << 1)
                         | ((uint8_t)child_stable << 7);
        // ── Window ADC — only when door is IDLE ─────────────
        if (door_stable_state == DOOR_IDLE && !child_stable) {
            for (int i = 0; i < 4; i++) {
                uint16_t adc_val;
                analogRead(ADC_PINS[i]);
                analogRead(ADC_PINS[i]);
                adc_val = analogRead(ADC_PINS[i]);
                windowState new_state = window_switch(adc_val);  
                if (new_state == pending_state[i]) {
                    debounce_count[i]++;
                    if (debounce_count[i] >= DEBOUNCE_THRESHOLD) {
                        window_states[i] = static_cast<uint8_t>(new_state);
                    }
                } else {
                    pending_state[i] = new_state;
                    debounce_count[i] = 1;
                }
            }
        }

        // ── LED feedback ─────────────────────────────────────
        if (break_received_flag) {
            break_received_flag = false;
            digitalWrite(LED_BREAK,    HIGH);
            digitalWrite(LED_SYNC,     LOW);
            digitalWrite(LED_RESPONSE, LOW);
        }
        if (response_sent_flag) {
            response_sent_flag = false;
            digitalWrite(LED_RESPONSE, HIGH);
        }
    }

    // Debug LED 13
    bool any_active = false;
    for (int i = 0; i < 4; i++) {
        if (window_states[i] != 0) any_active = true;
    }
    digitalWrite(13, any_active ? HIGH : LOW);
}