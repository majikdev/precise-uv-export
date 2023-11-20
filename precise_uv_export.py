bl_info = {
    'name': 'Precise UV Export',
    'description': 'Export pixel-perfect UV layouts as images',
    'author': 'majik',
    'version': (1, 4, 0),
    'blender': (3, 0, 0),
    'category': 'Import-Export'
}

import bpy

from bpy.props import StringProperty, BoolProperty, IntVectorProperty
from bpy_extras.mesh_utils import mesh_linked_uv_islands
from mathutils.geometry import tessellate_polygon
from math import ceil, sqrt, isclose

# Precise UV export operator.

class ExportLayout(bpy.types.Operator):
    """Export pixel-perfect UV layouts as images"""

    bl_idname = 'uv.export_precise_layout'
    bl_label = 'Export Precise Layout'
    bl_options = {'REGISTER', 'UNDO'}

    # Export properties.

    filepath: StringProperty(subtype='FILE_PATH')

    check_existing: BoolProperty(default=True, options={'HIDDEN'})

    size: IntVectorProperty(size=2, min=2, max=8192, default=(16, 16), name='Image Size',
                            description='Dimensions of the exported layout image')

    shade_islands: BoolProperty(default=True, name='Shade Islands',
                                description='Shade separate UV islands differently')

    grid_overlay: BoolProperty(default=True, name='Grid Overlay',
                               description='Overlay a grid on the exported image')

    #add_padding: BoolProperty(default=False, name='Add Padding',
    #                          description='Add padding to UV islands for filtered textures.')

    @classmethod
    def poll(cls, context):
        mesh = context.active_object

        return mesh is not None and mesh.type == 'MESH' and mesh.data.uv_layers

    def invoke(self, context, event):
        self.size = self.get_image_size(context, self.size)
        self.filepath = context.active_object.name.replace('.', '_') + '.png'
        context.window_manager.fileselect_add(self)

        return {'RUNNING_MODAL'}

    def check(self, context):
        self.filepath = bpy.path.ensure_ext(self.filepath, '.png')

        return True

    def execute(self, context):
        mesh = context.active_object
        editing = (mesh.mode == 'EDIT')

        if editing:
            bpy.ops.object.mode_set(mode='OBJECT')

        path = bpy.path.ensure_ext(self.filepath, '.png')
        meshes = list(self.get_meshes(context))
        triangles = list(self.get_triangles(meshes))

        self.export_uv_layout(path, triangles)

        if editing:
            bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

    def export_uv_layout(self, path, triangles):
        def draw_triangle(x1, y1, x2, y2, x3, y3):
            for x in range(x_min, x_max):
                for y in range(y_min, y_max):
                    dist_a = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
                    dist_b = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
                    dist_c = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)

                    negative = dist_a < 0 or dist_b < 0 or dist_c < 0
                    positive = dist_a > 0 or dist_b > 0 or dist_c > 0

                    if not (negative and positive):
                        set_index(x, y)

        def draw_line(x1, y1, x2, y2):
            length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            x_dir, y_dir = (x2 - x1) / length, (y2 - y1) / length
            x, y, dist = int(x1), int(y1), 0

            x_delta = 1e6 if x_dir == 0 else abs(1 / x_dir)
            y_delta = 1e6 if y_dir == 0 else abs(1 / y_dir)

            if x_dir < 0:
                x_step = -1
                x_dist = (x1 - x) * x_delta
            else:
                x_step = 1
                x_dist = (x - x1 + 1) * x_delta

            if y_dir < 0:
                y_step = -1
                y_dist = (y1 - y) * y_delta
            else:
                y_step = 1
                y_dist = (y - y1 + 1) * y_delta

            while dist < length:
                if x_min <= x < x_max and y_min <= y < y_max:
                    set_index(x, y)

                if x_dist < y_dist:
                    x_dist += x_delta
                    x += x_step
                    dist = x_dist - x_delta
                else:
                    y_dist += y_delta
                    y += y_step
                    dist = y_dist - y_delta

        def set_index(x, y):
            offset = y * width + x
            index = island_index + 1
            indices[offset] = index

        def get_colour(position, index):
            if index == 0:
                return 0, 0, 0, 0

            # White normally.
            value = 1

            # Give islands different shades of grey.
            if self.shade_islands and index > 0:
                value = 1 - (index - 1) % 6 * 0.1

            # Overlay a grid over the image.
            if self.grid_overlay and position % 2 == 1:
                value -= 0.04

            return value, value, value, 1

        # Create and populate the index buffer.

        width, height = self.size
        indices = [0] * (width * height)

        for triangle in triangles:
            island_index = triangle.pop()
            v1, v2, v3 = [(x * width, y * height) for x, y in triangle]

            x_min, x_max = max(min(v1[0], v2[0], v3[0]), 0), min(max(v1[0], v2[0], v3[0]), width)
            y_min, y_max = max(min(v1[1], v2[1], v3[1]), 0), min(max(v1[1], v2[1], v3[1]), height)

            x_min = ceil(x_min) if isclose(x_min, ceil(x_min), rel_tol=1e-4) else int(x_min)
            y_min = ceil(y_min) if isclose(y_min, ceil(y_min), rel_tol=1e-4) else int(y_min)
            x_max = int(x_max) if isclose(x_max, int(x_max), rel_tol=1e-4) else ceil(x_max)
            y_max = int(y_max) if isclose(y_max, int(y_max), rel_tol=1e-4) else ceil(y_max)

            draw_triangle(*v1, *v2, *v3)
            draw_line(*v1, *v2)
            draw_line(*v2, *v3)
            draw_line(*v3, *v1)

        # Create and populate the pixel buffer.

        pixels = [0] * (width * height * 4)

        for iy in range(height):
            for ix in range(width):
                index = iy * width + ix
                start = index * 4
                end = start + 4

                pixels[start:end] = get_colour(ix + iy, indices[index])

        # Save the image file.

        try:
            image = bpy.data.images.new('temp', width, height, alpha=True)
            image.filepath, image.pixels = path, pixels
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
                image_w, image_h = image.size

                if image_w and image_h:
                    width, height = image_w, image_h

        return width, height

    @staticmethod
    def get_meshes(context):
        for mesh in {*context.selected_objects, context.active_object}:
            if mesh.type != 'MESH':
                continue

            mesh = mesh.data

            if mesh.uv_layers.active is None:
                continue

            yield mesh

    @staticmethod
    def get_triangles(meshes):
        for mesh in meshes:
            layer = mesh.uv_layers.active.data
            islands = mesh_linked_uv_islands(mesh)

            for index, island in enumerate(islands):
                for poly_index in island:
                    polygon = mesh.polygons[poly_index]

                    start = polygon.loop_start
                    end = start + polygon.loop_total
                    uvs = tuple(uv.uv for uv in layer[start:end])

                    for triangle in tessellate_polygon([uvs]):
                        yield [tuple(uvs[i]) for i in triangle] + [index]

# Register and unregister the add-on.

def menu_entry(self, context):
    self.layout.operator(ExportLayout.bl_idname)

def register():
    bpy.utils.register_class(ExportLayout)
    bpy.types.IMAGE_MT_uvs.append(menu_entry)

def unregister():
    bpy.utils.unregister_class(ExportLayout)
    bpy.types.IMAGE_MT_uvs.remove(menu_entry)

if __name__ == '__main__':
    register()