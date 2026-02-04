/*
Lonely Binary ESP32-S3 N16R8 Arduino IDE Settings:
Board: ESP32S3 Dev Module
USB CDC On Boot: "Enabled"     <--- this is essential for serial monitor to work
PSRAM: OPI PSRAM
Flash Size: 16MB (128Mb)
Flash Mode: QIO 80MHz
Partition Scheme: 16M Flash (3MB APP/9.9MB FATFS)
Upload Mode: UART0 / Hardware CDC
USB Mode: Hardware CDC and JTAG

TODO: use https when deployment
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <FastLED.h>
#include "password.hpp"
#include "lock_controller.hpp"
#include "uln2003_stepper.hpp"
#include "html_content.hpp"

// RGB LED configuration (Lonely Binary ESP32-S3 onboard LED)
#define RGB_LED_PIN 48
#define NUM_LEDS 1
CRGB leds[NUM_LEDS];

HardwareStepperController controller;
WebServer server(80);

// --- LED Position Indicator ---

/**
 * Update the RGB LED to indicate current position.
 * - Centered (0): Very dim white (standby indicator)
 * - Negative position: Red, brightness proportional to |position / lock_position|
 * - Positive position: Green, brightness proportional to |position / unlock_position|
 */
void updatePositionLED()
{
    int pos = controller.getCurrentPosition();
    int lock_pos = controller.getLockPosition();
    int unlock_pos = controller.getUnlockPosition();

    if (pos == 0)
    {
        // Centered - very dim white to indicate standby (not power loss)
        leds[0] = CRGB(2, 2, 2);
    }
    else if (pos < 0)
    {
        // Negative position - show red
        // Brightness is proportional to how close we are to lock position
        float ratio = 0.0f;
        if (lock_pos < 0)
        {
            ratio = (float)pos / (float)lock_pos; // Both negative, ratio is positive
        }
        else if (lock_pos != 0)
        {
            ratio = (float)(-pos) / (float)abs(lock_pos);
        }
        ratio = constrain(ratio, 0.0f, 1.0f);
        uint8_t brightness = (uint8_t)(ratio * 255);
        leds[0] = CRGB(brightness, 0, 0); // Red
    }
    else
    {
        // Positive position - show green
        // Brightness is proportional to how close we are to unlock position
        float ratio = 0.0f;
        if (unlock_pos > 0)
        {
            ratio = (float)pos / (float)unlock_pos;
        }
        else if (unlock_pos != 0)
        {
            ratio = (float)pos / (float)abs(unlock_pos);
        }
        ratio = constrain(ratio, 0.0f, 1.0f);
        uint8_t brightness = (uint8_t)(ratio * 255);
        leds[0] = CRGB(0, brightness, 0); // Green
    }

    FastLED.show();
}

// --- Helper functions ---

void sendJsonResponse(int code, const String &json)
{
    server.send(code, "application/json", json);
}

String getRequestBody()
{
    return server.arg("plain");
}

// Simple JSON value extraction (avoids ArduinoJson dependency)
String extractJsonString(const String &json, const String &key)
{
    String searchKey = "\"" + key + "\"";
    int keyIndex = json.indexOf(searchKey);
    if (keyIndex == -1)
        return "";

    int colonIndex = json.indexOf(':', keyIndex);
    if (colonIndex == -1)
        return "";

    int valueStart = json.indexOf('"', colonIndex);
    if (valueStart == -1)
        return "";

    int valueEnd = json.indexOf('"', valueStart + 1);
    if (valueEnd == -1)
        return "";

    return json.substring(valueStart + 1, valueEnd);
}

// --- Route handlers ---

/**
 * GET /
 * Serves the single-page web application (embedded in flash)
 */
void handleRoot()
{
    server.send_P(200, "text/html", HTML_PAGE);
}

/**
 * GET /status
 * Returns current state as JSON
 * Response: {"position": int, "lock_pos": int, "unlock_pos": int, "mode": "normal"|"setup"}
 */
void handleStatus()
{
    String json = "{";
    json += "\"position\":" + String(controller.getCurrentPosition()) + ",";
    json += "\"lock_pos\":" + String(controller.getLockPosition()) + ",";
    json += "\"unlock_pos\":" + String(controller.getUnlockPosition()) + ",";
    json += "\"mode\":\"" + String(controller.getModeString().c_str()) + "\"";
    json += "}";
    sendJsonResponse(200, json);
}

/**
 * POST /step
 * Move the motor by specified steps
 * Request: {"direction": "fwd"|"bwd", "size": "small"|"large"}
 * Response: {"position": int}
 */
void handleStep()
{
    String body = getRequestBody();
    String direction = extractJsonString(body, "direction");
    String size = extractJsonString(body, "size");

    if (direction.isEmpty() || size.isEmpty())
    {
        sendJsonResponse(400, "{\"error\":\"Missing direction or size\"}");
        return;
    }

    int steps = (size == "large") ? LARGE_STEP : SMALL_STEP;
    int newPos;

    if (direction == "fwd")
    {
        newPos = controller.stepForward(steps);
    }
    else if (direction == "bwd")
    {
        newPos = controller.stepBackward(steps);
    }
    else
    {
        sendJsonResponse(400, "{\"error\":\"Invalid direction. Use 'fwd' or 'bwd'\"}");
        return;
    }

    Serial.printf("Step: dir=%s, size=%s, steps=%d, new_pos=%d\n",
                  direction.c_str(), size.c_str(), steps, newPos);

    updatePositionLED();
    sendJsonResponse(200, "{\"position\":" + String(newPos) + "}");
}

/**
 * POST /set_center
 * Set current position as center (0)
 * Response: {"position": 0}
 */
void handleSetCenter()
{
    int pos = controller.setCenter();
    Serial.printf("Set center: position=%d\n", pos);
    updatePositionLED();
    sendJsonResponse(200, "{\"position\":" + String(pos) + "}");
}

/**
 * POST /set_lock
 * Set current position as lock position
 * Response: {"lock_pos": int}
 */
void handleSetLock()
{
    int pos = controller.setLockPosition();
    Serial.printf("Set lock position: %d\n", pos);
    sendJsonResponse(200, "{\"lock_pos\":" + String(pos) + "}");
}

/**
 * POST /set_unlock
 * Set current position as unlock position
 * Response: {"unlock_pos": int}
 */
void handleSetUnlock()
{
    int pos = controller.setUnlockPosition();
    Serial.printf("Set unlock position: %d\n", pos);
    sendJsonResponse(200, "{\"unlock_pos\":" + String(pos) + "}");
}

/**
 * POST /lock
 * Move to lock position, then automatically return to center
 * Response: {"position": int} (position at lock point, before return)
 */
void handleLock()
{
    if (controller.getMode() == LockMode::SETUP)
    {
        sendJsonResponse(400, "{\"error\":\"Cannot lock in setup mode\"}");
        return;
    }
    int pos = controller.lock();
    Serial.printf("Lock: position=%d (will return to center)\n", pos);
    updatePositionLED();
    sendJsonResponse(200, "{\"position\":" + String(pos) + "}");
}

/**
 * POST /unlock
 * Move to unlock position, then automatically return to center
 * Response: {"position": int} (position at unlock point, before return)
 */
void handleUnlock()
{
    if (controller.getMode() == LockMode::SETUP)
    {
        sendJsonResponse(400, "{\"error\":\"Cannot unlock in setup mode\"}");
        return;
    }
    int pos = controller.unlock();
    Serial.printf("Unlock: position=%d (will return to center)\n", pos);
    updatePositionLED();
    sendJsonResponse(200, "{\"position\":" + String(pos) + "}");
}

/**
 * POST /mode
 * Change operating mode
 * Request: {"mode": "setup"|"normal"}
 * Response: {"mode": "setup"|"normal"}
 */
void handleMode()
{
    String body = getRequestBody();
    String modeStr = extractJsonString(body, "mode");

    if (modeStr.isEmpty())
    {
        sendJsonResponse(400, "{\"error\":\"Missing mode\"}");
        return;
    }

    if (controller.setModeFromString(modeStr.c_str()))
    {
        Serial.printf("Mode changed to: %s\n", modeStr.c_str());
        sendJsonResponse(200, "{\"mode\":\"" + modeStr + "\"}");
    }
    else
    {
        sendJsonResponse(400, "{\"error\":\"Invalid mode. Use 'setup' or 'normal'\"}");
    }
}

/**
 * 404 handler
 */
void handleNotFound()
{
    String message = "{\"error\":\"Not Found\",\"uri\":\"" + server.uri() + "\"}";
    sendJsonResponse(404, message);
}

void setup()
{
    Serial.begin(115200);

    // Initialize RGB LED
    FastLED.addLeds<WS2812, RGB_LED_PIN, GRB>(leds, NUM_LEDS);
    leds[0] = CRGB::Black;
    FastLED.show();

    delay(100);

    // Initialize stepper controller
    controller.begin();

    // Show initial position on LED
    updatePositionLED();

    // Connect to WiFi
    Serial.println();
    Serial.print("Connecting to WiFi...");

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    // Blink blue while connecting to WiFi
    bool ledState = false;
    int attempts = 0;
    bool debugPrinted = false;
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        attempts++;
        Serial.print(".");
        leds[0] = ledState ? CRGB::Blue : CRGB::Black;
        FastLED.show();
        ledState = !ledState;

        // Print debug info after 30 seconds if not connected
        if (attempts == 60 && !debugPrinted)
        {
            debugPrinted = true;
            Serial.println("\n\n=== WiFi Debug (not connected after 30s) ===");
            Serial.printf("Target SSID: '%s'\n", ssid);
            Serial.printf("Password length: %d\n", strlen(password));
            Serial.printf("WiFi status: %d\n", WiFi.status());
            // Status: 0=IDLE, 1=NO_SSID_AVAIL, 4=CONNECT_FAILED, 6=DISCONNECTED

            // Scan for available networks
            Serial.println("Scanning networks...");
            int numNetworks = WiFi.scanNetworks();
            Serial.printf("Found %d networks:\n", numNetworks);
            for (int i = 0; i < numNetworks; i++)
            {
                Serial.printf("  %d: '%s' (%d dBm)%s\n",
                              i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i),
                              (WiFi.SSID(i) == ssid) ? " <-- TARGET" : "");
            }
            Serial.println("Retrying connection...");
            WiFi.begin(ssid, password);
        }

        // Timeout after 60 seconds
        if (attempts > 120)
        {
            Serial.println("\n*** WiFi timeout! Restarting... ***");
            delay(3000);
            ESP.restart();
        }
    }

    // WiFi connected - show green briefly
    leds[0] = CRGB::Green;
    FastLED.show();
    delay(500);

    Serial.println("");
    Serial.println("WiFi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    // Start mDNS
    if (MDNS.begin("auto_lock"))
    {
        Serial.println("MDNS responder started: http://auto_lock.local");
    }

    // Show position on LED
    updatePositionLED();

    // Register routes
    server.on("/", HTTP_GET, handleRoot);
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/step", HTTP_POST, handleStep);
    server.on("/set_center", HTTP_POST, handleSetCenter);
    server.on("/set_lock", HTTP_POST, handleSetLock);
    server.on("/set_unlock", HTTP_POST, handleSetUnlock);
    server.on("/lock", HTTP_POST, handleLock);
    server.on("/unlock", HTTP_POST, handleUnlock);
    server.on("/mode", HTTP_POST, handleMode);
    server.onNotFound(handleNotFound);

    server.begin();
    Serial.println("HTTP server started");
}

void loop()
{
    server.handleClient();

    // Process return-to-center after lock/unlock operations
    if (controller.hasPendingReturnToCenter())
    {
        Serial.println("Processing return to center...");
        controller.processReturnToCenter();
        Serial.printf("Returned to center, position=%d\n", controller.getCurrentPosition());
        updatePositionLED();
    }

    delay(2); // Allow CPU to handle other tasks
}
