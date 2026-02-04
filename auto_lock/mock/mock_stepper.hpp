#ifndef MOCK_STEPPER_HPP
#define MOCK_STEPPER_HPP

#include <iostream>
#include <fstream>
#include <string>
#include <thread>
#include <chrono>
#include <cmath>
#include "lock_controller.hpp"

// Config file path for mock storage
const std::string CONFIG_FILE = "auto_lock_config.json";

/**
 * Mock implementation of StepperController for local testing.
 * Prints motor actions to stdout and stores config in a local JSON file.
 * Simulates realistic delays proportional to step count.
 */
class MockStepperController : public StepperController
{
protected:
    void moveSteps(int steps) override
    {
        int abs_steps = std::abs(steps);
        int delay_ms = abs_steps * MS_PER_STEP;

        std::cout << "MOTOR: moving " << steps << " steps (delay: " << delay_ms << "ms)" << std::endl;

        // Simulate motor movement time
        std::this_thread::sleep_for(std::chrono::milliseconds(delay_ms));

        releaseMotor();
    }

    void releaseMotor() override
    {
        std::cout << "MOTOR: released (all coils de-energized)" << std::endl;
    }

    void saveToStorage() override
    {
        std::ofstream file(CONFIG_FILE);
        if (file.is_open())
        {
            file << "{\n";
            file << "  \"lock_position\": " << lock_position << ",\n";
            file << "  \"unlock_position\": " << unlock_position << "\n";
            file << "}\n";
            file.close();
            std::cout << "CONFIG: saved lock_pos=" << lock_position
                      << ", unlock_pos=" << unlock_position << std::endl;
        }
        else
        {
            std::cerr << "CONFIG: failed to save to " << CONFIG_FILE << std::endl;
        }
    }

    void loadFromStorage() override
    {
        std::ifstream file(CONFIG_FILE);
        if (file.is_open())
        {
            std::string content((std::istreambuf_iterator<char>(file)),
                                std::istreambuf_iterator<char>());
            file.close();

            // Simple JSON parsing (good enough for our format)
            auto extractInt = [&content](const std::string &key) -> int
            {
                size_t pos = content.find("\"" + key + "\"");
                if (pos == std::string::npos)
                    return 0;
                pos = content.find(":", pos);
                if (pos == std::string::npos)
                    return 0;
                pos++;
                while (pos < content.size() && (content[pos] == ' ' || content[pos] == '\t'))
                    pos++;
                size_t end = pos;
                if (content[end] == '-')
                    end++;
                while (end < content.size() && isdigit(content[end]))
                    end++;
                return std::stoi(content.substr(pos, end - pos));
            };

            lock_position = extractInt("lock_position");
            unlock_position = extractInt("unlock_position");

            std::cout << "CONFIG: loaded lock_pos=" << lock_position
                      << ", unlock_pos=" << unlock_position << std::endl;
        }
        else
        {
            std::cout << "CONFIG: no config file found, using defaults" << std::endl;
            lock_position = 0;
            unlock_position = 0;
        }
    }

public:
    void begin() override
    {
        std::cout << "MockStepperController initialized" << std::endl;
        StepperController::begin();
    }
};

#endif // MOCK_STEPPER_HPP
