"""
STL Export Script for MCU Enclosure
Run this after mcu_enclosure.py to export STL files.

Usage:
    blender --background --python mcu_enclosure.py --python export_stl.py -- [output_dir] [scale]
"""

import bpy
import os
import sys


def get_stl_export_func():
    """Get the appropriate STL export function for the Blender version."""
    # Blender 4.0+ uses io_mesh_stl addon or bpy.ops.wm.stl_export
    # Blender 3.x uses bpy.ops.export_mesh.stl
    if hasattr(bpy.ops.wm, "stl_export"):
        return "wm"
    elif hasattr(bpy.ops.export_mesh, "stl"):
        return "export_mesh"
    else:
        # Try to enable the addon
        try:
            bpy.ops.preferences.addon_enable(module="io_mesh_stl")
            if hasattr(bpy.ops.export_mesh, "stl"):
                return "export_mesh"
        except:
            pass
    return None


def export_stl(filepath, use_selection=True):
    """Export to STL using available method."""
    method = get_stl_export_func()

    if method == "wm":
        # Blender 4.0+ method
        bpy.ops.wm.stl_export(
            filepath=filepath, export_selected_objects=use_selection, ascii_format=False
        )
    elif method == "export_mesh":
        # Blender 3.x method
        bpy.ops.export_mesh.stl(
            filepath=filepath, use_selection=use_selection, ascii=False
        )
    else:
        raise RuntimeError("No STL export method available")


def export_stl_files(output_dir="output", scale=10):
    """Export enclosure parts to STL files."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    parts = [
        ("Enclosure_Base", "enclosure_base.stl"),
        ("Enclosure_Lid", "enclosure_lid.stl"),
    ]

    for obj_name, filename in parts:
        if obj_name not in bpy.data.objects:
            print(f"⚠️  Object '{obj_name}' not found, skipping...")
            continue

        obj = bpy.data.objects[obj_name]

        # Deselect all
        bpy.ops.object.select_all(action="DESELECT")

        # Select and activate target object
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Scale for mm output
        original_scale = obj.scale.copy()
        obj.scale = (scale, scale, scale)
        bpy.ops.object.transform_apply(scale=True)

        # Export
        filepath = os.path.join(output_dir, filename)
        export_stl(filepath, use_selection=True)
        print(f"✅ Exported {filename} ({scale}x scale)")

        # Restore scale (divide by scale factor)
        obj.scale = (1 / scale, 1 / scale, 1 / scale)
        bpy.ops.object.transform_apply(scale=True)

    # Save blend file
    blend_path = os.path.join(output_dir, "enclosure.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"✅ Saved {blend_path}")


if __name__ == "__main__":
    # Parse arguments after "--"
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    output_dir = argv[0] if len(argv) > 0 else "output"
    scale = int(argv[1]) if len(argv) > 1 else 10

    export_stl_files(output_dir, scale)
