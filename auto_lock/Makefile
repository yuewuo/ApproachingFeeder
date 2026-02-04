# Auto Lock Mock Server Makefile

CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -O2 -I.
LDFLAGS = -pthread

TARGET = mock_server
SOURCES = mock/mock_main.cpp
HEADERS = lock_controller.hpp mock/mock_stepper.hpp mock/httplib.h

PORT ?= 8080

.PHONY: all clean run deps html arduino

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

# Compile Arduino sketch (verify only)
arduino:
	arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc auto_lock.ino

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
