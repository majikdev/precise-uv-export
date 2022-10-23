bl_info = {
    "name": "Precise UV Export",
    "description": "Export pixel-perfect UV layouts as images",
    "author": "majik",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "category": "Import-Export"
}

import bpy, os

from bpy.props import StringProperty, BoolProperty, IntVectorProperty
from mathutils.geometry import tessellate_polygon
from math import ceil, sqrt, isclose

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

    shade_islands: BoolProperty(default=True, name="Shade Islands",
                                description="Shade separate UV islands differently")

    @classmethod
    def poll(cls, context):
        mesh = context.active_object

        return mesh is not None and mesh.type == "MESH" and mesh.data.uv_layers

    def invoke(self, context, event):
        self.size = self.get_image_size(context, self.size)
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
        def draw_line(ax, ay, bx, by):
            length = sqrt(int(bx - ax) ** 2 + int(by - ay) ** 2)

            if length == 0:
                return

            x_dir, y_dir = (bx - ax) / length, (by - ay) / length
            x, y = int(ax), int(ay)

            x_delta = 1e30 if x_dir == 0 else abs(1 / x_dir)
            y_delta = 1e30 if y_dir == 0 else abs(1 / y_dir)

            if x_dir < 0:
                x_step = -1
                x_dist = (ax - x) * x_delta
            else:
                x_step = 1
                x_dist = (x - ax + 1) * x_delta

            if y_dir < 0:
                y_step = -1
                y_dist = (ay - y) * y_delta
            else:
                y_step = 1
                y_dist = (y - ay + 1) * y_delta

            while True:
                if x_min <= x < x_max and y_min <= y < y_max:
                    offset = (y * width + x) * 4
                    pixels[offset:offset + 4] = get_colour(index)

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

        def fill_poly(ax, ay, bx, by, cx, cy):
            for x in range(x_min, x_max):
                for y in range(y_min, y_max):
                    dist_a = (x - bx) * (ay - by) - (ax - bx) * (y - by)
                    dist_b = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
                    dist_c = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)

                    negative = dist_a < 0 or dist_b < 0 or dist_c < 0
                    positive = dist_a > 0 or dist_b > 0 or dist_c > 0

                    if not (negative and positive):
                        offset = (y * width + x) * 4
                        pixels[offset:offset + 4] = get_colour(index)

        def get_colour(index):
            if not self.shade_islands:
                return 1, 1, 1, 1

            value = 1 - (index % 6) * 0.1

            return value, value, value, 1

        width, height = self.size
        pixels = [0, 0, 0, 0] * width * height

        for triangle in triangles:
            index = triangle.pop()
            v1, v2, v3 = [(x * width, y * height) for x, y in triangle]
            
            x_min, x_max = min(v1[0], v2[0], v3[0]), ceil(max(v1[0], v2[0], v3[0]))
            y_min, y_max = min(v1[1], v2[1], v3[1]), ceil(max(v1[1], v2[1], v3[1]))

            # Fixes an issue caused by floating-point precision.
            x_min = ceil(x_min) if isclose(x_min, ceil(x_min), rel_tol=1e-06) else int(x_min)
            y_min = ceil(y_min) if isclose(y_min, ceil(y_min), rel_tol=1e-06) else int(y_min)

            draw_line(v1[0], v1[1], v2[0], v2[1])
            draw_line(v2[0], v2[1], v3[0], v3[1])
            draw_line(v3[0], v3[1], v1[0], v1[1])
            
            fill_poly(v1[0], v1[1], v2[0], v2[1], v3[0], v3[1])

        try:
            image = bpy.data.images.new("temp", width, height, alpha=True)
            image.filepath = path
            image.pixels = pixels
            image.save()
            bpy.data.images.remove(image)

        except:
            pass

    @staticmethod
    def get_image_size(context, default):
        width, height = default

        if isinstance(context.space_data, bpy.types.SpaceImageEditor):
            image = context.space_data.image

            if image is not None:
                image_w, image_h = context.space_data.image.size

                if image_w and image_h:
                    width, height = image_w, image_h

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
            """islands = []

            for v in layer:
                if v not in [uv for isle in islands for uv in isle]:
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.uv.select_all(action="DESELECT")
                    bpy.ops.object.mode_set(mode="OBJECT")

                    v.select = True

                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.uv.select_linked()
                    bpy.ops.object.mode_set(mode="OBJECT")

                    if island := [uv for uv in layer if uv.select]:
                        islands.append(island)

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.uv.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT")"""

            for polygon in mesh.polygons:
                start = polygon.loop_start
                end = start + polygon.loop_total
                uvs = tuple(uv.uv for uv in layer[start:end])
                island_index = 0

                """for i, island in enumerate(islands):
                    if layer[start] in island:
                        island_index = i"""

                for triangle in tessellate_polygon([uvs]):
                    yield [tuple(uvs[index]) for index in triangle] + [island_index]

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