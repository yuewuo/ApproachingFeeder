"""
MCU Enclosure Generator for Blender
====================================
A parametric 3D printable enclosure for MCU development board and motor driver.

Usage:
    1. Open Blender
    2. Go to Scripting workspace
    3. Open this file and click "Run Script"
    4. Adjust parameters in the PARAMETERS section and re-run

Requirements:
    - Blender 2.80 or later
    - Python 3.x (bundled with Blender)

Author: Auto-generated for ApproachingFeeder project
"""

import bpy
import bmesh
from math import radians, pi
from mathutils import Vector

# =============================================================================
# PARAMETERS - Adjust these values to customize the enclosure
# =============================================================================

# --- Main MCU Board Dimensions (cm) ---
MCU_LENGTH = 8.0  # X dimension
MCU_WIDTH = 3.0  # Y dimension
MCU_HEIGHT = 1.5  # Z dimension (board thickness including components)

# --- Motor Driver Board Dimensions (cm) ---
MOTOR_DRIVER_LENGTH = 3.0  # X dimension
MOTOR_DRIVER_WIDTH = 3.0  # Y dimension
MOTOR_DRIVER_HEIGHT = 2.0  # Z dimension

# --- Enclosure Parameters ---
WALL_THICKNESS = 0.3  # Shell wall thickness
SHELL_PADDING = 0.3  # Internal padding around boards
CORNER_RADIUS = 0.4  # Radius for rounded corners (modern look)
CORNER_SEGMENTS = 8  # Smoothness of rounded corners

# --- RGB LED Hole ---
RGB_LED_DIAMETER = 0.8  # Diameter of the RGB LED viewing hole
RGB_LED_OFFSET_X = 0.0  # X offset from center of MCU board
RGB_LED_OFFSET_Y = 0.0  # Y offset from center of MCU board
RGB_LED_OFFSET_Z = MCU_HEIGHT / 2 + 0.1  # Z offset from board top

# --- Button Hole (on top) ---
BUTTON_HOLE_DIAMETER = 1.2  # Larger than RGB LED hole
BUTTON_HOLE_OFFSET_X = 2.5  # X offset from center of MCU board
BUTTON_HOLE_OFFSET_Y = 0.0  # Y offset from center of MCU board

# --- USB-C Port Cutouts ---
USB_C_WIDTH = 0.9  # USB-C port width
USB_C_HEIGHT = 0.5  # USB-C port height
USB_C_DEPTH = 1.0  # Cutout depth (through wall)
USB_PORT_SPACING = 1.2  # Spacing between the two USB ports
USB_PORT_Z_OFFSET = 1.2  # Z offset from bottom of MCU board

# --- Antenna Hole ---
ANTENNA_HOLE_DIAMETER = 1  # Small hole for antenna cable
ANTENNA_HOLE_OFFSET_X = 3.5  # X offset from center (near edge)
ANTENNA_HOLE_OFFSET_Y = 0.0  # Y offset from center

# --- Motor Cable Port (on +X side, opposite USB ports) ---
MOTOR_CABLE_WIDTH = 1.8  # Double the USB-C width
MOTOR_CABLE_HEIGHT = 0.5  # Same height as USB-C
MOTOR_CABLE_DEPTH = 1.0  # Cutout depth (through wall)
MOTOR_CABLE_Z_OFFSET = 0.2  # Same Z offset as USB ports

# --- Motor Driver Placement ---
MOTOR_DRIVER_GAP = 0.5  # Gap between MCU and motor driver
MOTOR_DRIVER_ORIENTATION = "UPWARD"  # 'UPWARD' or 'FLAT'

# --- Ventilation Cuts (on both Y sides, from bottom) ---
VENT_HEIGHT = 0.2  # Height of the cut from the bottom
VENT_LENGTH_MARGIN = 1.5  # Margin from each end (leave material at corners)

# --- Lid Parameters ---
LID_OVERLAP = 0.2  # How much lid overlaps with base
LID_CLEARANCE = 0.05  # Clearance for lid fitting

# --- Visual/Rendering ---
BOARD_COLOR_MCU = (0.1, 0.3, 0.1, 1.0)  # Dark green for MCU
BOARD_COLOR_MOTOR = (0.3, 0.1, 0.1, 1.0)  # Dark red for motor driver
SHELL_COLOR = (0.8, 0.8, 0.85, 1.0)  # Light gray for shell
RGB_INDICATOR_COLOR = (0.0, 1.0, 0.5, 1.0)  # Cyan for RGB indicator

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def clear_scene():
    """Remove all mesh objects from the scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def create_material(name, color):
    """Create a simple material with given color."""
    mat = bpy.data.materials.new(name=name)
    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
    return mat


def apply_material(obj, material):
    """Apply material to object."""
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def create_rounded_box(name, size_x, size_y, size_z, radius, segments=8):
    """
    Create a box with rounded edges for a modern look.
    Uses bevel modifier for smooth corners.
    """
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = name

    # Scale to desired dimensions
    obj.scale = (size_x, size_y, size_z)
    bpy.ops.object.transform_apply(scale=True)

    # Add bevel modifier for rounded edges
    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
    bevel.width = radius
    bevel.segments = segments
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = radians(30)

    return obj


def create_cylinder_cutout(name, diameter, height, location, rotation=(0, 0, 0)):
    """Create a cylinder for boolean cutting."""
    bpy.ops.mesh.primitive_cylinder_add(
        radius=diameter / 2, depth=height, location=location
    )
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rotation
    return obj


def create_box_cutout(name, size, location, rotation=(0, 0, 0)):
    """Create a box for boolean cutting."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(scale=True)
    return obj


def boolean_difference(target, cutter, apply=True):
    """Perform boolean difference operation."""
    mod = target.modifiers.new(name="Boolean", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter

    if apply:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter)


def boolean_union(target, addition, apply=True):
    """Perform boolean union operation."""
    mod = target.modifiers.new(name="Boolean", type="BOOLEAN")
    mod.operation = "UNION"
    mod.object = addition

    if apply:
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(addition)


# =============================================================================
# BOARD PLACEHOLDER CREATION
# =============================================================================


def create_mcu_board():
    """Create a placeholder box representing the MCU development board."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    mcu = bpy.context.active_object
    mcu.name = "MCU_Board_Placeholder"
    mcu.scale = (MCU_LENGTH, MCU_WIDTH, MCU_HEIGHT)
    bpy.ops.object.transform_apply(scale=True)

    # Position at origin, sitting on door surface (z=0, open bottom design)
    mcu.location = (0, 0, MCU_HEIGHT / 2)

    # Apply material
    mat = create_material("MCU_Material", BOARD_COLOR_MCU)
    apply_material(mcu, mat)

    # Add custom properties for easy adjustment
    mcu["board_type"] = "MCU"
    mcu["dimensions"] = f"{MCU_LENGTH}x{MCU_WIDTH}x{MCU_HEIGHT} cm"

    return mcu


def create_motor_driver_board(mcu_board):
    """Create a placeholder box representing the motor driver board."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    motor = bpy.context.active_object
    motor.name = "Motor_Driver_Placeholder"

    if MOTOR_DRIVER_ORIENTATION == "UPWARD":
        # Board placed vertically (standing up)
        motor.scale = (MOTOR_DRIVER_LENGTH, MOTOR_DRIVER_WIDTH, MOTOR_DRIVER_HEIGHT)
        bpy.ops.object.transform_apply(scale=True)

        # Position next to MCU board (sitting on door surface at z=0)
        motor.location = (
            MCU_LENGTH / 2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH / 2,
            0,
            MOTOR_DRIVER_HEIGHT / 2,
        )
    else:
        # Board placed flat
        motor.scale = (MOTOR_DRIVER_LENGTH, MOTOR_DRIVER_WIDTH, MOTOR_DRIVER_HEIGHT)
        bpy.ops.object.transform_apply(scale=True)

        motor.location = (
            MCU_LENGTH / 2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH / 2,
            0,
            MOTOR_DRIVER_HEIGHT / 2,
        )

    # Apply material
    mat = create_material("Motor_Material", BOARD_COLOR_MOTOR)
    apply_material(motor, mat)

    # Add custom properties
    motor["board_type"] = "Motor Driver"
    motor["dimensions"] = (
        f"{MOTOR_DRIVER_LENGTH}x{MOTOR_DRIVER_WIDTH}x{MOTOR_DRIVER_HEIGHT} cm"
    )
    motor["orientation"] = MOTOR_DRIVER_ORIENTATION

    return motor


def create_rgb_indicator(mcu_board):
    """Create a visual indicator for the RGB LED position."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=RGB_LED_DIAMETER / 2 * 0.8,
        location=(
            mcu_board.location.x + RGB_LED_OFFSET_X,
            mcu_board.location.y + RGB_LED_OFFSET_Y,
            mcu_board.location.z + RGB_LED_OFFSET_Z,
        ),
    )
    rgb = bpy.context.active_object
    rgb.name = "RGB_LED_Indicator"

    # Emissive material for LED effect
    mat = bpy.data.materials.new(name="RGB_LED_Material")
    nodes = mat.node_tree.nodes
    nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 5.0
    nodes["Principled BSDF"].inputs[
        "Emission Color"
    ].default_value = RGB_INDICATOR_COLOR
    nodes["Principled BSDF"].inputs["Base Color"].default_value = RGB_INDICATOR_COLOR
    apply_material(rgb, mat)

    return rgb


# =============================================================================
# ENCLOSURE CREATION
# =============================================================================


def calculate_enclosure_dimensions():
    """Calculate the total enclosure dimensions based on boards and padding."""
    # Total internal space needed
    if MOTOR_DRIVER_ORIENTATION == "UPWARD":
        internal_x = MCU_LENGTH + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH
        internal_y = max(MCU_WIDTH, MOTOR_DRIVER_WIDTH)
        internal_z = max(MCU_HEIGHT, MOTOR_DRIVER_HEIGHT)
    else:
        internal_x = MCU_LENGTH + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH
        internal_y = max(MCU_WIDTH, MOTOR_DRIVER_WIDTH)
        internal_z = MCU_HEIGHT + MOTOR_DRIVER_HEIGHT

    # Add padding
    internal_x += 2 * SHELL_PADDING
    internal_y += 2 * SHELL_PADDING
    internal_z += SHELL_PADDING  # Top padding only (no bottom - open design)

    # External dimensions (add walls) - no bottom wall for open-bottom design
    external_x = internal_x + 2 * WALL_THICKNESS
    external_y = internal_y + 2 * WALL_THICKNESS
    external_z = internal_z  # No bottom wall - open bottom for door mounting

    return {
        "internal": (internal_x, internal_y, internal_z),
        "external": (external_x, external_y, external_z),
    }


def create_enclosure_base(mcu_board):
    """Create the main enclosure base with modern rounded design (open bottom for door mounting)."""
    dims = calculate_enclosure_dimensions()
    ext_x, ext_y, ext_z = dims["external"]
    int_x, int_y, int_z = dims["internal"]

    # Create outer shell
    outer = create_rounded_box(
        "Enclosure_Base_Outer", ext_x, ext_y, ext_z, CORNER_RADIUS, CORNER_SEGMENTS
    )

    # Apply bevel modifier
    bpy.context.view_layer.objects.active = outer
    bpy.ops.object.modifier_apply(modifier="Bevel")

    # Position: center X at the midpoint of total board span
    # MCU spans from -MCU_LENGTH/2 to +MCU_LENGTH/2
    # Motor driver spans from (MCU_LENGTH/2 + MOTOR_DRIVER_GAP) to (MCU_LENGTH/2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH)
    # Total span: -MCU_LENGTH/2 to (MCU_LENGTH/2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH)
    left_edge = -MCU_LENGTH / 2
    right_edge = MCU_LENGTH / 2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH
    center_x = (left_edge + right_edge) / 2
    outer.location = (center_x, 0, ext_z / 2)

    # Create inner cavity (hollow out) - extends through bottom only for open-bottom design
    # The cavity should cut through the bottom but NOT through the top (keep top wall)
    cavity_height = int_z + 0.2  # Internal height plus a bit extra
    inner = create_rounded_box(
        "Enclosure_Base_Inner",
        int_x,
        int_y,
        cavity_height,
        max(CORNER_RADIUS - WALL_THICKNESS, 0.1),
        CORNER_SEGMENTS,
    )
    bpy.context.view_layer.objects.active = inner
    bpy.ops.object.modifier_apply(modifier="Bevel")
    # Position inner cavity: top of cavity at (ext_z - WALL_THICKNESS), extends down through bottom
    # This keeps the top wall intact while opening the bottom
    inner.location = (center_x, 0, (ext_z - WALL_THICKNESS) - cavity_height / 2 + 0.1)

    # Boolean difference to hollow out (creates open bottom)
    boolean_difference(outer, inner)

    outer.name = "Enclosure_Base"
    return outer, dims


def create_usb_cutouts(enclosure, mcu_board, dims):
    """Create cutouts for USB-C ports on the shorter side of the MCU."""
    ext_x, ext_y, ext_z = dims["external"]
    center_x = enclosure.location.x

    # USB ports are on the -X side (shorter side of MCU board)
    usb_x = -MCU_LENGTH / 2 - WALL_THICKNESS - 0.1
    # Z position: boards sit at z=0 (on door surface), USB port offset from board bottom
    usb_z = USB_PORT_Z_OFFSET + USB_C_HEIGHT / 2

    # Create two USB port cutouts
    for i, y_offset in enumerate([-USB_PORT_SPACING / 2, USB_PORT_SPACING / 2]):
        usb_cutout = create_box_cutout(
            f"USB_Cutout_{i+1}",
            (USB_C_DEPTH, USB_C_WIDTH, USB_C_HEIGHT),
            (usb_x, y_offset, usb_z),
        )
        boolean_difference(enclosure, usb_cutout)


def create_motor_cable_cutout(enclosure, dims):
    """Create cutout for motor cables on the +X side (opposite USB ports)."""
    ext_x, ext_y, ext_z = dims["external"]

    # Motor cable port is on the +X side (shorter side near motor driver)
    # Position at the right edge of the enclosure
    right_edge = MCU_LENGTH / 2 + MOTOR_DRIVER_GAP + MOTOR_DRIVER_LENGTH
    cable_x = right_edge + WALL_THICKNESS + 0.1
    cable_z = MOTOR_CABLE_Z_OFFSET + MOTOR_CABLE_HEIGHT / 2

    cable_cutout = create_box_cutout(
        "Motor_Cable_Cutout",
        (MOTOR_CABLE_DEPTH, MOTOR_CABLE_WIDTH, MOTOR_CABLE_HEIGHT),
        (cable_x, 0, cable_z),
    )
    boolean_difference(enclosure, cable_cutout)


def create_rgb_hole(enclosure, mcu_board, dims):
    """Create a hole for viewing the RGB LED."""
    ext_z = dims["external"][2]

    # RGB hole on top of enclosure, centered on MCU board
    rgb_x = mcu_board.location.x + RGB_LED_OFFSET_X
    rgb_y = mcu_board.location.y + RGB_LED_OFFSET_Y
    rgb_z = ext_z + 0.1  # Above the enclosure for clean cut

    rgb_hole = create_cylinder_cutout(
        "RGB_LED_Hole", RGB_LED_DIAMETER, WALL_THICKNESS + 0.5, (rgb_x, rgb_y, rgb_z)
    )
    boolean_difference(enclosure, rgb_hole)


def create_button_hole(enclosure, mcu_board, dims):
    """Create a hole for a button on top of the enclosure."""
    ext_z = dims["external"][2]

    # Button hole on top of enclosure, offset from center of MCU board
    button_x = mcu_board.location.x + BUTTON_HOLE_OFFSET_X
    button_y = mcu_board.location.y + BUTTON_HOLE_OFFSET_Y
    button_z = ext_z + 0.1  # Above the enclosure for clean cut

    button_hole = create_cylinder_cutout(
        "Button_Hole",
        BUTTON_HOLE_DIAMETER,
        WALL_THICKNESS + 0.5,
        (button_x, button_y, button_z),
    )
    boolean_difference(enclosure, button_hole)


def create_antenna_hole(enclosure, mcu_board, dims):
    """Create a small hole for antenna cable."""
    ext_x, ext_y, ext_z = dims["external"]

    # Antenna hole on the side, near the top
    antenna_x = mcu_board.location.x + ANTENNA_HOLE_OFFSET_X
    antenna_y = ext_y / 2 + 0.1  # On the +Y side
    antenna_z = ext_z * 0.5

    antenna_hole = create_cylinder_cutout(
        "Antenna_Hole",
        ANTENNA_HOLE_DIAMETER,
        WALL_THICKNESS + 0.5,
        (antenna_x, antenna_y, antenna_z),
        rotation=(radians(90), 0, 0),
    )
    boolean_difference(enclosure, antenna_hole)


def add_mounting_posts(enclosure, dims):
    """Add mounting posts inside the enclosure for securing boards."""
    ext_z = dims["external"][2]
    post_height = SHELL_PADDING * 0.8
    post_radius = 0.15

    # Corner positions for MCU board
    mcu_corners = [
        (-MCU_LENGTH / 2 + 0.5, -MCU_WIDTH / 2 + 0.3),
        (-MCU_LENGTH / 2 + 0.5, MCU_WIDTH / 2 - 0.3),
        (MCU_LENGTH / 2 - 0.5, -MCU_WIDTH / 2 + 0.3),
        (MCU_LENGTH / 2 - 0.5, MCU_WIDTH / 2 - 0.3),
    ]

    for i, (px, py) in enumerate(mcu_corners):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=post_radius,
            depth=post_height,
            location=(px, py, WALL_THICKNESS + post_height / 2),
        )
        post = bpy.context.active_object
        post.name = f"Mounting_Post_{i+1}"

        # Union with enclosure (keep as separate for now)
        # This allows manual adjustment


def apply_shell_material(enclosure):
    """Apply material to shell components."""
    mat = create_material("Shell_Material", SHELL_COLOR)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.3
    mat.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.1

    apply_material(enclosure, mat)


# =============================================================================
# DECORATIVE ELEMENTS
# =============================================================================


def add_ventilation_cuts(enclosure, dims):
    """Add ventilation by cutting from the bottom on both Y sides.

    This design is 3D print friendly (no overhangs) and allows air to flow
    through the entire bottom of the enclosure.
    """
    ext_x, ext_y, ext_z = dims["external"]
    center_x = enclosure.location.x

    # Ventilation cut dimensions
    vent_depth = WALL_THICKNESS + 0.5  # Cut through the wall
    vent_length = ext_x - 2 * VENT_LENGTH_MARGIN  # Leave material at corners

    # Cut on +Y side (front)
    vent_front = create_box_cutout(
        "Vent_Front",
        (vent_length, vent_depth, VENT_HEIGHT),
        (center_x, ext_y / 2, VENT_HEIGHT / 2),
    )
    boolean_difference(enclosure, vent_front)

    # Cut on -Y side (back)
    vent_back = create_box_cutout(
        "Vent_Back",
        (vent_length, vent_depth, VENT_HEIGHT),
        (center_x, -ext_y / 2, VENT_HEIGHT / 2),
    )
    boolean_difference(enclosure, vent_back)


def add_chamfered_edges(enclosure):
    """Add subtle chamfers for a more refined look."""
    # This is handled by the bevel modifier already applied
    pass


# =============================================================================
# MAIN EXECUTION
# =============================================================================


def main():
    """Main function to generate the complete enclosure assembly."""
    print("=" * 50)
    print("MCU Enclosure Generator")
    print("=" * 50)

    # Clear existing objects
    clear_scene()

    # Create board placeholders
    print("Creating MCU board placeholder...")
    mcu_board = create_mcu_board()

    print("Creating motor driver placeholder...")
    motor_board = create_motor_driver_board(mcu_board)

    print("Creating RGB LED indicator...")
    rgb_indicator = create_rgb_indicator(mcu_board)

    # Create enclosure
    print("Creating enclosure base...")
    enclosure, dims = create_enclosure_base(mcu_board)

    print("Creating USB-C port cutouts...")
    create_usb_cutouts(enclosure, mcu_board, dims)

    print("Creating motor cable port cutout...")
    create_motor_cable_cutout(enclosure, dims)

    print("Creating RGB LED viewing hole...")
    create_rgb_hole(enclosure, mcu_board, dims)

    print("Creating button hole...")
    create_button_hole(enclosure, mcu_board, dims)

    print("Creating antenna hole...")
    create_antenna_hole(enclosure, mcu_board, dims)

    print("Adding ventilation cuts...")
    add_ventilation_cuts(enclosure, dims)

    print("Applying materials...")
    apply_shell_material(enclosure)

    # Organize objects into collections
    print("Organizing scene...")

    # Create collections
    if "Boards" not in bpy.data.collections:
        boards_col = bpy.data.collections.new("Boards")
        bpy.context.scene.collection.children.link(boards_col)
    else:
        boards_col = bpy.data.collections["Boards"]

    if "Enclosure" not in bpy.data.collections:
        enclosure_col = bpy.data.collections.new("Enclosure")
        bpy.context.scene.collection.children.link(enclosure_col)
    else:
        enclosure_col = bpy.data.collections["Enclosure"]

    # Move objects to collections
    for obj in [mcu_board, motor_board, rgb_indicator]:
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)
        if obj.name not in boards_col.objects:
            boards_col.objects.link(obj)

    # Set up camera and lighting for nice render
    setup_scene_lighting()

    print("=" * 50)
    print("Enclosure generation complete!")
    print(
        f"External dimensions: {dims['external'][0]:.1f} x {dims['external'][1]:.1f} x {dims['external'][2]:.1f} cm"
    )
    print("=" * 50)
    print("\nTips:")
    print(
        "- Adjust board positions by selecting 'MCU_Board_Placeholder' or 'Motor_Driver_Placeholder'"
    )
    print("- Modify parameters at the top of the script and re-run")
    print("- Hide 'Boards' collection to see only the enclosure")
    print("- Export to STL: File > Export > STL")


def setup_scene_lighting():
    """Set up basic lighting for visualization."""
    # Add a sun light
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    sun = bpy.context.active_object
    sun.name = "Sun_Light"
    sun.data.energy = 3

    # Add ambient light
    bpy.ops.object.light_add(type="AREA", location=(-3, 3, 8))
    area = bpy.context.active_object
    area.name = "Fill_Light"
    area.data.energy = 100
    area.data.size = 5

    # Position camera
    bpy.ops.object.camera_add(location=(15, -15, 12))
    camera = bpy.context.active_object
    camera.name = "Main_Camera"
    camera.rotation_euler = (radians(60), 0, radians(45))
    bpy.context.scene.camera = camera


# Run the script
if __name__ == "__main__":
    main()
