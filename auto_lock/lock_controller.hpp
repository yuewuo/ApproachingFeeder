#ifndef LOCK_CONTROLLER_HPP
#define LOCK_CONTROLLER_HPP

#include <string>

// Step size constants (adjustable)
constexpr int SMALL_STEP = 10;
constexpr int LARGE_STEP = 50;

// Delay per step in milliseconds (for realistic motor simulation)
constexpr int MS_PER_STEP = 5;

// Operating modes
enum class LockMode
{
    NORMAL,
    SETUP
};

/**
 * Abstract base class for stepper motor control.
 * Provides common logic for position tracking and lock/unlock operations.
 * Derived classes implement hardware-specific or mock motor control.
 */
class StepperController
{
protected:
    int current_position = 0;
    int lock_position = 0;
    int unlock_position = 0;
    LockMode mode = LockMode::SETUP;
    bool pending_return_to_center = false;

    /**
     * Move the motor by the specified number of steps.
     * Positive values = forward/clockwise, negative = backward/counter-clockwise.
     * Implementation should call releaseMotor() after movement.
     * Implementation should include appropriate delay based on step count.
     * @param steps Number of steps to move (signed)
     */
    virtual void moveSteps(int steps) = 0;

    /**
     * Release all motor coils to save power and prevent overheating.
     */
    virtual void releaseMotor() = 0;

    /**
     * Save lock_position and unlock_position to persistent storage.
     */
    virtual void saveToStorage() = 0;

    /**
     * Load lock_position and unlock_position from persistent storage.
     */
    virtual void loadFromStorage() = 0;

public:
    virtual ~StepperController() = default;

    /**
     * Initialize the controller. Call this in setup().
     * Loads saved positions from storage.
     * Automatically sets mode to NORMAL if already calibrated (lock_pos != unlock_pos).
     */
    virtual void begin()
    {
        loadFromStorage();
        // If positions differ, device is calibrated - start in normal mode
        if (lock_position != unlock_position)
        {
            mode = LockMode::NORMAL;
        }
    }

    // --- Position accessors ---
    int getCurrentPosition() const { return current_position; }
    int getLockPosition() const { return lock_position; }
    int getUnlockPosition() const { return unlock_position; }
    bool hasPendingReturnToCenter() const { return pending_return_to_center; }

    // --- Mode accessors ---
    LockMode getMode() const { return mode; }
    std::string getModeString() const
    {
        return mode == LockMode::SETUP ? "setup" : "normal";
    }

    void setMode(LockMode new_mode) { mode = new_mode; }

    bool setModeFromString(const std::string &mode_str)
    {
        if (mode_str == "setup")
        {
            mode = LockMode::SETUP;
            return true;
        }
        else if (mode_str == "normal")
        {
            mode = LockMode::NORMAL;
            return true;
        }
        return false;
    }

    // --- Movement operations (for setup mode) ---

    /**
     * Move forward by specified steps. Updates current_position.
     * @param steps Number of steps (positive)
     * @return New current position
     */
    int stepForward(int steps)
    {
        if (steps > 0)
        {
            moveSteps(steps);
            current_position += steps;
        }
        return current_position;
    }

    /**
     * Move backward by specified steps. Updates current_position.
     * @param steps Number of steps (positive value, will move backward)
     * @return New current position
     */
    int stepBackward(int steps)
    {
        if (steps > 0)
        {
            moveSteps(-steps);
            current_position -= steps;
        }
        return current_position;
    }

    // --- Calibration operations ---

    /**
     * Set the current position as the center reference (position 0).
     * @return New current position (always 0)
     */
    int setCenter()
    {
        current_position = 0;
        return current_position;
    }

    /**
     * Set the current position as the lock position.
     * Saves to persistent storage.
     * @return The lock position value
     */
    int setLockPosition()
    {
        lock_position = current_position;
        saveToStorage();
        return lock_position;
    }

    /**
     * Set the current position as the unlock position.
     * Saves to persistent storage.
     * @return The unlock position value
     */
    int setUnlockPosition()
    {
        unlock_position = current_position;
        saveToStorage();
        return unlock_position;
    }

    // --- Lock/Unlock operations ---

    /**
     * Move to the lock position.
     * After reaching target, sets pending_return_to_center flag.
     * Call processReturnToCenter() in main loop to execute the return.
     * @return Final position after movement (at lock position)
     */
    int lock()
    {
        int delta = lock_position - current_position;
        if (delta != 0)
        {
            moveSteps(delta);
            current_position = lock_position;
        }
        pending_return_to_center = true;
        return current_position;
    }

    /**
     * Move to the unlock position.
     * After reaching target, sets pending_return_to_center flag.
     * Call processReturnToCenter() in main loop to execute the return.
     * @return Final position after movement (at unlock position)
     */
    int unlock()
    {
        int delta = unlock_position - current_position;
        if (delta != 0)
        {
            moveSteps(delta);
            current_position = unlock_position;
        }
        pending_return_to_center = true;
        return current_position;
    }

    /**
     * Process return to center if pending.
     * Call this in the main loop. It will move back to position 0
     * if a lock/unlock operation has completed.
     * @return true if a return was processed, false otherwise
     */
    bool processReturnToCenter()
    {
        if (!pending_return_to_center)
        {
            return false;
        }
        pending_return_to_center = false;

        int delta = -current_position;
        if (delta != 0)
        {
            moveSteps(delta);
            current_position = 0;
        }
        return true;
    }
};

#endif // LOCK_CONTROLLER_HPP
