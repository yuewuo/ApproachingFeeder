# MCU Enclosure 3D Design

This folder contains Blender Python scripts for generating 3D printable enclosures for the auto_lock MCU system.

## Files

- `mcu_enclosure.py` - Main parametric enclosure generator

## Requirements

- Blender 2.80 or later (tested with 3.x)
- No additional Python packages required (uses Blender's built-in modules)

## Usage

### Method 1: Blender GUI

1. Open Blender
2. Switch to the **Scripting** workspace (top menu tabs)
3. Click **Open** and select `mcu_enclosure.py`
4. Click **Run Script** (or press Alt+P)

### Method 2: Command Line

```bash
# Generate and open in Blender
blender --python mcu_enclosure.py

# Generate and save to file (headless)
blender --background --python mcu_enclosure.py -- --output enclosure.blend
```

## Parameters

All customizable parameters are at the top of `mcu_enclosure.py`:

### Board Dimensions (cm)
| Parameter             | Default | Description              |
| --------------------- | ------- | ------------------------ |
| `MCU_LENGTH`          | 8.0     | MCU board X dimension    |
| `MCU_WIDTH`           | 3.0     | MCU board Y dimension    |
| `MCU_HEIGHT`          | 2.0     | MCU board Z dimension    |
| `MOTOR_DRIVER_LENGTH` | 3.0     | Motor driver X dimension |
| `MOTOR_DRIVER_WIDTH`  | 3.0     | Motor driver Y dimension |
| `MOTOR_DRIVER_HEIGHT` | 2.0     | Motor driver Z dimension |

### Enclosure Parameters
| Parameter         | Default | Description                    |
| ----------------- | ------- | ------------------------------ |
| `WALL_THICKNESS`  | 0.3     | Shell wall thickness           |
| `SHELL_PADDING`   | 0.3     | Internal padding around boards |
| `CORNER_RADIUS`   | 0.4     | Rounded corner radius          |
| `CORNER_SEGMENTS` | 8       | Smoothness of corners          |

### Feature Cutouts
| Parameter               | Default | Description                   |
| ----------------------- | ------- | ----------------------------- |
| `RGB_LED_DIAMETER`      | 0.8     | RGB LED viewing hole diameter |
| `USB_C_WIDTH`           | 0.9     | USB-C port cutout width       |
| `USB_C_HEIGHT`          | 0.35    | USB-C port cutout height      |
| `USB_PORT_SPACING`      | 1.2     | Spacing between USB ports     |
| `ANTENNA_HOLE_DIAMETER` | 0.3     | Antenna cable hole diameter   |

### Motor Driver Placement
| Parameter                  | Default  | Description                      |
| -------------------------- | -------- | -------------------------------- |
| `MOTOR_DRIVER_GAP`         | 0.5      | Gap between MCU and motor driver |
| `MOTOR_DRIVER_ORIENTATION` | 'UPWARD' | 'UPWARD' or 'FLAT'               |

## Generated Objects

The script creates the following objects organized into collections:

### Boards Collection
- **MCU_Board_Placeholder** - Green box representing the main MCU board
- **Motor_Driver_Placeholder** - Red box representing the motor driver
- **RGB_LED_Indicator** - Glowing sphere showing LED position

### Enclosure Collection
- **Enclosure_Base** - Main shell body with cutouts
- **Enclosure_Lid** - Matching lid with RGB hole

## Customization Workflow

1. Run the script with default parameters
2. Check if boards fit by toggling visibility
3. Adjust parameters as needed:
   - Board dimensions if your boards differ
   - Cutout positions for USB/LED/antenna
   - Wall thickness for strength vs. material
4. Re-run the script to regenerate

## Manual Adjustments

After generating, you can manually adjust:

1. **Board Positions**: Select placeholders and move them
2. **Hole Positions**: Modify the offset parameters
3. **Enclosure Shape**: Edit the mesh directly in Edit mode

## Exporting for 3D Printing

1. Select the part to export (Base or Lid)
2. File > Export > STL (.stl)
3. Recommended settings:
   - Scale: 10 (converts cm to mm)
   - Apply Modifiers: Yes
   - Selection Only: Yes

## Design Features

- **Modern rounded corners** - Achieved with bevel modifiers
- **Ventilation slots** - For thermal management
- **Snap-fit lid** - With overlap lip design
- **USB-C cutouts** - For cable connectivity
- **RGB LED window** - Circular viewing hole
- **Antenna port** - Small hole for external antenna

## Tips

- Use a 0.4mm nozzle for best detail on ventilation slots
- Print base upside-down for cleaner USB port edges
- Consider adding supports for the lid overhang
- Test fit with placeholder objects before final print
