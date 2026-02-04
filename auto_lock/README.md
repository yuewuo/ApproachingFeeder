# Auto Lock Controller

An ESP32-S3 based automatic door lock controller using a ULN2003 stepper motor driver.

## Features

- Web-based control interface with visual position dial
- Setup wizard for calibrating lock/unlock positions
- Persistent storage of calibration using ESP32 NVS
- Mock server for local development and testing without hardware
- Motor auto-release after movement to save power

## Hardware Requirements

- ESP32-S3 (Lonely Binary or compatible)
- ULN2003 stepper motor driver
- 28BYJ-48 stepper motor (or compatible 5V stepper)
- 5V power supply for motor

## Wiring Diagram

```
ESP32-S3          ULN2003
---------         -------
GPIO 4   ──────── IN1
GPIO 5   ──────── IN2
GPIO 6   ──────── IN3
GPIO 7   ──────── IN4
GND      ──────── GND

External 5V ───── +5V (motor power)
```

> **Note:** The ULN2003 motor power should be from an external 5V supply, not the ESP32's 3.3V pin. The ESP32 GPIO pins provide control signals only.

## Setup

### 1. Configure WiFi Credentials

```bash
cd auto_lock
cp password.hpp.template password.hpp
# Edit password.hpp with your WiFi SSID and password
```

### 2. Upload to ESP32-S3

Using Arduino IDE or PlatformIO:
1. Open `auto_lock.ino`
2. Select board: ESP32S3 Dev Module
3. Upload

### 3. Access Web Interface

After upload, the ESP32 will connect to WiFi and start the web server:
- mDNS: `http://auto_lock.local`
- Or check Serial Monitor for IP address

## Mock Server (Local Testing)

The mock server allows testing the full API without hardware.

### Build

```bash
cd auto_lock

# Download cpp-httplib (header-only library)
curl -O https://raw.githubusercontent.com/yhirose/cpp-httplib/master/httplib.h

# Build mock server
g++ -std=c++17 mock_main.cpp -o mock_server -pthread
```

### Run

```bash
./mock_server [port]
# Default port: 8080
```

### Test with Web GUI

1. Start mock server: `./mock_server`
2. Open `auto_lock.html` in a browser
3. Set MCU Address to `http://localhost:8080`
4. Use the interface to test calibration and lock/unlock

## HTTP API Reference

All endpoints return JSON. POST endpoints accept JSON body.

### `GET /status`

Get current controller state.

**Response:**
```json
{
  "position": 0,
  "lock_pos": -50,
  "unlock_pos": 50,
  "mode": "normal"
}
```

### `POST /step`

Move the motor by specified steps.

**Request:**
```json
{
  "direction": "fwd",
  "size": "small"
}
```

| Field     | Values               | Description                          |
| --------- | -------------------- | ------------------------------------ |
| direction | `"fwd"`, `"bwd"`     | Forward (CW) or backward (CCW)       |
| size      | `"small"`, `"large"` | Small (10 steps) or large (50 steps) |

**Response:**
```json
{
  "position": 10
}
```

### `POST /set_center`

Set current position as center reference (resets to 0).

**Response:**
```json
{
  "position": 0
}
```

### `POST /set_lock`

Save current position as the lock position.

**Response:**
```json
{
  "lock_pos": -50
}
```

### `POST /set_unlock`

Save current position as the unlock position.

**Response:**
```json
{
  "unlock_pos": 50
}
```

### `POST /lock`

Move to the saved lock position. Only works in normal mode.

**Response:**
```json
{
  "position": -50
}
```

### `POST /unlock`

Move to the saved unlock position. Only works in normal mode.

**Response:**
```json
{
  "position": 50
}
```

### `POST /mode`

Change operating mode.

**Request:**
```json
{
  "mode": "normal"
}
```

| Mode       | Description                                     |
| ---------- | ----------------------------------------------- |
| `"setup"`  | Calibration mode - allows setting positions     |
| `"normal"` | Normal operation - enables lock/unlock commands |

**Response:**
```json
{
  "mode": "normal"
}
```

## Example curl Commands

```bash
# Get status
curl http://localhost:8080/status

# Move forward small step
curl -X POST http://localhost:8080/step \
  -H "Content-Type: application/json" \
  -d '{"direction":"fwd","size":"small"}'

# Move backward large step
curl -X POST http://localhost:8080/step \
  -H "Content-Type: application/json" \
  -d '{"direction":"bwd","size":"large"}'

# Set center position
curl -X POST http://localhost:8080/set_center

# Set lock position
curl -X POST http://localhost:8080/set_lock

# Set unlock position
curl -X POST http://localhost:8080/set_unlock

# Switch to normal mode
curl -X POST http://localhost:8080/mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"normal"}'

# Lock the door
curl -X POST http://localhost:8080/lock

# Unlock the door
curl -X POST http://localhost:8080/unlock
```

## Configuration

Step sizes can be adjusted in `lock_controller.hpp`:

```cpp
constexpr int SMALL_STEP = 10;   // Steps per small movement
constexpr int LARGE_STEP = 50;   // Steps per large movement
```

Motor speed can be adjusted in `uln2003_stepper.hpp`:

```cpp
constexpr int STEP_DELAY_US = 2000;  // Microseconds between steps
```

GPIO pins can be changed in `uln2003_stepper.hpp`:

```cpp
constexpr int STEPPER_PIN_1 = 4;  // IN1
constexpr int STEPPER_PIN_2 = 5;  // IN2
constexpr int STEPPER_PIN_3 = 6;  // IN3
constexpr int STEPPER_PIN_4 = 7;  // IN4
```

## File Structure

```
auto_lock/
├── auto_lock.ino           # Arduino entry point
├── lock_controller.hpp     # Abstract controller class (shared)
├── uln2003_stepper.hpp     # Hardware stepper implementation
├── mock_stepper.hpp        # Mock stepper for testing
├── mock_main.cpp           # Mock HTTP server
├── auto_lock.html          # Web GUI
├── password.hpp.template   # WiFi credentials template
└── README.md               # This file
```

## License

See repository LICENSE file.
