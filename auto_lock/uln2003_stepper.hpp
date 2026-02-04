#ifndef ULN2003_STEPPER_HPP
#define ULN2003_STEPPER_HPP

#include <Arduino.h>
#include <Preferences.h>
#include "lock_controller.hpp"

// GPIO pins for ULN2003 driver (IN1-IN4)
// Adjust these based on your ESP32-S3 wiring
constexpr int STEPPER_PIN_1 = 4; // IN1
constexpr int STEPPER_PIN_2 = 5; // IN2
constexpr int STEPPER_PIN_3 = 6; // IN3
constexpr int STEPPER_PIN_4 = 7; // IN4

// Step delay in microseconds (controls motor speed)
// Lower = faster, but may cause missed steps
constexpr int STEP_DELAY_US = 2000;

// NVS namespace for storing positions
constexpr const char *NVS_NAMESPACE = "auto_lock";

/**
 * Hardware implementation of StepperController for ULN2003 driver.
 * Uses half-step sequence for smoother operation.
 * Stores configuration in ESP32 NVS (Preferences library).
 */
class HardwareStepperController : public StepperController
{
private:
    Preferences preferences;
    int current_phase = 0;

    // Half-step sequence for 28BYJ-48 stepper motor with ULN2003
    // 8 phases for smoother operation and higher resolution
    const int HALF_STEP_SEQUENCE[8][4] = {
        {1, 0, 0, 0}, // Phase 0
        {1, 1, 0, 0}, // Phase 1
        {0, 1, 0, 0}, // Phase 2
        {0, 1, 1, 0}, // Phase 3
        {0, 0, 1, 0}, // Phase 4
        {0, 0, 1, 1}, // Phase 5
        {0, 0, 0, 1}, // Phase 6
        {1, 0, 0, 1}, // Phase 7
    };

    void setPhase(int phase)
    {
        digitalWrite(STEPPER_PIN_1, HALF_STEP_SEQUENCE[phase][0]);
        digitalWrite(STEPPER_PIN_2, HALF_STEP_SEQUENCE[phase][1]);
        digitalWrite(STEPPER_PIN_3, HALF_STEP_SEQUENCE[phase][2]);
        digitalWrite(STEPPER_PIN_4, HALF_STEP_SEQUENCE[phase][3]);
    }

    void stepOnce(bool forward)
    {
        if (forward)
        {
            current_phase = (current_phase + 1) % 8;
        }
        else
        {
            current_phase = (current_phase + 7) % 8; // -1 mod 8
        }
        setPhase(current_phase);
        delayMicroseconds(STEP_DELAY_US);
    }

protected:
    void moveSteps(int steps) override
    {
        bool forward = steps > 0;
        int abs_steps = forward ? steps : -steps;

        for (int i = 0; i < abs_steps; i++)
        {
            stepOnce(forward);
        }

        // Always release motor after movement to save power
        releaseMotor();
    }

    void releaseMotor() override
    {
        digitalWrite(STEPPER_PIN_1, LOW);
        digitalWrite(STEPPER_PIN_2, LOW);
        digitalWrite(STEPPER_PIN_3, LOW);
        digitalWrite(STEPPER_PIN_4, LOW);
    }

    void saveToStorage() override
    {
        preferences.begin(NVS_NAMESPACE, false); // false = read/write
        preferences.putInt("lock_pos", lock_position);
        preferences.putInt("unlock_pos", unlock_position);
        preferences.end();
        Serial.printf("Saved: lock_pos=%d, unlock_pos=%d\n", lock_position, unlock_position);
    }

    void loadFromStorage() override
    {
        preferences.begin(NVS_NAMESPACE, true); // true = read-only
        lock_position = preferences.getInt("lock_pos", 0);
        unlock_position = preferences.getInt("unlock_pos", 0);
        preferences.end();
        Serial.printf("Loaded: lock_pos=%d, unlock_pos=%d\n", lock_position, unlock_position);
    }

public:
    void begin() override
    {
        // Initialize GPIO pins
        pinMode(STEPPER_PIN_1, OUTPUT);
        pinMode(STEPPER_PIN_2, OUTPUT);
        pinMode(STEPPER_PIN_3, OUTPUT);
        pinMode(STEPPER_PIN_4, OUTPUT);

        // Start with motor released
        releaseMotor();

        // Load saved positions
        StepperController::begin();

        Serial.println("HardwareStepperController initialized");
        Serial.printf("Pins: IN1=%d, IN2=%d, IN3=%d, IN4=%d\n",
                      STEPPER_PIN_1, STEPPER_PIN_2, STEPPER_PIN_3, STEPPER_PIN_4);
    }
};

#endif // ULN2003_STEPPER_HPP
