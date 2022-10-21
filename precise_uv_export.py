bl_info = {
    "name": "Precise UV Export",
    "author": "majik",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "description": "Export a pixel-perfect UV layout as an image",
    "category": "Import-Export"
}

# TODO: Add the ability to shade separate UV islands differently.
# TODO: Add the ability to shade overlapping UVs a certain colour.
# TODO: Clean up the horrendous pixel drawing code.

import bpy, os

from bpy.props import StringProperty, BoolProperty, IntVectorProperty
from mathutils.geometry import tessellate_polygon
from math import ceil, sqrt

# Precise UV layout export operator.

class ExportLayout(bpy.types.Operator):
    """Export a pixel-perfect UV layout as an image"""

    bl_idname = "uv.export_precise_layout"
    bl_label = "Export Precise Layout"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    check_existing: BoolProperty(default=True, options={"HIDDEN"})

    size: IntVectorProperty(size=2, min=2, max=8192, default=(16, 16), name="Image Size",
                            description="Dimensions of the exported layout image")

    @classmethod
    def poll(cls, context):
        mesh = context.active_object

        return mesh is not None and mesh.type == "MESH" and mesh.data.uv_layers

    def invoke(self, context, event):
        self.size = self.get_image_size(context)
        self.filepath = f"{context.active_object.name.replace('.', '_')}.png"
        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def check(self, context):
        if self.filepath.endswith(".png"):
            self.filepath = self.filepath[:-4]

        self.filepath = bpy.path.ensure_ext(self.filepath, ".png")

        return True

    def execute(self, context):
        mesh = context.active_object
        edit_mode = mesh.mode == "EDIT"

        if edit_mode:
            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)

        path = bpy.path.ensure_ext(self.filepath, ".png")
        meshes = list(self.get_meshes_to_export(context))
        triangles = list(self.get_mesh_triangles(meshes))
        self.export_uv_layout(path, triangles)

        if edit_mode:
            bpy.ops.object.mode_set(mode="EDIT", toggle=False)

        return {"FINISHED"}

    def export_uv_layout(self, path, triangles):
        def draw_line(x_begin, y_begin, x_end, y_end):
            length = sqrt(int(x_end - x_begin) ** 2 + int(y_end - y_begin) ** 2)
            x_dir, y_dir = (x_end - x_begin) / length, (y_end - y_begin) / length
            x, y = int(x_begin), int(y_begin)

            x_delta = 1e30 if x_dir == 0 else abs(1 / x_dir)
            y_delta = 1e30 if y_dir == 0 else abs(1 / y_dir)

            if x_dir < 0:
                x_step = -1
                x_dist = (x_begin - x) * x_delta
            else:
                x_step = 1
                x_dist = (x - x_begin + 1) * x_delta

            if y_dir < 0:
                y_step = -1
                y_dist = (y_begin - y) * y_delta
            else:
                y_step = 1
                y_dist = (y - y_begin + 1) * y_delta

            while True:
                if x < x_max and y < y_max:
                    offset = (y * width + x) * 4
                    pixels[offset:offset + 4] = [1, 1, 1, 1]

                if x_dist < y_dist:
                    x_dist += x_delta
                    x += x_step
                    dist = x_dist - x_delta
                else:
                    y_dist += y_delta
                    y += y_step
                    dist = y_dist - y_delta

                if dist >= length:
                    break

        def draw_inside(ax, ay, bx, by, cx, cy, px, py):
            dist1 = (px - bx) * (ay - by) - (ax - bx) * (py - by)
            dist2 = (px - cx) * (by - cy) - (bx - cx) * (py - cy)
            dist3 = (px - ax) * (cy - ay) - (cx - ax) * (py - ay)

            has_negative = dist1 < 0 or dist2 < 0 or dist3 < 0
            has_positive = dist1 > 0 or dist2 > 0 or dist3 > 0

            if not (has_negative and has_positive):
                offset = (y * width + x) * 4
                pixels[offset:offset + 4] = [1, 1, 1, 1]

        width, height = self.size
        pixels = [0, 0, 0, 0] * width * height

        for triangle in triangles:
            v1, v2, v3 = [(x * width, y * height) for x, y in triangle]
            x_min, x_max = int(min(v1[0], v2[0], v3[0])), ceil(max(v1[0], v2[0], v3[0]))
            y_min, y_max = int(min(v1[1], v2[1], v3[1])), ceil(max(v1[1], v2[1], v3[1]))

            draw_line(v1[0], v1[1], v2[0], v2[1])
            draw_line(v2[0], v2[1], v3[0], v3[1])
            draw_line(v3[0], v3[1], v1[0], v1[1])

            for x in range(x_min, x_max):
                for y in range(y_min, y_max):
                    draw_inside(v1[0], v1[1], v2[0], v2[1], v3[0], v3[1], x, y)

        try:
            image = bpy.data.images.new("temp", width, height, alpha=True)
            image.filepath = path
            image.pixels = pixels
            image.save()
            bpy.data.images.remove(image)

        except:
            pass

    def get_image_size(self, context):
        width, height = self.size

        if isinstance(context.space_data, bpy.types.SpaceImageEditor):
            image = context.space_data.image

            if image is not None:
                ctx_width, ctx_height = context.space_data.image.size

                if ctx_width and ctx_height:
                    width, height = ctx_width, ctx_height

        return width, height

    @staticmethod
    def get_meshes_to_export(context):
        for mesh in {*context.selected_objects, context.active_object}:
            if mesh.type != "MESH":
                continue

            mesh = mesh.data

            if mesh.uv_layers.active is None:
                continue

            yield mesh

    @staticmethod
    def get_mesh_triangles(meshes):
        for mesh in meshes:
            layer = mesh.uv_layers.active.data

            for polygon in mesh.polygons:
                start = polygon.loop_start
                end = start + polygon.loop_total
                uvs = tuple(uv.uv for uv in layer[start:end])

                for triangle in tessellate_polygon([uvs]):
                    yield [tuple(uvs[index]) for index in triangle]

# Register and unregister the addon.

def menu_entry(self, context):
    self.layout.operator(ExportLayout.bl_idname)

def register():
    bpy.utils.register_class(ExportLayout)
    bpy.types.IMAGE_MT_uvs.append(menu_entry)

def unregister():
    bpy.utils.unregister_class(ExportLayout)
    bpy.types.IMAGE_MT_uvs.remove(menu_entry)

if __name__ == "__main__":
    register()