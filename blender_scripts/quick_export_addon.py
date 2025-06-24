bl_info = {
    "name": "Quick GLB Export",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "category": "Import-Export",
}

import bpy
import os
from datetime import datetime

class GLB_OT_QuickExport(bpy.types.Operator):
    bl_idname = "export.quick_glb"
    bl_label = "Export GLB"
    
    def execute(self, context):
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        filename = f"model_{timestamp}.glb"
        out_dir = "/Users/shubhamjena/Desktop/Personal projects/blend-to-threejs/blender_exports"
        output_path = os.path.join(out_dir, filename)
        print("Exporting to:", output_path)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format="GLB",
            export_apply=True
        )
        print("Export successful.")
        
        self.report({'INFO'}, f"Exported: {filename}")
        return {'FINISHED'}

class GLB_PT_Panel(bpy.types.Panel):
    bl_label = "GLB Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "GLB"
    
    def draw(self, context):
        self.layout.operator("export.quick_glb", text="Export GLB", icon='EXPORT')

def register():
    bpy.utils.register_class(GLB_OT_QuickExport)
    bpy.utils.register_class(GLB_PT_Panel)

def unregister():
    bpy.utils.unregister_class(GLB_OT_QuickExport)
    bpy.utils.unregister_class(GLB_PT_Panel)

if __name__ == "__main__":
    register()