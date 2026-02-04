# Makefile for MCU Enclosure 3D Models
# Generates and exports STL files using Blender

# Blender executable (adjust if not in PATH)
BLENDER := /Applications/Blender.app/Contents/MacOS/Blender

# Output directory for STL files
OUTPUT_DIR := output

# Source scripts
SCRIPT := mcu_enclosure.py
EXPORT_SCRIPT := export_stl.py

# Output files
STL_BASE := $(OUTPUT_DIR)/enclosure_base.stl
STL_LID := $(OUTPUT_DIR)/enclosure_lid.stl
BLEND_FILE := $(OUTPUT_DIR)/enclosure.blend

# Scale factor: cm to mm (for 3D printing)
SCALE := 10

.PHONY: all clean preview help base lid

all: $(STL_BASE) $(STL_LID)
	@echo "✅ All STL files generated in $(OUTPUT_DIR)/"

$(OUTPUT_DIR):
	@mkdir -p $(OUTPUT_DIR)

# Generate both STL files
$(STL_BASE) $(STL_LID): $(SCRIPT) $(EXPORT_SCRIPT) | $(OUTPUT_DIR)
	@echo "🔧 Generating enclosure models..."
	@$(BLENDER) --background --python $(SCRIPT) --python $(EXPORT_SCRIPT) -- $(OUTPUT_DIR) $(SCALE)
	@echo "📦 STL files ready for 3D printing (scale: $(SCALE)x = mm)"

# Export only the base
base: $(SCRIPT) $(EXPORT_SCRIPT) | $(OUTPUT_DIR)
	@echo "🔧 Generating enclosure base..."
	@$(BLENDER) --background --python $(SCRIPT) --python $(EXPORT_SCRIPT) -- $(OUTPUT_DIR) $(SCALE)

# Export only the lid
lid: $(SCRIPT) $(EXPORT_SCRIPT) | $(OUTPUT_DIR)
	@echo "🔧 Generating enclosure lid..."
	@$(BLENDER) --background --python $(SCRIPT) --python $(EXPORT_SCRIPT) -- $(OUTPUT_DIR) $(SCALE)

# Open in Blender for preview/editing
preview: $(SCRIPT)
	@echo "🖥️  Opening in Blender..."
	@$(BLENDER) --python $(SCRIPT)

# Save blend file without STL export
blend: $(SCRIPT) | $(OUTPUT_DIR)
	@echo "💾 Saving Blender file..."
	@$(BLENDER) --background --python $(SCRIPT) --python-expr "\
import bpy; \
bpy.ops.wm.save_as_mainfile(filepath='$(BLEND_FILE)'); \
print('✅ Saved $(BLEND_FILE)'); \
"

# Clean generated files
clean:
	@echo "🧹 Cleaning output files..."
	@rm -rf $(OUTPUT_DIR)
	@echo "✅ Clean complete"

# Help
help:
	@echo "MCU Enclosure 3D Model Generator"
	@echo "================================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all      - Generate all STL files (default)"
	@echo "  base     - Generate only the enclosure base STL"
	@echo "  lid      - Generate only the enclosure lid STL"
	@echo "  blend    - Save Blender project file only"
	@echo "  preview  - Open in Blender GUI for editing"
	@echo "  clean    - Remove all generated files"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Output files are saved to: $(OUTPUT_DIR)/"
	@echo "  - enclosure_base.stl"
	@echo "  - enclosure_lid.stl"
	@echo "  - enclosure.blend"
	@echo ""
	@echo "Scale factor: $(SCALE)x (cm → mm for 3D printing)"
