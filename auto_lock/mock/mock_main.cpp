/**
 * Mock server for auto_lock testing.
 * Uses cpp-httplib to provide the same HTTP API as the ESP32 firmware.
 *
 * Build (from auto_lock directory):
 *   make
 *
 * Run:
 *   ./mock_server [port]
 *   Default port: 8080
 *
 * Dependencies:
 *   - httplib.h (cpp-httplib, header-only) - download with:
 *     make deps
 */

#include <iostream>
#include <fstream>
#include <string>
#include <csignal>
#include <thread>
#include <atomic>
#include <mutex>
#include "httplib.h"
#include "../lock_controller.hpp"
#include "mock_stepper.hpp"

MockStepperController controller;
httplib::Server server;
std::string html_content;        // Cached HTML content
std::mutex controller_mutex;     // Protect controller access from multiple threads
std::atomic<bool> running{true}; // Flag for background thread

// Background thread to process return-to-center
void returnToCenterWorker()
{
    while (running)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        std::lock_guard<std::mutex> lock(controller_mutex);
        if (controller.hasPendingReturnToCenter())
        {
            std::cout << "BACKGROUND: Starting return to center..." << std::endl;
            controller.processReturnToCenter();
            std::cout << "BACKGROUND: Returned to center, position=" << controller.getCurrentPosition() << std::endl;
        }
    }
}

// --- Helper functions ---

std::string loadHtmlFile(const std::string &filename)
{
    std::ifstream file(filename);
    if (!file.is_open())
    {
        std::cerr << "Warning: Could not load " << filename << std::endl;
        return "";
    }
    std::string content((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    file.close();
    return content;
}

std::string extractJsonString(const std::string &json, const std::string &key)
{
    std::string searchKey = "\"" + key + "\"";
    size_t keyIndex = json.find(searchKey);
    if (keyIndex == std::string::npos)
        return "";

    size_t colonIndex = json.find(':', keyIndex);
    if (colonIndex == std::string::npos)
        return "";

    size_t valueStart = json.find('"', colonIndex);
    if (valueStart == std::string::npos)
        return "";

    size_t valueEnd = json.find('"', valueStart + 1);
    if (valueEnd == std::string::npos)
        return "";

    return json.substr(valueStart + 1, valueEnd - valueStart - 1);
}

int extractJsonInt(const std::string &json, const std::string &key, int defaultValue = 0)
{
    std::string searchKey = "\"" + key + "\"";
    size_t keyIndex = json.find(searchKey);
    if (keyIndex == std::string::npos)
        return defaultValue;

    size_t colonIndex = json.find(':', keyIndex);
    if (colonIndex == std::string::npos)
        return defaultValue;

    // Skip whitespace after colon
    size_t valueStart = colonIndex + 1;
    while (valueStart < json.length() && json[valueStart] == ' ')
        valueStart++;

    // Find end of number
    size_t valueEnd = valueStart;
    while (valueEnd < json.length() && (isdigit(json[valueEnd]) || json[valueEnd] == '-'))
        valueEnd++;

    if (valueEnd == valueStart)
        return defaultValue;

    return std::stoi(json.substr(valueStart, valueEnd - valueStart));
}

// --- Signal handler for graceful shutdown ---

void signalHandler(int /* signum */)
{
    std::cout << "\nShutting down server..." << std::endl;
    running = false;
    server.stop();
}

// --- Main ---

int main(int argc, char *argv[])
{
    int port = 8080;
    if (argc > 1)
    {
        port = std::stoi(argv[1]);
    }

    // Register signal handler
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    // Load HTML file
    html_content = loadHtmlFile("auto_lock.html");
    if (html_content.empty())
    {
        std::cerr << "Warning: auto_lock.html not found, using fallback page" << std::endl;
    }

    // Initialize controller
    controller.begin();

    // Start background thread for return-to-center processing
    std::thread returnThread(returnToCenterWorker);

    // Enable CORS for browser testing
    server.set_default_headers({{"Access-Control-Allow-Origin", "*"},
                                {"Access-Control-Allow-Methods", "GET, POST, OPTIONS"},
                                {"Access-Control-Allow-Headers", "Content-Type"}});

    // Handle preflight requests
    server.Options(".*", [](const httplib::Request & /* req */, httplib::Response &res)
                   { res.status = 204; });

    /**
     * GET /
     * Returns the single-page web application
     */
    server.Get("/", [](const httplib::Request & /* req */, httplib::Response &res)
               {
        if (!html_content.empty()) {
            res.set_content(html_content, "text/html");
        } else {
            // Fallback if HTML file not found
            std::string html = "<!DOCTYPE html><html><head><title>Auto Lock (Mock)</title></head><body>";
            html += "<h1>Auto Lock Controller (Mock Server)</h1>";
            html += "<p>Error: auto_lock.html not found</p>";
            html += "<p>Position: " + std::to_string(controller.getCurrentPosition()) + "</p>";
            html += "<p>Lock Position: " + std::to_string(controller.getLockPosition()) + "</p>";
            html += "<p>Unlock Position: " + std::to_string(controller.getUnlockPosition()) + "</p>";
            html += "<p>Mode: " + controller.getModeString() + "</p>";
            html += "<p><a href='/status'>JSON Status</a></p>";
            html += "</body></html>";
            res.set_content(html, "text/html");
        } });

    /**
     * GET /status
     * Returns current state as JSON
     * Response: {"position": int, "lock_pos": int, "unlock_pos": int, "mode": "normal"|"setup"}
     */
    server.Get("/status", [](const httplib::Request & /* req */, httplib::Response &res)
               {
        std::lock_guard<std::mutex> lock(controller_mutex);
        std::string json = "{";
        json += "\"position\":" + std::to_string(controller.getCurrentPosition()) + ",";
        json += "\"lock_pos\":" + std::to_string(controller.getLockPosition()) + ",";
        json += "\"unlock_pos\":" + std::to_string(controller.getUnlockPosition()) + ",";
        json += "\"mode\":\"" + controller.getModeString() + "\"";
        json += "}";
        res.set_content(json, "application/json"); });

    /**
     * POST /step
     * Move the motor by specified steps
     * Request: {"direction": "fwd"|"bwd", "size": "small"|"large"|"custom", "steps": int (optional)}
     * Response: {"position": int}
     */
    server.Post("/step", [](const httplib::Request &req, httplib::Response &res)
                {
        std::string direction = extractJsonString(req.body, "direction");
        std::string size = extractJsonString(req.body, "size");

        if (direction.empty() || size.empty()) {
            res.status = 400;
            res.set_content("{\"error\":\"Missing direction or size\"}", "application/json");
            return;
        }

        int steps;
        if (size == "custom") {
            steps = extractJsonInt(req.body, "steps", SMALL_STEP);
            steps = std::min(std::max(steps, 1), 2048); // Limit custom steps
        } else {
            steps = (size == "large") ? LARGE_STEP : SMALL_STEP;
        }

        int newPos;

        {
            std::lock_guard<std::mutex> lock(controller_mutex);
            if (direction == "fwd") {
                newPos = controller.stepForward(steps);
            } else if (direction == "bwd") {
                newPos = controller.stepBackward(steps);
            } else {
                res.status = 400;
                res.set_content("{\"error\":\"Invalid direction. Use 'fwd' or 'bwd'\"}", "application/json");
                return;
            }
        }

        std::cout << "API: /step dir=" << direction << " size=" << size
                  << " steps=" << steps << " new_pos=" << newPos << std::endl;

        res.set_content("{\"position\":" + std::to_string(newPos) + "}", "application/json"); });

    /**
     * POST /set_center
     * Set current position as center (0)
     * Response: {"position": 0}
     */
    server.Post("/set_center", [](const httplib::Request & /* req */, httplib::Response &res)
                {
        std::lock_guard<std::mutex> lock(controller_mutex);
        int pos = controller.setCenter();
        std::cout << "API: /set_center position=" << pos << std::endl;
        res.set_content("{\"position\":" + std::to_string(pos) + "}", "application/json"); });

    /**
     * POST /set_lock
     * Set current position as lock position
     * Response: {"lock_pos": int}
     */
    server.Post("/set_lock", [](const httplib::Request & /* req */, httplib::Response &res)
                {
        std::lock_guard<std::mutex> lock(controller_mutex);
        int pos = controller.setLockPosition();
        std::cout << "API: /set_lock lock_pos=" << pos << std::endl;
        res.set_content("{\"lock_pos\":" + std::to_string(pos) + "}", "application/json"); });

    /**
     * POST /set_unlock
     * Set current position as unlock position
     * Response: {"unlock_pos": int}
     */
    server.Post("/set_unlock", [](const httplib::Request & /* req */, httplib::Response &res)
                {
        std::lock_guard<std::mutex> lock(controller_mutex);
        int pos = controller.setUnlockPosition();
        std::cout << "API: /set_unlock unlock_pos=" << pos << std::endl;
        res.set_content("{\"unlock_pos\":" + std::to_string(pos) + "}", "application/json"); });

    /**
     * POST /lock
     * Move to lock position, then automatically return to center
     * Response: {"position": int} (position at lock point, before return)
     */
    server.Post("/lock", [](const httplib::Request & /* req */, httplib::Response &res)
                {
        std::lock_guard<std::mutex> lock(controller_mutex);
        if (controller.getMode() == LockMode::SETUP) {
            res.status = 400;
            res.set_content("{\"error\":\"Cannot lock in setup mode\"}", "application/json");
            return;
        }
        int pos = controller.lock();
        std::cout << "API: /lock position=" << pos << " (will return to center)" << std::endl;
        res.set_content("{\"position\":" + std::to_string(pos) + "}", "application/json"); });

    /**
     * POST /unlock
     * Move to unlock position, then automatically return to center
     * Response: {"position": int} (position at unlock point, before return)
     */
    server.Post("/unlock", [](const httplib::Request & /* req */, httplib::Response &res)
                {
        std::lock_guard<std::mutex> lock(controller_mutex);
        if (controller.getMode() == LockMode::SETUP) {
            res.status = 400;
            res.set_content("{\"error\":\"Cannot unlock in setup mode\"}", "application/json");
            return;
        }
        int pos = controller.unlock();
        std::cout << "API: /unlock position=" << pos << " (will return to center)" << std::endl;
        res.set_content("{\"position\":" + std::to_string(pos) + "}", "application/json"); });

    /**
     * POST /mode
     * Change operating mode
     * Request: {"mode": "setup"|"normal"}
     * Response: {"mode": "setup"|"normal"}
     */
    server.Post("/mode", [](const httplib::Request &req, httplib::Response &res)
                {
        std::string modeStr = extractJsonString(req.body, "mode");

        if (modeStr.empty()) {
            res.status = 400;
            res.set_content("{\"error\":\"Missing mode\"}", "application/json");
            return;
        }

        std::lock_guard<std::mutex> lock(controller_mutex);
        if (controller.setModeFromString(modeStr)) {
            std::cout << "API: /mode mode=" << modeStr << std::endl;
            res.set_content("{\"mode\":\"" + modeStr + "\"}", "application/json");
        } else {
            res.status = 400;
            res.set_content("{\"error\":\"Invalid mode. Use 'setup' or 'normal'\"}", "application/json");
        } });

    // 404 handler
    server.set_error_handler([](const httplib::Request &req, httplib::Response &res)
                             {
        if (res.status == 404) {
            res.set_content("{\"error\":\"Not Found\",\"uri\":\"" + req.path + "\"}", "application/json");
        } });

    std::cout << "==================================" << std::endl;
    std::cout << "Auto Lock Mock Server" << std::endl;
    std::cout << "==================================" << std::endl;
    std::cout << "Listening on http://localhost:" << port << std::endl;
    std::cout << "Press Ctrl+C to stop" << std::endl;
    std::cout << "==================================" << std::endl;

    server.listen("0.0.0.0", port);

    // Clean up background thread
    running = false;
    if (returnThread.joinable())
    {
        returnThread.join();
    }

    return 0;
}
