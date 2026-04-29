#include "window_swich.h"
#include "lin_slave.h"

// ── External variables from lin_slave.cpp ────────────────────
extern volatile uint8_t window_states[4];
// ← ADD THESE TWO LINES at the top of main.cpp
volatile bool break_received_flag = false;
volatile bool response_sent_flag  = false;

// ── Pin definitions ──────────────────────────────────────────
#define LED_BREAK    4    // RED    — BREAK received
#define LED_SYNC     5    // YELLOW — SYNC received
#define LED_RESPONSE 6    // GREEN  — response sent

// ── ADC pins ─────────────────────────────────────────────────
const uint8_t ADC_PINS[4] = {A0, A1, A2, A3};

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
    // Phase 1 — all ON together 1 second
    all_leds(true);
    delay(1000);
    all_leds(false);
    delay(200);

    // Phase 2 — chase RED → YELLOW → GREEN × 3
    for (int r = 0; r < 3; r++) {
        digitalWrite(LED_BREAK,    HIGH); delay(150);
        digitalWrite(LED_BREAK,    LOW);
        digitalWrite(LED_SYNC,     HIGH); delay(150);
        digitalWrite(LED_SYNC,     LOW);
        digitalWrite(LED_RESPONSE, HIGH); delay(150);
        digitalWrite(LED_RESPONSE, LOW);
        delay(100);
    }

    // Phase 3 — chase GREEN → YELLOW → RED × 3
    for (int r = 0; r < 3; r++) {
        digitalWrite(LED_RESPONSE, HIGH); delay(150);
        digitalWrite(LED_RESPONSE, LOW);
        digitalWrite(LED_SYNC,     HIGH); delay(150);
        digitalWrite(LED_SYNC,     LOW);
        digitalWrite(LED_BREAK,    HIGH); delay(150);
        digitalWrite(LED_BREAK,    LOW);
        delay(100);
    }

    // Phase 4 — all fast blink × 5
    for (int i = 0; i < 5; i++) {
        all_leds(true);  delay(80);
        all_leds(false); delay(80);
    }

    // Phase 5 — light one by one and stay ON
    delay(200);
    digitalWrite(LED_BREAK,    HIGH); delay(300);
    digitalWrite(LED_SYNC,     HIGH); delay(300);
    digitalWrite(LED_RESPONSE, HIGH); delay(300);

    // Phase 6 — all OFF = READY
    delay(400);
    all_leds(false);
    delay(300);

    // Phase 7 — single slow blink = listening
    all_leds(true);  delay(500);
    all_leds(false); delay(500);
}

// ── Setup ────────────────────────────────────────────────────
void setup() {
    pinMode(LED_BREAK,    OUTPUT);
    pinMode(LED_SYNC,     OUTPUT);
    pinMode(LED_RESPONSE, OUTPUT);
    reset_leds();

    startup_sequence();

    lin_slave_init();
}

// ── Loop ─────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    if (now - last_sample_time >= 1) {
        last_sample_time = now;

        // Sample ADC and update window states
        cli();
        for (int i = 0; i < 4; i++) {
            int adc_val = analogRead(ADC_PINS[i]);
            windowState state = window_swich(adc_val);
            window_states[i] = static_cast<uint8_t>(state);
        }
        sei();
        // Update LEDs from ISR flags
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
    // Debug — blink LED 13 if any window not OFF
    bool any_active = false;
    for (int i = 0; i < 4; i++) {
        if (window_states[i] != 0) any_active = true;
    }
    pinMode(13, OUTPUT);
    digitalWrite(13, any_active ? HIGH : LOW);
}