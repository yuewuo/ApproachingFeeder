#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include "password.hpp"
#include "lock_controller.hpp"
#include "uln2003_stepper.hpp"

const int LED_PIN = LED_BUILTIN;

HardwareStepperController controller;
WebServer server(80);

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
 * Returns a simple HTML status page
 */
void handleRoot()
{
    digitalWrite(LED_PIN, HIGH);
    String html = "<!DOCTYPE html><html><head><title>Auto Lock</title></head><body>";
    html += "<h1>Auto Lock Controller</h1>";
    html += "<p>Position: " + String(controller.getCurrentPosition()) + "</p>";
    html += "<p>Lock Position: " + String(controller.getLockPosition()) + "</p>";
    html += "<p>Unlock Position: " + String(controller.getUnlockPosition()) + "</p>";
    html += "<p>Mode: " + String(controller.getModeString().c_str()) + "</p>";
    html += "<p><a href='/status'>JSON Status</a></p>";
    html += "</body></html>";
    server.send(200, "text/html", html);
    digitalWrite(LED_PIN, LOW);
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
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    delay(100);

    // Initialize stepper controller
    controller.begin();

    // Connect to WiFi
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
        digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Blink while connecting
    }

    digitalWrite(LED_PIN, LOW);
    Serial.println("");
    Serial.println("WiFi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    // Start mDNS
    if (MDNS.begin("auto_lock"))
    {
        Serial.println("MDNS responder started: http://auto_lock.local");
    }

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
    }

    delay(2); // Allow CPU to handle other tasks
}
