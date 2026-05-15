#include "motor_driver.h"
#include <Arduino.h>
#include "config.h"

const long AUTO_DURATION = 5000; // 5 seconds of movement

struct MotorState
{
    int pin_en;
    int pin_in1;
    int pin_in2;
    uint8_t current_cmd;
    bool is_auto;
    unsigned long auto_start_time;
    uint8_t auto_direction;
    unsigned long last_position_update_time;
    long motor_position;
};

MotorState motors[4];

void set_motor(int pin_en, int pin_in1, int pin_in2, uint8_t command)
{
    if (command == CMD_UP)
    {
        digitalWrite(pin_in1, HIGH);
        digitalWrite(pin_in2, LOW);
        analogWrite(pin_en, 255);
    }
    else if (command == CMD_DOWN)
    {
        digitalWrite(pin_in1, LOW);
        digitalWrite(pin_in2, HIGH);
        analogWrite(pin_en, 255);
    }
    else
    { // CMD_STOP
        digitalWrite(pin_in1, LOW);
        digitalWrite(pin_in2, LOW);
        analogWrite(pin_en, 0);
    }
}

void motor_driver_init()
{
    pinMode(ENA_WA, OUTPUT);
    pinMode(IN1_WA, OUTPUT);
    pinMode(IN2_WA, OUTPUT);

    pinMode(ENB_WB, OUTPUT);
    pinMode(IN3_WB, OUTPUT);
    pinMode(IN4_WB, OUTPUT);

    pinMode(ENA_PA, OUTPUT);
    pinMode(INP1_PA, OUTPUT);
    pinMode(INP2_PA, OUTPUT);

    pinMode(ENB_PB, OUTPUT);
    pinMode(INP1_PB, OUTPUT);
    pinMode(INP2_PB, OUTPUT);

    motors[0] = {ENA_WA, IN1_WA, IN2_WA, CMD_STOP, false, 0, CMD_STOP, 0, AUTO_DURATION};
    motors[1] = {ENB_WB, IN3_WB, IN4_WB, CMD_STOP, false, 0, CMD_STOP, 0, AUTO_DURATION};
    motors[2] = {ENA_PA, INP1_PA, INP2_PA, CMD_STOP, false, 0, CMD_STOP, 0, 0};
    motors[3] = {ENB_PB, INP1_PB, INP2_PB, CMD_STOP, false, 0, CMD_STOP, 0, 0};
}

void process_motor_command(int m_id, uint8_t command)
{
    // Ignore UP commands if the window is already fully up
    if ((command == CMD_UP || command == CMD_UP_AUTO) && motors[m_id].motor_position >= AUTO_DURATION)
    {
        return;
    }

    // Ignore DOWN commands if the window is already fully down
    if ((command == CMD_DOWN || command == CMD_DOWN_AUTO) && motors[m_id].motor_position <= 0)
    {
        return;
    }

    // CANCEL AUTO ROLL IF OPPOSITE DIRECTION IS PRESSED
    if (motors[m_id].is_auto) {
        if (motors[m_id].current_cmd == CMD_UP && (command == CMD_DOWN || command == CMD_DOWN_AUTO)) {
            motors[m_id].is_auto = false;
            motors[m_id].current_cmd = CMD_STOP;
            set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, CMD_STOP);
            return; 
        }
        else if (motors[m_id].current_cmd == CMD_DOWN && (command == CMD_UP || command == CMD_UP_AUTO)) {
            motors[m_id].is_auto = false;
            motors[m_id].current_cmd = CMD_STOP;
            set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, CMD_STOP);
            return; 
        }
    }

    if (command == CMD_UP_AUTO)
    {
        motors[m_id].is_auto = true;
        // We don't need auto_start_time anymore because update_all_motors tracks the exact position!
        motors[m_id].current_cmd = CMD_UP;
        set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, CMD_UP);
    }
    else if (command == CMD_DOWN_AUTO)
    {
        motors[m_id].is_auto = true;
        motors[m_id].current_cmd = CMD_DOWN;
        set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, CMD_DOWN);
    }
    else if (command == CMD_UP || command == CMD_DOWN)
    {
        motors[m_id].is_auto = false;
        motors[m_id].current_cmd = command;
        set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, command);
    }
    else if (command == CMD_STOP)
    {
        if (!motors[m_id].is_auto)
        {
            // ONLY stop if we aren't in the middle of an AUTO roll!
            motors[m_id].current_cmd = CMD_STOP;
            set_motor(motors[m_id].pin_en, motors[m_id].pin_in1, motors[m_id].pin_in2, CMD_STOP);
        }
    }
}

void update_all_motors()
{
    for (int i = 0; i < 4; i++)
    {
        unsigned long now = millis();
        unsigned long delta = now - motors[i].last_position_update_time;
        motors[i].last_position_update_time = now;
        if (motors[i].current_cmd == CMD_UP)
        {
            motors[i].motor_position += delta;
            if (motors[i].motor_position >= AUTO_DURATION)
            {
                motors[i].motor_position = AUTO_DURATION; // Lock it exactly to the limit
                motors[i].is_auto = false;
                motors[i].current_cmd = CMD_STOP;
                set_motor(motors[i].pin_en, motors[i].pin_in1, motors[i].pin_in2, CMD_STOP);
            }
        }
        else if (motors[i].current_cmd == CMD_DOWN)
        {
            motors[i].motor_position -= delta;
            if (motors[i].motor_position <= 0)
            {
                motors[i].motor_position = 0; // Lock it exactly to the limit
                motors[i].is_auto = false;
                motors[i].current_cmd = CMD_STOP;
                set_motor(motors[i].pin_en, motors[i].pin_in1, motors[i].pin_in2, CMD_STOP);
            }
        }
    }
}

void motorWA_command(uint8_t command) { process_motor_command(0, command); }
void motorWB_command(uint8_t command) { process_motor_command(1, command); }
void motorPA_command(uint8_t command) { process_motor_command(2, command); }
void motorPB_command(uint8_t command) { process_motor_command(3, command); }

void stop_all_motors()
{
    motorWA_command(CMD_STOP);
    motorWB_command(CMD_STOP);
    motorPA_command(CMD_STOP);
    motorPB_command(CMD_STOP);
}
