# Auto Lock Mock Server Makefile

CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I.
LDFLAGS = -pthread

TARGET = mock_server
SOURCES = mock/mock_main.cpp
HEADERS = lock_controller.hpp mock/mock_stepper.hpp mock/httplib.h

PORT ?= 8080

# Arduino CLI settings for Lonely Binary ESP32-S3 N16R8
FQBN = esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,UploadMode=default,FlashMode=qio,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi
SERIAL_PORT ?= $(shell arduino-cli board list | grep -m1 usbmodem | awk '{print $$1}')
BAUD_RATE ?= 115200

.PHONY: all clean run deps html arduino upload flash monitor serial devices ports help

all: html $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $(TARGET) $(LDFLAGS)

# Generate html_content.hpp from auto_lock.html (always runs)
html:
	python3 generate_html_header.py

# Download cpp-httplib if not present
deps: mock/httplib.h

mock/httplib.h:
	mkdir -p mock
	curl -so mock/httplib.h https://raw.githubusercontent.com/yhirose/cpp-httplib/master/httplib.h

# --- Arduino CLI targets ---

# Compile Arduino sketch (verify only)
arduino:
	arduino-cli compile --fqbn "$(FQBN)" auto_lock.ino

# Upload to ESP32 (also compiles)
upload: html
	arduino-cli compile --fqbn "$(FQBN)" auto_lock.ino
	arduino-cli upload --fqbn "$(FQBN)" -p $(SERIAL_PORT) auto_lock.ino

# Alias for upload
flash: upload

# Open serial monitor
monitor:
	arduino-cli monitor -p $(SERIAL_PORT) -c baudrate=$(BAUD_RATE)

# Alias for monitor
serial: monitor

# List connected devices
devices:
	arduino-cli board list

# Alias for devices
ports: devices

# --- Mock server targets ---

run: $(TARGET)
	./$(TARGET) $(PORT)

clean:
	rm -f $(TARGET) auto_lock_config.json

# Install httplib and build
setup: deps all

# Test the server with curl commands
test: $(TARGET)
	@echo "Starting server in background..."
	@./$(TARGET) $(PORT) & echo $$! > .server.pid
	@sleep 1
	@echo "\n=== GET /status ==="
	@curl -s http://localhost:$(PORT)/status | python3 -m json.tool || true
	@echo "\n=== POST /step (fwd, small) ==="
	@curl -s -X POST http://localhost:$(PORT)/step -H "Content-Type: application/json" -d '{"direction":"fwd","size":"small"}' | python3 -m json.tool || true
	@echo "\n=== POST /step (bwd, large) ==="
	@curl -s -X POST http://localhost:$(PORT)/step -H "Content-Type: application/json" -d '{"direction":"bwd","size":"large"}' | python3 -m json.tool || true
	@echo "\n=== POST /set_center ==="
	@curl -s -X POST http://localhost:$(PORT)/set_center | python3 -m json.tool || true
	@echo "\n=== POST /set_lock ==="
	@curl -s -X POST http://localhost:$(PORT)/step -H "Content-Type: application/json" -d '{"direction":"bwd","size":"large"}' > /dev/null
	@curl -s -X POST http://localhost:$(PORT)/set_lock | python3 -m json.tool || true
	@echo "\n=== POST /set_unlock ==="
	@curl -s -X POST http://localhost:$(PORT)/step -H "Content-Type: application/json" -d '{"direction":"fwd","size":"large"}' > /dev/null
	@curl -s -X POST http://localhost:$(PORT)/step -H "Content-Type: application/json" -d '{"direction":"fwd","size":"large"}' > /dev/null
	@curl -s -X POST http://localhost:$(PORT)/set_unlock | python3 -m json.tool || true
	@echo "\n=== POST /mode (normal) ==="
	@curl -s -X POST http://localhost:$(PORT)/mode -H "Content-Type: application/json" -d '{"mode":"normal"}' | python3 -m json.tool || true
	@echo "\n=== POST /lock ==="
	@curl -s -X POST http://localhost:$(PORT)/lock | python3 -m json.tool || true
	@echo "\n=== POST /unlock ==="
	@curl -s -X POST http://localhost:$(PORT)/unlock | python3 -m json.tool || true
	@echo "\n=== Final status ==="
	@curl -s http://localhost:$(PORT)/status | python3 -m json.tool || true
	@echo "\nStopping server..."
	@kill `cat .server.pid` 2>/dev/null || true
	@rm -f .server.pid
	@echo "Done."

# Show available commands
help:
	@echo "Auto Lock Makefile Commands"
	@echo "==========================="
	@echo ""
	@echo "Arduino/ESP32:"
	@echo "  make arduino    - Compile sketch (verify only)"
	@echo "  make upload     - Compile and upload to ESP32"
	@echo "  make flash      - Alias for upload"
	@echo "  make monitor    - Open serial monitor (Ctrl+C to exit)"
	@echo "  make serial     - Alias for monitor"
	@echo "  make devices    - List connected boards"
	@echo "  make ports      - Alias for devices"
	@echo ""
	@echo "Mock Server:"
	@echo "  make            - Build mock server"
	@echo "  make run        - Run mock server on port $(PORT)"
	@echo "  make test       - Run API tests"
	@echo ""
	@echo "Other:"
	@echo "  make html       - Regenerate html_content.hpp"
	@echo "  make deps       - Download cpp-httplib"
	@echo "  make clean      - Remove build artifacts"
	@echo "  make help       - Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  SERIAL_PORT=$(SERIAL_PORT)"
	@echo "  BAUD_RATE=$(BAUD_RATE)"
	@echo "  PORT=$(PORT) (mock server)"