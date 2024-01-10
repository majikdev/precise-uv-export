import bpy
from bpy.props import StringProperty, BoolProperty, IntVectorProperty
from bpy_extras.mesh_utils import mesh_linked_uv_islands
from mathutils.geometry import tessellate_polygon
from math import ceil, sqrt, isclose

bl_info = {
    'name': 'Precise UV Export',
    'description': 'Export pixel-perfect UV layouts as images',
    'author': 'majik',
    'version': (1, 4, 0),
    'blender': (3, 0, 0),
    'category': 'Import-Export'
}

# Precise UV export operator.

class ExportLayout(bpy.types.Operator):
    """Export pixel-perfect UV layouts as images"""

    bl_idname = 'uv.export_precise_layout'
    bl_label = 'Export Precise Layout'
    bl_options = {'REGISTER', 'UNDO'}

    # Export properties.

    filepath: StringProperty(subtype='FILE_PATH')

    check_existing: BoolProperty(default=True, options={'HIDDEN'})

    size: IntVectorProperty(size=2, min=2, max=4096, default=(16, 16), name='Image Size',
                            description='Dimensions of the exported layout image')

    shade_islands: BoolProperty(default=True, name='Shade Islands',
                                description='Shade separate UV islands differently')

    grid_overlay: BoolProperty(default=True, name='Grid Overlay',
                               description='Overlay a grid on the exported image')

    outline_islands: BoolProperty(default=True, name='Outline Islands',
                                  description='Draw an outline around every island')

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
        self.width, self.height = self.size

        self.indices = [-1] * (self.width * self.height)

        for triangle in triangles:
            island_index = triangle.pop()
            v1, v2, v3 = [(x * self.width, y * self.height) for x, y in triangle]

            x_min, x_max = max(min(v1[0], v2[0], v3[0]), 0), min(max(v1[0], v2[0], v3[0]), self.width)
            y_min, y_max = max(min(v1[1], v2[1], v3[1]), 0), min(max(v1[1], v2[1], v3[1]), self.height)

            x_min = ceil(x_min) if isclose(x_min, ceil(x_min), rel_tol=1e-4) else int(x_min)
            y_min = ceil(y_min) if isclose(y_min, ceil(y_min), rel_tol=1e-4) else int(y_min)
            x_max = int(x_max) if isclose(x_max, int(x_max), rel_tol=1e-4) else ceil(x_max)
            y_max = int(y_max) if isclose(y_max, int(y_max), rel_tol=1e-4) else ceil(y_max)

            self.draw_triangle(*v1, *v2, *v3, x_min, x_max, y_min, y_max, island_index)
            self.draw_line(*v1, *v2, x_min, x_max, y_min, y_max, island_index)
            self.draw_line(*v2, *v3, x_min, x_max, y_min, y_max, island_index)
            self.draw_line(*v3, *v1, x_min, x_max, y_min, y_max, island_index)

        # Create and save the image.

        pixels = [i for y in range(self.height) for x in range(self.width) for i in self.get_colour(x, y)]

        try:
            image = bpy.data.images.new('temp', self.width, self.height, alpha=True)
            image.filepath = path
            image.pixels = pixels
            image.save()

            bpy.data.images.remove(image)
        except:
            pass

    def draw_triangle(self, x1, y1, x2, y2, x3, y3, x_min, x_max, y_min, y_max, island):
        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                dist_a = (x - x2) * (y1 - y2) - (x1 - x2) * (y - y2)
                dist_b = (x - x3) * (y2 - y3) - (x2 - x3) * (y - y3)
                dist_c = (x - x1) * (y3 - y1) - (x3 - x1) * (y - y1)

                negative = dist_a < 0 or dist_b < 0 or dist_c < 0
                positive = dist_a > 0 or dist_b > 0 or dist_c > 0

                if not (negative and positive):
                    self.indices[y * self.width + x] = island

    def draw_line(self, x1, y1, x2, y2, x_min, x_max, y_min, y_max, island):
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
                self.indices[y * self.width + x] = island

            if x_dist < y_dist:
                x_dist += x_delta
                x += x_step
                dist = x_dist - x_delta
            else:
                y_dist += y_delta
                y += y_step
                dist = y_dist - y_delta

    def get_colour(self, x, y):
        index = self.indices[y * self.width + x]

        if index != -1:
            value = 1

            if self.shade_islands:
                value -= (index % 6) * 0.1

            if self.grid_overlay and (x + y) % 2 == 1:
                value -= 0.04

            return value, value, value, 1

        if self.outline_islands:
            has_l = x > 0
            has_r = x < self.width - 1
            has_t = y > 0
            has_b = y < self.height - 1

            neighbours  = has_l and self.indices[y * self.width + (x - 1)] >= 0
            neighbours += has_r and self.indices[y * self.width + (x + 1)] >= 0
            neighbours += has_t and self.indices[(y - 1) * self.width + x] >= 0
            neighbours += has_b and self.indices[(y + 1) * self.width + x] >= 0
            neighbours += has_l and has_t and self.indices[(y - 1) * self.width + (x - 1)] >= 0
            neighbours += has_r and has_t and self.indices[(y - 1) * self.width + (x + 1)] >= 0
            neighbours += has_l and has_b and self.indices[(y + 1) * self.width + (x - 1)] >= 0
            neighbours += has_r and has_b and self.indices[(y + 1) * self.width + (x + 1)] >= 0

            if neighbours > 0:
                return 0, 0, 0, 1

        return 0, 0, 0, 0

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

            if mesh.data.uv_layers.active is None:
                continue

            yield mesh.data

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
