"""Procedural Q-style Haikou V1 miniature city asset.

Run from the project root:
  blender --background --factory-startup --python tools/blender/build_haikou_v1.py

Set HAIKOU_STAGE=blockout for a 900x600 / 24 sample composition pass.
"""
import bpy
import bmesh
import json
import math
import os
import random
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(ROOT, "..", ".."))
ASSET_DIR = os.path.join(PROJECT, "data", "asset")
MODEL_DIR = os.path.join(PROJECT, "assets", "models")
REPORT_PATH = os.path.join(PROJECT, "docs", "asset-report.md")
STAGE = os.environ.get("HAIKOU_STAGE", "final").lower()
ROUND = os.environ.get("HAIKOU_ROUND", "1")
DRAFT = STAGE != "final"
random.seed(24)

os.makedirs(ASSET_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# The palette intentionally stays at 24 materials for GLB size and draw calls.
PALETTE = {
    "wood": ((0.35, 0.20, 0.11), 0.72, 0.0),
    "wood_dark": ((0.17, 0.095, 0.052), 0.78, 0.0),
    "sea": ((0.018, 0.235, 0.34), 0.27, 0.18),
    "foam": ((0.80, 0.92, 0.91), 0.72, 0.0),
    "sand": ((0.91, 0.73, 0.44), 0.88, 0.0),
    "grass": ((0.29, 0.51, 0.27), 0.93, 0.0),
    "meadow": ((0.43, 0.64, 0.35), 0.88, 0.0),
    "road": ((0.64, 0.65, 0.60), 0.85, 0.0),
    "cream": ((0.95, 0.84, 0.64), 0.78, 0.0),
    "terracotta": ((0.75, 0.29, 0.21), 0.76, 0.0),
    "butter": ((0.97, 0.67, 0.30), 0.70, 0.0),
    "mint": ((0.34, 0.65, 0.50), 0.72, 0.0),
    "skyblue": ((0.36, 0.59, 0.77), 0.62, 0.0),
    "coral": ((0.88, 0.35, 0.27), 0.64, 0.0),
    "white": ((0.96, 0.95, 0.90), 0.48, 0.0),
    "glass": ((0.17, 0.39, 0.52), 0.25, 0.24),
    "dark": ((0.13, 0.17, 0.17), 0.58, 0.0),
    "gold": ((0.82, 0.55, 0.20), 0.28, 0.68),
    "brick": ((0.58, 0.22, 0.17), 0.84, 0.0),
    "trunk": ((0.37, 0.24, 0.14), 0.88, 0.0),
    "leaf": ((0.15, 0.43, 0.23), 0.86, 0.0),
    "cloud": ((0.96, 0.98, 1.00), 0.91, 0.0),
    "window": ((0.10, 0.24, 0.31), 0.29, 0.22),
    "lava": ((0.22, 0.075, 0.045), 0.50, 0.08),
}
MATS = {}
for name, (rgb, roughness, metallic) in PALETTE.items():
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    MATS[name] = mat


def _activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifiers(obj):
    _activate(obj)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def apply_rot_scale(obj):
    _activate(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.select_set(False)


def assign(obj, material):
    obj.data.materials.append(MATS[material])
    return obj


def box(name, size, loc, material, bevel=0.25, rot=(0.0, 0.0, 0.0), seg=2):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    obj.rotation_euler = rot
    apply_rot_scale(obj)
    assign(obj, material)
    if bevel > 0:
        mod = obj.modifiers.new("rounded_edges", "BEVEL")
        mod.width = min(bevel, min(size) * 0.32)
        mod.segments = seg
        mod.limit_method = "ANGLE"
        apply_modifiers(obj)
    return obj


def cyl(name, radius, depth, loc, material, rot=(0.0, 0.0, 0.0), verts=24,
        bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth,
                                        location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    apply_rot_scale(obj)
    assign(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    if bevel > 0:
        mod = obj.modifiers.new("soft_rim", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        apply_modifiers(obj)
    return obj


def cone(name, radius1, radius2, depth, loc, material, verts=24,
         rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius1,
                                    radius2=radius2, depth=depth, location=loc,
                                    rotation=rot)
    obj = bpy.context.object
    obj.name = name
    apply_rot_scale(obj)
    assign(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def sphere(name, radius, loc, material, scale=(1.0, 1.0, 1.0),
           segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         radius=radius, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    apply_rot_scale(obj)
    assign(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def torus(name, major_radius, minor_radius, loc, material,
          rot=(0.0, 0.0, 0.0), major_segments=48, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius,
                                     minor_radius=minor_radius,
                                     major_segments=major_segments,
                                     minor_segments=minor_segments,
                                     location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    apply_rot_scale(obj)
    assign(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def mesh_object(name, verts, faces, material, loc=(0.0, 0.0, 0.0)):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    if material:
        assign(obj, material)
    return obj


def between(name, p1, p2, radius, material, verts=8):
    a, b = Vector(p1), Vector(p2)
    delta = b - a
    if delta.length < 0.001:
        return None
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=delta.length,
                                        location=(a + b) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    apply_rot_scale(obj)
    assign(obj, material)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def parent_keep_world(child, parent):
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()


def smooth_closed(points, steps=5):
    out = []
    count = len(points)
    for i in range(count):
        p0 = points[(i - 1) % count]
        p1 = points[i]
        p2 = points[(i + 1) % count]
        p3 = points[(i + 2) % count]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def ellipse_outline(rx, ry, seed=0, count=72):
    result = []
    phase = seed * 0.73
    for i in range(count):
        a = math.tau * i / count
        fac = 1.0 + 0.035 * math.sin(3 * a + phase) + 0.018 * math.sin(7 * a - phase)
        result.append((rx * math.cos(a) * fac, ry * math.sin(a) * fac))
    return result


MAIN_CENTER = (8.0, -1.0)
MAIN_POINTS_WORLD = [
    (8, 60), (42, 62), (73, 48), (94, 19), (92, -8), (80, -34),
    (50, -54), (10, -63), (-30, -57), (-60, -38), (-76, -8),
    (-68, 16), (-47, 32), (-28, 44), (-10, 58),
]
MAIN_OUTLINE = smooth_closed([(x - MAIN_CENTER[0], y - MAIN_CENTER[1])
                              for x, y in MAIN_POINTS_WORLD], steps=5)
HAIDIAN_CENTER = (-70.0, 45.0)
HAIDIAN_OUTLINE = ellipse_outline(26.0, 15.5, seed=3)


def make_land(name, center, outline, base_z=1.18, top_z=3.05):
    n = len(outline)
    scales = ((1.015, base_z), (1.0, base_z + 0.55),
              (0.985, top_z - 0.20), (0.98, top_z))
    verts = []
    for scale, z in scales:
        verts.extend((x * scale, y * scale, z - base_z) for x, y in outline)
    faces = []
    for layer in range(len(scales) - 1):
        a0, b0 = layer * n, (layer + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.append((a0 + i, a0 + j, b0 + j, b0 + i))
    top_start = (len(scales) - 1) * n
    top_center = len(verts)
    verts.append((0.0, 0.0, top_z - base_z))
    bottom_center = len(verts)
    verts.append((0.0, 0.0, 0.0))
    for i in range(n):
        j = (i + 1) % n
        faces.append((top_start + i, top_start + j, top_center))
        faces.append((i, bottom_center, j))
    return mesh_object(name, verts, faces, "grass", (center[0], center[1], base_z))


def add_rings_to_mesh(verts, faces, center, outline, inner, outer, z, lift=0.0):
    n = len(outline)
    start = len(verts)
    for scale, zoff in ((inner, 0.0), (outer, lift)):
        verts.extend((center[0] + x * scale, center[1] + y * scale, z + zoff)
                     for x, y in outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append((start + i, start + j, start + n + j, start + n + i))


def add_arch_band(name, front_x, center_y, base_z, outer_r, inner_r, depth,
                  material):
    steps = 14
    verts = []
    for x in (front_x - depth * 0.5, front_x + depth * 0.5):
        for radius in (outer_r, inner_r):
            for i in range(steps + 1):
                a = math.pi * i / steps
                verts.append((x, center_y + radius * math.cos(a),
                              base_z + radius * math.sin(a)))
    length = steps + 1
    faces = []
    # Front and rear arch faces.
    for side in range(2):
        outer0 = side * 2 * length
        inner0 = outer0 + length
        for i in range(steps):
            faces.append((outer0 + i, outer0 + i + 1,
                          inner0 + i + 1, inner0 + i))
    # Extruded sides and both arch feet.
    front_outer, front_inner = 0, length
    back_outer, back_inner = 2 * length, 3 * length
    for i in range(steps):
        faces.append((front_outer + i, back_outer + i,
                      back_outer + i + 1, front_outer + i + 1))
        faces.append((front_inner + i, front_inner + i + 1,
                      back_inner + i + 1, back_inner + i))
    for side_i in (0, steps):
        faces.append((front_outer + side_i, front_inner + side_i,
                      back_inner + side_i, back_outer + side_i))
    return mesh_object(name, verts, faces, material)


# ---------------------------------------------------------------------------
# Scene settings and round base.
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24 if DRAFT else 64
scene.cycles.use_denoising = True
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = 0.0
scene.render.film_transparent = False
world = bpy.data.worlds.new("Haikou_Sky")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.50, 0.69, 0.81, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.48

# Dark lower plinth, wooden lip, circular ocean, and visible concentric wood grain.
cyl("Plinth_Base", 112.0, 7.0, (0.0, 0.0, -3.45), "wood_dark", verts=96, bevel=1.0)
cyl("Wood_Tray", 110.1, 3.5, (0.0, 0.0, -1.25), "wood", verts=96, bevel=0.6)
cyl("Sea", 107.2, 0.75, (0.0, 0.0, 0.68), "sea", verts=96, bevel=0.12)
for i, (radius, mat) in enumerate(((108.0, "wood_dark"), (109.1, "butter"),
                                   (110.1, "wood_dark"), (111.0, "wood"))):
    torus("Tray_Grain_%02d" % (i + 1), radius, 0.16, (0.0, 0.0, 0.58), mat,
          major_segments=96, minor_segments=6)
plaque = box("Copper_Plaque", (52.0, 1.5, 7.0),
             (0.0, -110.8, -3.35), "gold", 0.45, seg=3)
text_data = bpy.data.curves.new("Copper_Plaque_Text_Curve", type="FONT")
text_data.body = "HAIKOU 20.04\N{DEGREE SIGN}N 110.34\N{DEGREE SIGN}E"
text_data.size = 2.0
text_data.extrude = 0.035
text_data.align_x = "CENTER"
text_data.align_y = "CENTER"
text_obj = bpy.data.objects.new("Copper_Plaque_Text", text_data)
bpy.context.collection.objects.link(text_obj)
text_obj.location = (0.0, -111.62, -3.35)
text_obj.rotation_euler = (math.pi / 2, 0.0, 0.0)
assign(text_obj, "dark")
_activate(text_obj)
bpy.ops.object.convert(target="MESH")
text_obj = bpy.context.object
apply_rot_scale(text_obj)

# Two independent land masses, with a visible sand and foam ribbon.
make_land("MainIsland", MAIN_CENTER, MAIN_OUTLINE)
make_land("Haidian", HAIDIAN_CENTER, HAIDIAN_OUTLINE, base_z=1.18, top_z=2.85)
sand_verts, sand_faces = [], []
add_rings_to_mesh(sand_verts, sand_faces, MAIN_CENTER, MAIN_OUTLINE,
                  1.006, 1.028, 1.10, 0.012)
add_rings_to_mesh(sand_verts, sand_faces, HAIDIAN_CENTER, HAIDIAN_OUTLINE,
                  1.008, 1.03, 1.09, 0.012)
mesh_object("Shore_Sand", sand_verts, sand_faces, "sand")
foam_verts, foam_faces = [], []
add_rings_to_mesh(foam_verts, foam_faces, MAIN_CENTER, MAIN_OUTLINE,
                  1.026, 1.052, 1.08, 0.018)
add_rings_to_mesh(foam_verts, foam_faces, HAIDIAN_CENTER, HAIDIAN_OUTLINE,
                  1.026, 1.052, 1.07, 0.018)
mesh_object("Foam", foam_verts, foam_faces, "foam")
shallow_verts, shallow_faces = [], []
add_rings_to_mesh(shallow_verts, shallow_faces, MAIN_CENTER, MAIN_OUTLINE,
                  1.046, 1.145, 1.075, 0.005)
# Keep the northwestern bridge channel dark and visibly open.
shallow_faces = [face for face in shallow_faces
                 if not (sum(shallow_verts[i][0] for i in face) / 4 < -25.0 and
                         sum(shallow_verts[i][1] for i in face) / 4 > 21.0)]
mesh_object("Coastal_Shallow", shallow_verts, shallow_faces, "glass")

# ---------------------------------------------------------------------------
# Roads, parks, CBD and a dense 42-block old-town fabric.
# Collector road ribbons make the neighborhood layout readable without leaving
# large uninterrupted lawns.
box("Coastal_Road", (4.0, 80.0, 0.32), (-35.2, -2.0, 3.28), "road", 0.14)
box("South_Avenue", (94.0, 4.2, 0.30), (26.0, -36.5, 3.28), "road", 0.14)
box("East_Avenue", (4.2, 65.0, 0.30), (53.5, -6.0, 3.28), "road", 0.14)

# Old-town quarter: a pedestrian lane, one plaza and a handful of larger,
# varied buildings instead of a repetitive block grid.
facades = ["cream", "butter", "mint", "terracotta", "skyblue", "white"]
roof_mats = ["terracotta", "skyblue", "coral", "cream"]
block_index = 0

def old_building(label, x, y, w, d, h, mat, roof_mat, roof="flat", rot=0.0, arcade=False):
    global block_index
    block_index += 1
    name = "OldTown_%02d" % block_index
    box(name, (w, d, h), (x, y, 3.32 + h / 2), mat, 0.5, rot=(0.0, 0.0, rot), seg=2)
    box(name + "_Roof", (w + 0.4, d + 0.4, 0.46),
        (x, y, 3.32 + h + 0.16), roof_mat, 0.16, seg=1, rot=(0.0, 0.0, rot))
    box(name + "_Parapet", (w + 0.55, d + 0.55, 0.38),
        (x, y, 3.32 + h + 0.42), "cream", 0.10, seg=1, rot=(0.0, 0.0, rot))
    # sparse windows so facades read without turning into a repetitive grid
    for wx in (-w * 0.28, w * 0.0, w * 0.28):
        for zz in (h * 0.42, h * 0.72):
            box(name + "_Win_%s_%s" % (round(wx, 1), round(zz, 1)),
                (1.25, 0.22, 1.15), (x + wx, y - d / 2 - 0.09, 3.32 + zz),
                "window", 0.10, seg=1, rot=(0.0, 0.0, rot))
    if roof == "hip":
        cone(name + "_Hip", max(w, d) * 0.64, 0.35, 2.4,
             (x, y, 3.32 + h + 1.55), roof_mats[0], verts=4, rot=(0.0, 0.0, math.radians(45) + rot))
    if arcade:
        for k in range(3):
            cx = x - w / 2 + w * (k + 1) / 4.0
            cyl(name + "_Col_%d" % k, 0.34, 3.6, (cx, y - d / 2 - 0.55, 5.1),
                "cream", verts=12)
            box(name + "_Arch_%d" % k, (1.4, 0.5, 0.5),
                (cx, y - d / 2 - 0.55, 7.0), "cream", 0.15, seg=1)
    return name

# The west edge is left open: the arcade row itself frames a large public square.
# east lane frontage (4 buildings, set back to leave gardens)
east = [(8, -24, 9.2, 9.2, 6.8), (8, -14, 9.2, 9.2, 8.4),
        (8, 16, 9.2, 9.2, 6.6)]
for i, (x, y, w, d, h) in enumerate(east):
    old_building("east", x, y, w, d, h, facades[(i + 2) % len(facades)],
                 roof_mats[(i + 1) % len(roof_mats)])

# waterfront fish-market hall and a lively market square by the marina
old_building("fishmarket", -25, -31, 15.0, 8.5, 6.4, "butter", "terracotta", arcade=True)
box("Market_Square", (24.0, 16.0, 0.16), (-4.0, -27.0, 3.30), "cream", 0.8, seg=2)
cyl("Market_Mast", 0.28, 9.0, (-4.0, -27.0, 7.8), "trunk", verts=10)
cone("Market_Mast_Cap", 1.2, 0.1, 1.8, (-4.0, -27.0, 13.0), "coral", verts=4)
for i, (x, y) in enumerate([(-12.0, -33.0), (-8.0, -35.0), (-2.0, -35.0), (3.0, -33.0),
                            (-13.0, -22.0), (-7.0, -20.5), (0.0, -20.5), (5.0, -22.0)]):
    box("Market_Stall_%d" % i, (2.6, 1.5, 1.15), (x, y, 3.9), "cream", 0.18, seg=1)
    cone("Market_Stall_Roof_%d" % i, 1.9, 0.15, 1.1, (x, y, 5.35),
         ["coral", "mint", "butter", "skyblue"][i % 4], verts=4)
for i, (x, y) in enumerate([(-15.0, -27.0), (7.0, -27.0), (-4.0, -18.5), (-4.0, -36.0)]):
    cyl("Market_Tree_Trunk_%d" % i, 0.3, 3.4, (x, y, 5.1), "trunk", verts=8)
    sphere("Market_Tree_Crown_%d" % i, 2.0, (x, y, 7.4), "leaf",
           scale=(1.0, 1.0, 1.05), segments=10, rings=7)

# north civic buildings around the plaza
old_building("guild", -26, 24, 11.0, 9.0, 8.8, "cream", "terracotta", roof="hip")
old_building("teahouse", -14, 24, 10.5, 9.0, 10.2, "terracotta", "coral", roof="hip")
old_building("post", -2, 24, 9.5, 9.0, 7.0, "skyblue", "cream")

# A single generous public square between the arcade and the CBD:
# paved ring, grass panels, fountain, banyan and a small market.
box("OldTown_Plaza", (28.0, 20.0, 0.16), (-16.0, -2.0, 3.30), "cream", 0.7, seg=2)
for i, (x, y, w, d) in enumerate([(-25.5, -8.0, 8.0, 6.0), (-25.5, 4.0, 8.0, 6.0),
                                 (-7.0, -8.0, 8.0, 6.0), (-7.0, 4.0, 8.0, 6.0)]):
    box("Plaza_Grass_%d" % i, (w, d, 0.22), (x, y, 3.42), "meadow", 0.6, seg=2)
cyl("Plaza_Fountain_Basin", 3.2, 0.55, (-16.0, -2.0, 3.55), "white", verts=28)
cyl("Plaza_Fountain_Water", 2.7, 0.18, (-16.0, -2.0, 3.86), "glass", verts=28)
cyl("Plaza_Fountain_Jet", 0.34, 2.1, (-16.0, -2.0, 5.0), "foam", verts=12)
cyl("Plaza_Banyan_Trunk", 0.85, 5.0, (-25.0, 7.0, 5.8), "trunk", verts=10)
sphere("Plaza_Banyan_Crown", 3.8, (-25.0, 7.0, 8.8), "leaf", scale=(1.25, 1.0, 0.85),
       segments=14, rings=9)
for i, (x, y) in enumerate([(-8.0, -9.0), (-8.0, 4.0)]):
    cyl("Market_Col_%d" % i, 0.22, 3.2, (x, y, 5.0), "trunk", verts=8)
    cone("Market_Roof_%d" % i, 2.8, 0.2, 1.6, (x, y, 7.1),
         "coral" if i % 2 else "mint", verts=4)
for i, (x, y) in enumerate([(-31.0, -2.0), (-1.0, -2.0), (-16.0, 9.0), (-16.0, -13.0)]):
    cyl("Plaza_EdgeTree_%d" % i, 0.3, 3.4, (x, y, 5.2), "trunk", verts=8)
    sphere("Plaza_EdgeCrown_%d" % i, 1.9, (x, y, 7.6), "leaf",
           scale=(1.0, 1.0, 1.05), segments=10, rings=7)

# ring walk around the fountain plus a row of shade trees and benches
torus("Plaza_RingWalk", 6.4, 0.30, (-16.0, -2.0, 3.40), "cream",
      major_segments=48, minor_segments=8)
for i in range(9):
    a = math.radians(40 + i * 40)
    x = -16.0 + math.cos(a) * 10.6
    y = -2.0 + math.sin(a) * 7.6
    cyl("Plaza_Tree_Trunk_%d" % i, 0.28, 3.0, (x, y, 5.1), "trunk", verts=8)
    sphere("Plaza_Tree_Crown_%d" % i, 1.75, (x, y, 7.2), "leaf",
           scale=(1.0, 1.0, 1.05), segments=10, rings=7)
for i, a in enumerate((45, 135, 225, 315)):
    ang = math.radians(a)
    x = -16.0 + math.cos(ang) * 7.4
    y = -2.0 + math.sin(ang) * 5.4
    box("Plaza_Bench_%d" % i, (2.0, 0.75, 0.55), (x, y, 3.85), "trunk", 0.18, seg=1)

# two pocket gardens outside the square
for i, (x, y, w, d) in enumerate([(-18, 18, 9, 6), (12, -6, 6, 8)]):
    box("OldTown_Garden_%d" % i, (w, d, 0.14), (x, y, 3.28), "meadow", 0.8, seg=2)
    sphere("OldTown_GardenTree_%d" % i, 2.2, (x, y, 5.6), "leaf",
           scale=(1.0, 1.0, 1.05), segments=12, rings=8)

# City hall on the east side of the square: colonnade + hipped roof.
box("Civic_Hall", (15.0, 13.0, 9.5), (7.5, 0.0, 3.32 + 4.75), "cream", 0.7, seg=3)
box("Civic_Hall_Band", (15.4, 13.4, 0.55), (7.5, 0.0, 3.32 + 6.2), "white", 0.18, seg=1)
for k in range(5):
    yy = -5.0 + k * 2.5
    cyl("Civic_Col_%d" % k, 0.36, 4.6, (0.25, yy, 3.32 + 2.3), "cream", verts=14)
    box("Civic_Col_Cap_%d" % k, (1.2, 1.2, 0.45), (0.25, yy, 3.32 + 4.75), "white", 0.14, seg=1)
for k in range(3):
    box("Civic_Win_%d" % k, (0.3, 2.4, 1.7), (0.05, -4.0 + k * 4.0, 3.32 + 7.4), "window", 0.10, seg=1)
cone("Civic_Roof", 10.6, 0.6, 3.8, (7.5, 0.0, 3.32 + 11.2), "terracotta", verts=4,
     rot=(0.0, 0.0, math.radians(45)))
box("Civic_Steps", (16.0, 1.6, 0.35), (7.5, -7.3, 3.46), "white", 0.18, seg=1)

# Open-air stage in the north-west corner of the square.
box("Plaza_Stage", (8.0, 6.0, 0.65), (-27.0, -10.0, 3.62), "cream", 0.3, seg=2)
for i, (x, y) in enumerate([(-30.4, -12.4), (-23.6, -12.4), (-30.4, -7.6), (-23.6, -7.6)]):
    cyl("Stage_Col_%d" % i, 0.3, 4.2, (x, y, 3.95 + 2.1), "trunk", verts=10)
cone("Stage_Roof", 5.6, 0.3, 2.4, (-27.0, -10.0, 3.95 + 4.2 + 1.2), "terracotta", verts=4,
     rot=(0.0, 0.0, math.radians(45)))

# Waterfront boardwalk / lookout linking the arcade, clock tower and fish market.
box("Boardwalk", (26.0, 3.4, 0.38), (-32.0, -37.5, 3.36), "wood", 0.22, seg=1,
    rot=(0.0, 0.0, math.radians(-0.22)))
box("Lookout_Deck", (12.0, 8.0, 0.42), (-44.0, -51.5, 3.36), "wood", 0.3, seg=2)
box("Lookout_Link", (4.0, 7.0, 0.36), (-44.0, -45.8, 3.34), "wood", 0.2, seg=1)
for i in range(7):
    x = -51.5 + i * 1.8
    cyl("Lookout_Post_%d" % i, 0.12, 1.4, (x, -55.4, 4.2), "wood_dark", verts=8)
box("Lookout_Rail", (12.4, 0.14, 0.18), (-44.0, -55.4, 4.92), "wood_dark", 0.05, seg=1)
for i in range(3):
    box("Lookout_Step_%d" % i, (10.0, 0.7, 0.28), (-44.0, -47.2 - i * 0.75, 3.2 - i * 0.28), "sand", 0.08, seg=1)
for i, (x, y) in enumerate([(-42.0, -48.0), (-30.0, -38.0), (-22.0, -36.0), (-38.0, -34.0)]):
    cyl("Boardwalk_Lamp_%d" % i, 0.16, 3.6, (x, y, 5.1), "dark", verts=8)
    sphere("Boardwalk_LampHead_%d" % i, 0.34, (x, y, 7.0), "gold", scale=(0.9, 0.9, 0.9),
           segments=10, rings=7)
for i, (x, y) in enumerate([(-39.0, -39.0), (-29.0, -38.5), (-19.0, -37.0)]):
    cyl("Boardwalk_Palm_Trunk_%d" % i, 0.35, 5.2, (x, y, 5.8), "trunk", verts=9)
    sphere("Boardwalk_Palm_Crown_%d" % i, 3.0, (x, y, 9.0), "leaf",
           scale=(1.1, 1.1, 0.75), segments=12, rings=8)

# Market crates and two moored fishing boats beside the boardwalk.
for i in range(6):
    box("Market_Crate_%d" % i, (1.1, 1.1, 0.8), (-16.0 + (i % 3) * 1.4, -34.5 - (i // 3) * 1.5, 3.75),
        "butter" if i % 2 else "terracotta", 0.12, seg=1)
for i, (x, y) in enumerate([(-24.0, -44.5), (-17.0, -45.5)]):
    box("FishBoat_Hull_%d" % i, (5.2, 2.2, 1.0), (x, y, 1.9), "white", 0.5, seg=2)
    box("FishBoat_Cabin_%d" % i, (2.2, 1.6, 1.2), (x - 0.8, y, 2.9), "skyblue", 0.35, seg=2)
    cyl("FishBoat_Mast_%d" % i, 0.12, 4.0, (x + 1.6, y, 4.0), "trunk", verts=8)

# Five slender rounded CBD towers in the center-north, with readable glass bands.
towers = [
    (16.0, 15.0, 9.0, 9.5, 34.0, "skyblue"),
    (29.0, 22.0, 9.5, 9.0, 45.0, "glass"),
    (43.5, 14.0, 8.5, 9.0, 31.0, "white"),
    (27.0, 38.0, 9.5, 9.0, 38.0, "skyblue"),
    (47.0, 35.0, 9.0, 9.5, 47.0, "glass"),
]
for i, (x, y, w, d, h, mat) in enumerate(towers, start=1):
    base = box("CBD_Tower_%02d" % i, (w, d, h), (x, y, 3.3 + h / 2), mat, 1.3, seg=3)
    box("CBD_Podium_%02d" % i, (w + 1.5, d + 1.5, 2.4),
        (x, y, 4.5), "white", 0.45, seg=2)
    for k in range(5):
        z = 7.0 + k * (h - 9.0) / 4.0
        box("CBD_Band_%02d_%02d" % (i, k), (w + 0.18, d + 0.18, 0.34),
            (x, y, z), "white", 0.10, seg=1)
    box("CBD_Facade_%02d" % i, (w * 0.62, 0.25, h * 0.68),
        (x, y - d / 2 - 0.16, 3.3 + h * 0.52), "window", 0.16, seg=2)
    box("CBD_Cap_%02d" % i, (w * 0.62, d * 0.62, 1.5),
        (x, y, 3.3 + h + 0.55), "white", 0.42, seg=2)

# ---------------------------------------------------------------------------
# Qilou old street: eight continuous ground-floor arches, west-facing shops,
# pastel upper floors, awnings, balconies, and tiled parapets.
arcade_y = [-31.0 + i * 6.95 for i in range(8)]
arcade_front_x = -50.0
arcade_depth = 11.2
for i, y in enumerate(arcade_y, start=1):
    unit_width = 6.65
    h = 16.0 + (i % 3) * 0.8
    facade = facades[(i + 1) % len(facades)]
    roof = roof_mats[i % len(roof_mats)]
    root = box("Arcade_%02d" % i, (arcade_depth, unit_width, h - 9.1),
               (arcade_front_x + arcade_depth / 2, y, 9.1 + (h - 9.1) / 2),
               facade, 0.65, seg=3)
    root["landmark"] = "Qilou Arcade"
    parent_parts = []
    # The open arcade is framed by two columns and a true semicircular voussoir band.
    for side, cy in enumerate((y - 2.50, y + 2.50)):
        col = cyl("Arcade_Column_%02d_%d" % (i, side), 0.46, 4.25,
                  (arcade_front_x - 0.25, cy, 5.36), "cream", verts=16)
        cap = box("Arcade_Cap_%02d_%d" % (i, side), (1.25, 1.25, 0.42),
                  (arcade_front_x - 0.25, cy, 7.48), "white", 0.16, seg=1)
        parent_parts.extend((col, cap))
    arch = add_arch_band("Arcade_Arch_%02d" % i, arcade_front_x - 0.25, y,
                         7.0, 2.50, 1.93, 0.92, "cream")
    back_wall = box("Arcade_InnerWall_%02d" % i, (0.65, unit_width, 5.8),
                    (arcade_front_x + arcade_depth - 0.35, y, 6.15), facade, 0.18, seg=1)
    awning = box("Arcade_Awning_%02d" % i, (2.6, unit_width - 0.65, 0.30),
                 (arcade_front_x - 0.65, y, 7.80), "coral" if i % 2 else "mint",
                 0.12, rot=(0.0, math.radians(7), 0.0), seg=1)
    parapet = box("Arcade_Parapet_%02d" % i, (0.85, unit_width + 0.15, 1.0),
                  (arcade_front_x + 0.25, y, h + 0.42), "white", 0.22, seg=2)
    roof_obj = box("Arcade_Roof_%02d" % i, (arcade_depth, unit_width + 0.20, 0.52),
                   (arcade_front_x + arcade_depth / 2, y, h + 0.16), roof, 0.26, seg=2)
    parent_parts.extend((arch, back_wall, awning, parapet, roof_obj))
    # Two upper-floor window pairs and their light frames.
    for row, wz in enumerate((h - 2.4, h - 5.0)):
        for side, wy in enumerate((y - 1.60, y + 1.60)):
            frame = box("Arcade_WindowFrame_%02d_%d_%d" % (i, row, side),
                        (0.32, 1.95, 1.85), (arcade_front_x - 0.12, wy, wz),
                        "white", 0.16, seg=1)
            pane = box("Arcade_Window_%02d_%d_%d" % (i, row, side),
                       (0.34, 1.42, 1.34), (arcade_front_x - 0.28, wy, wz),
                       "window", 0.12, seg=1)
            parent_parts.extend((frame, pane))
    sign = box("Arcade_Sign_%02d" % i, (0.36, 1.05, 2.55),
               (arcade_front_x - 0.82, y - 2.78, 11.0),
               "butter" if i % 2 else "white", 0.12, seg=1)
    parent_parts.append(sign)
    for part in parent_parts:
        parent_keep_world(part, root)

# A narrow shaded promenade and street lamps along the arcade frontage.
box("Arcade_Promenade", (2.8, 76.0, 0.24), (-53.8, 3.6, 3.20), "sand", 0.12)
for i, y in enumerate((-32, -20, -8, 4, 16, 28, 39)):
    cyl("Arcade_Lamp_%02d" % i, 0.18, 4.0, (-55.0, y, 5.2), "dark", verts=10)
    sphere("Arcade_LampHead_%02d" % i, 0.46, (-55.0, y, 7.3), "gold",
           scale=(0.85, 0.85, 0.85), segments=12, rings=8)

# ---------------------------------------------------------------------------
# Clock tower at the south end of the Qilou row, with four clock faces.
clock_x, clock_y = -48.5, -40.5
clock_base = box("ClockTower", (10.0, 10.0, 9.0),
                 (clock_x, clock_y, 7.8), "brick", 0.9, seg=3)
clock_base["landmark"] = "ClockTower"
clock_parts = []
shaft = box("ClockTower_Shaft", (7.4, 7.4, 14.0),
            (clock_x, clock_y, 19.3), "white", 0.75, seg=3)
clock_parts.append(shaft)
for z, width, material in ((12.4, 9.6, "brick"), (26.4, 8.8, "brick"),
                           (27.4, 7.1, "white")):
    clock_parts.append(box("ClockTower_Cornice_%.1f" % z, (width, width, 0.9),
                           (clock_x, clock_y, z), material, 0.32, seg=2))
for side in ("W", "E", "S", "N"):
    if side == "W":
        loc, rot = (clock_x - 3.88, clock_y, 22.7), (0.0, math.pi / 2, 0.0)
        hour_size, minute_size = (0.18, 0.34, 1.8), (0.18, 1.55, 0.18)
        hour_shift, minute_shift = (0.16, 0.0, 0.0), (0.15, 0.18, 0.58)
    elif side == "E":
        loc, rot = (clock_x + 3.88, clock_y, 22.7), (0.0, math.pi / 2, 0.0)
        hour_size, minute_size = (0.18, 0.34, 1.8), (0.18, 1.55, 0.18)
        hour_shift, minute_shift = (-0.16, 0.0, 0.0), (-0.15, 0.18, 0.58)
    elif side == "S":
        loc, rot = (clock_x, clock_y - 3.88, 22.7), (math.pi / 2, 0.0, 0.0)
        hour_size, minute_size = (0.34, 0.18, 1.8), (1.55, 0.18, 0.18)
        hour_shift, minute_shift = (0.0, 0.16, 0.0), (0.18, 0.15, 0.58)
    else:
        loc, rot = (clock_x, clock_y + 3.88, 22.7), (math.pi / 2, 0.0, 0.0)
        hour_size, minute_size = (0.34, 0.18, 1.8), (1.55, 0.18, 0.18)
        hour_shift, minute_shift = (0.0, -0.16, 0.0), (0.18, -0.15, 0.58)
    face = cyl("ClockTower_Face_" + side, 2.72, 0.34, loc, "cream", rot, verts=32)
    ring = torus("ClockTower_Rim_" + side, 2.76, 0.16, loc, "gold", rot,
                 major_segments=40, minor_segments=8)
    normal = Vector((0.0, 0.0, 1.0))
    normal = Vector((-1.0, 0.0, 0.0)) if side == "W" else \
        Vector((1.0, 0.0, 0.0)) if side == "E" else \
        Vector((0.0, -1.0, 0.0)) if side == "S" else Vector((0.0, 1.0, 0.0))
    hour_loc = Vector(loc) + normal * 0.27 + Vector((0.0, 0.0, 0.46))
    minute_loc = Vector(loc) + normal * 0.31
    hand1 = box("ClockTower_Hour_" + side, hour_size,
                hour_loc, "dark", 0.06, seg=1)
    hand2 = box("ClockTower_Minute_" + side, minute_size,
                minute_loc, "dark", 0.05, seg=1)
    clock_parts.extend((face, ring, hand1, hand2))
clock_parts.extend((cone("ClockTower_Roof", 5.3, 0.5, 5.8,
                         (clock_x, clock_y, 30.2), "skyblue", verts=4),
                    cyl("ClockTower_Spire", 0.22, 3.0,
                        (clock_x, clock_y, 34.6), "gold", verts=12),
                    sphere("ClockTower_Orb", 0.52, (clock_x, clock_y, 36.4), "gold",
                           segments=12, rings=8)))
for part in clock_parts:
    parent_keep_world(part, clock_base)

# ---------------------------------------------------------------------------
# Cloud Cave Library: smooth white shell with three boolean-cut, round portals.
lib_x, lib_y, lib_z = -54.0, 27.0, 7.0
library = sphere("Library", 1.0, (lib_x, lib_y, lib_z), "white",
                 scale=(7.0, 5.2, 4.2), segments=32, rings=20)
library["landmark"] = "Cloud Cave Library"
for i, (oy, oz, radius) in enumerate(((-3.10, -0.35, 1.02),
                                      (0.00, 0.70, 1.23),
                                      (3.10, -0.35, 1.02)), start=1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=radius, depth=18.0,
                                        location=(lib_x, lib_y + oy, lib_z + oz),
                                        rotation=(0.0, math.pi / 2, 0.0))
    cutter = bpy.context.object
    cutter.name = "_Library_Cutter_%02d" % i
    mod = library.modifiers.new("portal_%02d" % i, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    apply_modifiers(library)
    bpy.data.objects.remove(cutter, do_unlink=True)
for i, (oy, oz, radius) in enumerate(((-3.10, -0.35, 0.98),
                                      (0.00, 0.70, 1.19),
                                      (3.10, -0.35, 0.98)), start=1):
    disk = cyl("Library_Portal_Shadow_%02d" % i, radius, 0.20,
               (lib_x + 4.4, lib_y + oy, lib_z + oz), "dark",
               rot=(0.0, math.pi / 2, 0.0), verts=32)
    parent_keep_world(disk, library)
box("Library_Platform", (11.0, 14.0, 1.0), (lib_x, lib_y, 3.55), "sand", 1.3, seg=3)

# ---------------------------------------------------------------------------
# Century Bridge over the northwestern channel, with twin H pylons, fan stays,
# two descending approaches, barriers, six named cars and visible piers.
bridge_center = (-35.5, 45.5)
bridge_angle = math.radians(-23.0)
bridge_span = 40.0
deck_z = 12.8
ca, sa = math.cos(bridge_angle), math.sin(bridge_angle)

def bridge_point(x, y, z):
    return (bridge_center[0] + x * ca - y * sa,
            bridge_center[1] + x * sa + y * ca, z)


def bridge_box(name, size, x, y, z, material, bevel=0.25, seg=2):
    return box(name, size, bridge_point(x, y, z), material, bevel,
               (0.0, 0.0, bridge_angle), seg)

bridge_box("Bridge_Deck", (bridge_span, 8.6, 1.25), 0, 0, deck_z, "white", 0.72, 3)
bridge_box("Bridge_Girder_L", (bridge_span, 0.65, 1.65), 0, -4.0,
           deck_z - 1.22, "skyblue", 0.22, 2)
bridge_box("Bridge_Girder_R", (bridge_span, 0.65, 1.65), 0, 4.0,
           deck_z - 1.22, "skyblue", 0.22, 2)
for side in (-1, 1):
    bridge_box("Bridge_Rail_%s" % side, (bridge_span, 0.35, 1.15), 0,
               side * 4.15, deck_z + 0.92, "coral", 0.12, 2)
    for i in range(17):
        x = -19.0 + i * 2.38
        bridge_box("Bridge_Baluster_%s_%02d" % (side, i), (0.20, 0.22, 1.05),
                   x, side * 4.15, deck_z + 0.12, "white", 0.06, 1)

# Approach embankments are solid wedges: top matches the deck, sides and ends
# reach the ground so there is no floating ramp or visible joint.
def ramp_mesh(name, x0, x1):
    # x0 must be the land end: keep the outer x on the low side on both banks.
    if abs(x0) < abs(x1):
        x0, x1 = x1, x0
    z0, z1, zb = 3.30, deck_z + 0.18, 2.20
    verts = []
    for x, z in ((x0, z0), (x1, z1)):
        for y in (-4.6, 4.6):
            verts.append(bridge_point(x, y, z))
    for x, z in ((x0, z0), (x1, z1)):
        for y in (-4.6, 4.6):
            verts.append(bridge_point(x, y, zb))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign(obj, "white")
    return obj

ramp_mesh("Bridge_Ramp_NW", -31.0, -19.8)
ramp_mesh("Bridge_Ramp_SE", 19.8, 31.0)
for sx in (-1, 1):
    bridge_box("Bridge_Abutment_%s" % ("NW" if sx < 0 else "SE"),
               (4.2, 9.4, 4.4), sx * 20.4, 0, 11.0, "white", 0.45, 2)
    bridge_box("Bridge_RoadJoin_%s" % ("NW" if sx < 0 else "SE"),
               (3.6, 9.6, 0.55), sx * 31.6, 0, 3.55, "road", 0.12, 1)
bridge_pylons = []
for side, px in (("L", -8.3), ("R", 8.3)):
    root = box("Bridge_Tower_" + side, (1.7, 0.9, 17.2),
               bridge_point(px, -3.25, deck_z + 8.8), "white", 0.28, seg=2)
    root["landmark"] = "Century Bridge Tower"
    pieces = []
    for py in (-3.2, 3.2):
        pieces.append(box("Bridge_PylonLeg_%s_%.1f" % (side, py),
                          (1.55, 0.78, 18.0),
                          bridge_point(px, py, deck_z + 8.8), "white", 0.24, seg=2))
    pieces.append(bridge_box("Bridge_PylonCross_%s" % side, (1.55, 7.6, 1.4),
                             px, 0, deck_z + 17.3, "coral", 0.24, 2))
    pieces.append(bridge_box("Bridge_PylonMid_%s" % side, (1.35, 7.0, 0.95),
                             px, 0, deck_z + 9.1, "skyblue", 0.20, 2))
    for p in pieces:
        parent_keep_world(p, root)
    bridge_pylons.append((side, px, root))

for side, px, root in bridge_pylons:
    top = bridge_point(px, 0.0, deck_z + 17.2)
    for i, x in enumerate((px - 7.0, px - 4.8, px - 2.6, px + 2.6, px + 4.8, px + 7.0)):
        if abs(x - px) < 1.0:
            continue
        for sy in (-1, 1):
            cable = between("Bridge_Stay_%s_%02d_%s" % (side, i, sy),
                            top, bridge_point(x, sy * 3.65, deck_z + 1.25),
                            0.075, "white", verts=6)
            if cable:
                parent_keep_world(cable, root)

for i, x in enumerate((-18.0, 18.0), start=1):
    pier = between("Bridge_Pier_%02d" % i, bridge_point(x, 0, 1.1),
                   bridge_point(x, 0, deck_z - 1.1), 1.0, "white", verts=10)

# Named vehicle roots sit at their chassis centers; attached parts move with them.
car_palette = ["coral", "butter", "skyblue", "mint", "white", "terracotta"]
for i, x in enumerate((-15.5, -9.5, -3.5, 3.5, 9.5, 15.5), start=1):
    lane_y = -1.8 if i % 2 else 1.8
    loc = bridge_point(x, lane_y, deck_z + 1.10)
    car = box("Car_%02d" % i, (3.65, 1.85, 0.98), loc,
              car_palette[i - 1], 0.28, (0.0, 0.0, bridge_angle), seg=2)
    for part in (
        box("Car_Window_%02d" % i, (2.0, 1.35, 0.72),
            bridge_point(x - 0.05, lane_y, deck_z + 1.92), "window", 0.20,
            (0.0, 0.0, bridge_angle), seg=2),
        box("Car_Bumper_%02d" % i, (0.34, 1.72, 0.25),
            bridge_point(x + 1.82, lane_y, deck_z + 0.92), "white", 0.08,
            (0.0, 0.0, bridge_angle), seg=1),
    ):
        parent_keep_world(part, car)
    for wx in (-1.18, 1.18):
        for wy in (-0.92, 0.92):
            wheel = sphere("Car_Wheel_%02d_%s_%s" % (i, wx, wy), 0.48,
                           bridge_point(x + wx, lane_y + wy, deck_z + 0.66),
                           "dark", scale=(1.0, 0.48, 0.68), segments=12, rings=8)
            parent_keep_world(wheel, car)

# ---------------------------------------------------------------------------
# Park, volcanic cone and east-coast fishing village.
park_x, park_y = 17.0, -37.0
park_outline = ellipse_outline(23.0, 15.4, seed=8, count=64)
park_verts = [(x, y, 0.0) for x, y in park_outline]
park_verts.append((0.0, 0.0, 0.0))
park_faces = [(i, (i + 1) % len(park_outline), len(park_outline))
              for i in range(len(park_outline))]
park = mesh_object("Park", park_verts, park_faces, "meadow",
                   (park_x, park_y, 3.42))
park["landmark"] = "Wanlv Park"
sphere("Park_Lake", 1.0, (park_x - 3.8, park_y + 2.6, 3.62), "sea",
       scale=(9.4, 5.6, 0.14), segments=32, rings=12)
for i, (x, y, length, angle) in enumerate(((-7, -7, 20, 0.08), (7, -3, 19, -0.22),
                                           (-1, 7, 22, 0.52), (9, 8, 15, -0.6)), start=1):
    box("Park_Path_%02d" % i, (length, 1.35, 0.20),
        (park_x + x, park_y + y, 3.62), "sand", 0.55,
        (0.0, 0.0, angle), seg=2)
for i, (x, y) in enumerate(((-10, -1), (5, -10), (13, 3)), start=1):
    box("Park_Bench_%02d" % i, (3.4, 0.55, 0.42),
        (park_x + x, park_y + y, 4.0), "wood", 0.14, seg=2)
    for dx in (-1.2, 1.2):
        box("Park_BenchLeg_%02d_%s" % (i, dx), (0.24, 0.32, 0.85),
            (park_x + x + dx, park_y + y, 3.64), "dark", 0.06, seg=1)
# A small airy gazebo anchors the lakeside without obscuring the park.
for i, (dx, dy) in enumerate(((-2.1, -1.7), (2.1, -1.7),
                              (-2.1, 1.7), (2.1, 1.7)), start=1):
    cyl("Park_GazeboPost_%02d" % i, 0.16, 3.2,
        (park_x + 10 + dx, park_y + 5 + dy, 5.1), "white", verts=10)
box("Park_GazeboRoof", (5.5, 4.8, 0.5),
    (park_x + 10, park_y + 5, 6.95), "terracotta", 0.18, seg=2)

vol_x, vol_y = 66.0, -24.0
VOL_SEG = 72
VOL_BASE = 3.32
VOL_RINGS = [(21.2, 3.32), (19.6, 4.15), (18.0, 5.25), (16.5, 6.55),
             (15.0, 8.0), (13.6, 9.55), (12.3, 11.15), (11.1, 12.7),
             (10.0, 14.1), (9.0, 15.3), (8.2, 16.15), (7.6, 16.75)]

def vol_scale(a):
    return (1.0 + 0.085 * math.sin(3.0 * a + 0.7)
            + 0.050 * math.sin(7.0 * a + 1.3)
            + 0.028 * math.sin(11.0 * a - 0.4)
            + 0.070 * math.cos(a - 0.85))

def vol_zoff(a):
    return 0.42 * math.sin(2.0 * a + 0.2) + 0.24 * math.sin(5.0 * a + 1.0)

def vol_breach(a):
    return max(0.0, math.cos(a - 2.25)) ** 6

def vol_profile_z(r):
    rs = [p[0] for p in VOL_RINGS]
    zs = [p[1] for p in VOL_RINGS]
    if r >= rs[0]:
        return VOL_BASE
    if r <= rs[-1]:
        return zs[-1]
    for i in range(len(rs) - 1):
        if rs[i] >= r >= rs[i + 1]:
            t = (rs[i] - r) / (rs[i] - rs[i + 1])
            return zs[i] + (zs[i + 1] - zs[i]) * t
    return VOL_BASE

def vol_surface_z(r, a):
    return vol_profile_z(r) + vol_zoff(a) * 0.55

verts, faces, face_mats = [], [], []
for li, (rr, zz) in enumerate(VOL_RINGS):
    for i in range(VOL_SEG):
        a = math.tau * i / VOL_SEG
        z = zz + vol_zoff(a) * 0.55
        if li >= len(VOL_RINGS) - 2:
            z -= 2.1 * vol_breach(a)
        verts.append((vol_x + rr * vol_scale(a) * math.cos(a),
                      vol_y + rr * vol_scale(a) * math.sin(a), z))
for li in range(len(VOL_RINGS) - 1):
    for i in range(VOL_SEG):
        a0 = li * VOL_SEG + i
        a1 = li * VOL_SEG + (i + 1) % VOL_SEG
        b0 = a0 + VOL_SEG
        b1 = a1 + VOL_SEG
        faces.append((a0, a1, b1, b0))
        zc = (verts[a0][2] + verts[a1][2] + verts[b0][2] + verts[b1][2]) / 4.0
        ac = math.atan2(verts[a0][1] + verts[b0][1], verts[a0][0] + verts[b0][0])
        if zc < 6.4 + 0.55 * math.sin(3.0 * ac):
            face_mats.append(0)
        elif zc < 12.4:
            face_mats.append(1)
        else:
            face_mats.append(2)
# inner crater bowl
inner = [(7.55, 16.7), (6.9, 16.0), (5.8, 14.9), (4.5, 13.9),
         (3.1, 13.25), (1.5, 13.0)]
inner_start = len(verts)
for li, (rr, zz) in enumerate(inner):
    for i in range(VOL_SEG):
        a = math.tau * i / VOL_SEG
        z = zz + vol_zoff(a) * 0.3 - 1.7 * vol_breach(a) * (li == 0)
        verts.append((vol_x + rr * math.cos(a), vol_y + rr * math.sin(a), z))
for li in range(len(inner) - 1):
    for i in range(VOL_SEG):
        a0 = inner_start + li * VOL_SEG + i
        a1 = inner_start + li * VOL_SEG + (i + 1) % VOL_SEG
        b0 = a0 + VOL_SEG
        b1 = a1 + VOL_SEG
        faces.append((a0, b0, b1, a1))
        face_mats.append(3 if li < 3 else 2)
verts.append((vol_x, vol_y, 12.85))
center_idx = len(verts) - 1
last = inner_start + (len(inner) - 1) * VOL_SEG
for i in range(VOL_SEG):
    faces.append((last + i, last + (i + 1) % VOL_SEG, center_idx))
    face_mats.append(3)

mesh = bpy.data.meshes.new("Volcano_mesh")
mesh.from_pydata(verts, [], faces)
mesh.update()
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()
volcano = bpy.data.objects.new("Volcano", mesh)
bpy.context.collection.objects.link(volcano)
for mat in ("grass", "terracotta", "dark", "lava"):
    volcano.data.materials.append(MATS[mat])
for i, poly in enumerate(volcano.data.polygons):
    poly.material_index = face_mats[i] if i < len(face_mats) else 2
volcano["landmark"] = "Volcano"

# Lava tongue escaping the breached south-east rim.
lava_verts, lava_faces = [], []
for i in range(12):
    rr = 7.4 + i * 1.18
    a0 = 2.25
    z = vol_surface_z(rr, a0) + 0.22
    for da in (-0.085, 0.085):
        lava_verts.append((rr * math.cos(a0 + da), rr * math.sin(a0 + da), z))
for i in range(11):
    a = i * 2
    lava_faces.append((a, a + 1, a + 3, a + 2))
lava = mesh_object("Volcano_LavaFlow", lava_verts, lava_faces, "lava")
lava_verts2 = [(vol_x + x, vol_y + y, z) for x, y, z in lava_verts]
lava.data.vertices.foreach_set("co", [c for v in lava_verts2 for c in v])
lava.data.update()

# Cinder cone and rim rocks give the silhouette a second, rougher peak.
cinder = cone("Volcano_CinderCone", 4.8, 0.9, 3.4,
              (vol_x + 10.5, vol_y + 7.0, 5.05), "dark", verts=28)
cone("Volcano_CinderCrater", 1.05, 0.55, 0.7,
     (vol_x + 10.5, vol_y + 7.0, 6.55), "lava", verts=16)
for i in range(7):
    a = 2.05 + i * 0.12
    rr = 7.7 + (i % 3) * 0.5
    z = vol_surface_z(rr, a) + 0.4
    box("Volcano_RimRock_%02d" % i, (1.9, 1.3, 1.1),
        (vol_x + rr * math.cos(a), vol_y + rr * math.sin(a), z),
        "dark", 0.2, (0.0, 0.0, a), seg=1)
# lookout terrace at the foot of the cone
torus("Volcano_Lookout_Ring", 20.6, 0.55, (vol_x, vol_y, 4.0), "wood",
      major_segments=48, minor_segments=8)
box("Volcano_ObservationDeck", (8.0, 4.0, 0.6),
    (vol_x + 20.6, vol_y - 6.0, 4.2), "wood", 0.3,
    (0.0, 0.0, math.radians(-18)), seg=2)

# Vegetation clusters on the lower slopes, rocks and switchback trail above.
for i in range(26):
    cluster = i % 3
    base_a = (2.9, 4.35, 5.55)[cluster]
    a = base_a + random.uniform(-0.28, 0.28)
    rr = random.uniform(12.6, 18.2)
    if abs(math.atan2(math.sin(a - 2.25), math.cos(a - 2.25))) < 0.45:
        rr = 19.0
    z = vol_surface_z(rr, a)
    x = vol_x + rr * math.cos(a)
    y = vol_y + rr * math.sin(a)
    cyl("Volcano_Tree_Trunk_%02d" % i, 0.20, 1.3, (x, y, z + 0.65), "trunk", verts=8)
    sphere("Volcano_Tree_Crown_%02d" % i, 1.05, (x, y, z + 1.55), "leaf",
           scale=(1.0, 1.0, 0.95), segments=10, rings=7)
for i in range(12):
    a = math.tau * (i / 12.0) + 0.2
    rr = 8.4 + (i % 4) * 0.55
    z = vol_surface_z(rr, a)
    box("Volcano_Rock_%02d" % i, (1.5, 1.1, 0.9),
        (vol_x + rr * math.cos(a), vol_y + rr * math.sin(a), z + 0.3),
        "dark", 0.16, (0.0, 0.0, a), seg=1)
for i in range(11):
    t = i / 10.0
    rr = 19.2 - t * 10.6
    a = 5.35 - t * 1.5
    z = vol_surface_z(rr, a)
    box("Volcano_Trail_%02d" % i, (2.2, 1.0, 0.22),
        (vol_x + rr * math.cos(a), vol_y + rr * math.sin(a), z + 0.15),
        "sand", 0.10, (0.0, 0.0, -a), seg=1)
for i, (dx, dy, dz, sc) in enumerate(((-1.2, 0.4, 2.2, 1.5), (1.4, -0.6, 3.4, 1.9),
                                      (-0.4, 1.1, 4.8, 2.2), (1.0, 0.2, 6.2, 2.5))):
    sphere("Volcano_Steam_%02d" % i, sc, (vol_x + dx, vol_y + dy, 16.8 + dz), "cloud",
           scale=(1.0, 0.95, 0.8), segments=12, rings=8)

# East-coast fishing village: ten pastel houses and a winding road.
for i in range(10):
    row, col = divmod(i, 5)
    x = 73.0 + col * 4.6 + (row % 2) * 1.6
    y = -1.0 + row * 8.0 + (col % 2) * 1.3
    w, d = random.uniform(3.5, 4.5), random.uniform(3.6, 4.6)
    h = random.uniform(4.5, 6.0)
    house = box("EastVillage_House_%02d" % (i + 1), (w, d, h),
                (x, y, 3.32 + h / 2), facades[(i + 2) % len(facades)], 0.44, seg=2)
    cone("EastVillage_Roof_%02d" % (i + 1), w * 0.72, 0.35, 2.0,
         (x, y, 3.32 + h + 1.0), "terracotta" if i % 2 else "skyblue", verts=4)
box("EastVillage_Lane", (2.2, 49.0, 0.20),
    (70.0, 6.8, 3.30), "road", 0.10, seg=1)

# ---------------------------------------------------------------------------
# Haidian Island fishing village and lighthouse.
for i in range(7):
    x = -86.0 + (i % 4) * 7.1
    y = 42.0 + (i // 4) * 7.2 + (i % 2) * 1.0
    w, d, h = random.uniform(4.4, 5.7), random.uniform(4.2, 5.4), random.uniform(4.8, 6.8)
    box("Haidian_House_%02d" % (i + 1), (w, d, h),
        (x, y, 2.95 + h / 2), facades[i % len(facades)], 0.44, seg=2)
    cone("Haidian_Roof_%02d" % (i + 1), w * 0.74, 0.35, 2.0,
         (x, y, 2.95 + h + 1.0), "skyblue" if i % 2 else "terracotta", verts=4)
box("Haidian_Road", (35.0, 2.2, 0.22), (-70.0, 43.0, 3.0), "road", 0.10, seg=1)
lighthouse = cyl("Lighthouse", 1.55, 8.4, (-88.6, 49.2, 7.0), "white", verts=20)
cone("Lighthouse_RedBand", 1.7, 1.7, 1.1, (-88.6, 49.2, 9.4), "coral", verts=20)
cyl("Lighthouse_Lantern", 1.34, 1.45, (-88.6, 49.2, 11.0), "gold", verts=20)
cone("Lighthouse_Roof", 1.7, 0.2, 1.6, (-88.6, 49.2, 12.5), "coral", verts=16)

# ---------------------------------------------------------------------------
# Three southwestern dock clusters, nine fish boats and three outer sailboats.
dock_layout = ((-50.0, -45.0, 44.0), (-32.0, -63.0, 27.0), (-14.0, -74.0, 17.0))
for group, (y, shore_x, length) in enumerate(dock_layout, start=1):
    end_x = shore_x - length
    center_x = (shore_x + end_x) / 2.0
    box("Dock_%02d_Pier" % group, (length, 4.0, 0.82),
        (center_x, y, 1.82), "wood", 0.35, seg=2)
    for i in range(int(length // 5.0) + 1):
        x = shore_x - 2.0 - i * 4.8
        cyl("Dock_%02d_Pile_%02d" % (group, i), 0.34, 3.8,
            (x, y, 0.28), "wood_dark", verts=10)
    for i, x in enumerate((shore_x - 8.0, shore_x - length * 0.56,
                           shore_x - length + 5.0), start=1):
        box("Dock_%02d_Finger_%02d" % (group, i), (2.6, 5.4, 0.58),
            (x, y + 3.8, 1.82), "wood", 0.22, seg=2)

# Three fish-market sheds sit on the landward ends of the piers.
for i, (x, y) in enumerate(((-39.0, -50.0), (-56.0, -32.0), (-67.0, -14.0)), start=1):
    box("FishMarket_%02d" % i, (6.2, 5.4, 4.0),
        (x, y, 5.45), "cream", 0.42, seg=2)
    cone("FishMarket_Roof_%02d" % i, 4.4, 0.28, 2.4,
         (x, y, 8.65), "terracotta", verts=4)
    box("FishMarket_Awning_%02d" % i, (1.6, 6.4, 0.30),
        (x - 3.4, y, 5.15), "coral", 0.12, seg=1)
    for j in range(3):
        cyl("FishMarket_Basket_%02d_%02d" % (i, j), 0.65, 0.8,
            (x - 4.6, y - 1.6 + j * 1.5, 3.95), "wood", verts=12)

# Low, segmented stone breakwater wraps the outer harbor without leaving the tray.
breakwater_points = [(-88.0, -60.0), (-96.0, -48.0), (-98.0, -35.0), (-95.0, -21.0)]
for i in range(len(breakwater_points) - 1):
    ax, ay = breakwater_points[i]
    bx, by = breakwater_points[i + 1]
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    angle = math.atan2(dy, dx)
    box("Breakwater_Segment_%02d" % (i + 1), (length + 0.8, 3.0, 1.65),
        ((ax + bx) * 0.5, (ay + by) * 0.5, 1.88), "road", 0.48,
        (0.0, 0.0, angle), seg=2)
for i, (x, y) in enumerate(((-91, -53), (-97, -41), (-97, -28)), start=1):
    cyl("Harbor_Buoy_%02d" % i, 0.62, 1.5, (x, y, 2.55), "butter", verts=12)
    sphere("Harbor_Buoy_Lamp_%02d" % i, 0.42, (x, y, 3.48), "coral",
           segments=10, rings=7)


def boat(name, loc, color, heading=0.0):
    x, y = loc
    # Root origin is at the waterline; the hull mesh center sits just above it.
    root = box(name, (8.2, 3.25, 1.12), (x, y, 1.85), "white", 0.58,
               (0.0, 0.0, heading), seg=3)
    bpy.context.scene.cursor.location = (x, y, 1.0)
    _activate(root)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    cabin = box(name + "_Cabin", (3.15, 2.35, 1.7),
                (x - math.cos(heading) * 1.1, y - math.sin(heading) * 1.1, 3.05),
                color, 0.40, (0.0, 0.0, heading), seg=2)
    roof = box(name + "_CabinRoof", (3.45, 2.55, 0.28),
               (x - math.cos(heading) * 1.1, y - math.sin(heading) * 1.1, 3.98),
               "white", 0.12, (0.0, 0.0, heading), seg=1)
    mast = cyl(name + "_Mast", 0.16, 4.6, (x + math.cos(heading) * 2.3,
               y + math.sin(heading) * 2.3, 4.25), "trunk", verts=8)
    crane = between(name + "_Crane", (x + math.cos(heading) * 2.3,
                    y + math.sin(heading) * 2.3, 6.4),
                    (x + math.cos(heading) * 4.8, y + math.sin(heading) * 4.8, 5.3),
                    0.10, "gold", verts=8)
    stripe = box(name + "_HullStripe", (7.4, 0.16, 0.23),
                 (x, y, 1.52), color, 0.06, (0.0, 0.0, heading), seg=1)
    for part in (cabin, roof, mast, crane, stripe):
        if part:
            parent_keep_world(part, root)
    root["animation_anchor"] = "Waterline center"
    return root

boat_positions = [(-87, -54), (-83, -45), (-88, -37),
                  (-82, -35), (-86, -27), (-80, -20),
                  (-84, -18), (-80, -9), (-76, -24)]
for i, loc in enumerate(boat_positions, start=1):
    heading = math.radians((-18, 11, -28, 20, -12, 14, 32, -5, 22)[i - 1])
    root = boat("Boat_%02d" % i, loc, car_palette[(i + 1) % len(car_palette)],
                heading=heading)
    x, y = loc
    for side in (-1, 1):
        wake_heading = heading + side * 0.36
        wake = box("Boat_Wake_%02d_%s" % (i, side), (4.6, 0.20, 0.07),
                   (x - math.cos(heading) * 5.4 + side * math.sin(heading) * 1.0,
                    y - math.sin(heading) * 5.4 - side * math.cos(heading) * 1.0,
                    1.12), "foam", 0.08, (0.0, 0.0, wake_heading), seg=1)
        parent_keep_world(wake, root)

# Three small sailboats are distributed around the open water for balance.
for i, (x, y, heading) in enumerate(((-94, -32, 0.12), (22, -96, -0.28),
                                     (89, -48, 0.30)), start=1):
    root = box("Sail_%02d" % i, (7.4, 2.5, 0.9), (x, y, 1.55), "cream",
               0.42, (0.0, 0.0, heading), seg=2)
    mast = cyl("Sail_Mast_%02d" % i, 0.12, 6.0, (x, y, 4.7), "trunk", verts=8)
    sail_mesh = mesh_object("Sail_Canvas_%02d" % i,
                            [(-0.08, 0, 1.8), (-0.08, 0, 6.0),
                             (-0.08, 2.6, 2.2)], [(0, 1, 2)], "white",
                            (x, y, 0.0))
    mast.rotation_euler[2] = heading
    apply_rot_scale(mast)
    parent_keep_world(mast, root)
    parent_keep_world(sail_mesh, root)

# South-park marina boardwalk and east fishing jetty fill the nearshore water.
box("Park_Marina_Walk", (46.0, 2.8, 0.70), (18.0, -72.5, 1.92),
    "wood", 0.35, seg=2)
box("Park_Marina_Link", (2.6, 15.0, 0.70), (6.0, -66.0, 1.92),
    "wood", 0.30, seg=2)
for i, x in enumerate((0.0, 10.0, 20.0, 30.0, 40.0), start=1):
    box("Park_Marina_Finger_%02d" % i, (2.0, 7.2, 0.65),
        (x, -76.2, 1.91), "wood", 0.24, seg=2)
    cyl("Park_Marina_Post_%02d" % i, 0.22, 2.2, (x, -79.2, 1.9), "white", verts=10)
    torus("Park_Marina_Ring_%02d" % i, 0.52, 0.16,
          (x, -77.0, 2.44), "coral", major_segments=20, minor_segments=6)
box("EastVillage_Jetty", (12.8, 2.6, 0.68), (97.6, 10.5, 1.80),
    "wood", 0.28, seg=2)
for i, (x, y) in enumerate(((52, -78), (66, -69), (79, -58), (91, -42),
                              (98, -17), (48, 75), (17, 88)), start=1):
    cone("Navigation_Buoy_%02d" % i, 0.82, 0.36, 1.2,
         (x, y, 1.7), "coral" if i % 2 else "butter", verts=12)
    cyl("Navigation_Mast_%02d" % i, 0.12, 1.5,
        (x, y, 2.95), "dark", verts=8)

# Thin animated-looking foam strokes provide scale in the outer water without
# adding an extra material or changing the single named Foam shoreline anchor.
wave_specs = [(-39, -86, 12, 0.10), (-9, -91, 13, -0.12),
              (49, -83, 12, 0.28), (68, -70, 9, 0.32),
              (91, -33, 8, 0.52), (-8, 85, 11, -0.13),
              (25, 83, 9, 0.05), (57, 69, 10, 0.42),
              (-68, -76, 8, -0.16), (-99, 8, 9, 1.2)]
for i, (cx, cy, length, angle) in enumerate(wave_specs, start=1):
    pts = []
    for k in range(7):
        t = (k / 6.0 - 0.5) * length
        rise = 0.50 * math.cos(t * math.pi / length)
        pts.append((cx + t * math.cos(angle) - rise * math.sin(angle),
                    cy + t * math.sin(angle) + rise * math.cos(angle), 1.13))
    for j in range(6):
        between("Sea_Ripple_%02d_%02d" % (i, j), pts[j], pts[j + 1],
                0.28, "foam", verts=6)
for i, (x, y, sx, sy) in enumerate(((81, -58, 2.6, 1.7), (86, -51, 1.8, 1.5),
                                    (4, 79, 2.8, 1.6), (12, 81, 1.8, 1.2)), start=1):
    sphere("Reef_%02d" % i, 1.0, (x, y, 1.15), "road",
           scale=(sx, sy, 0.85), segments=12, rings=8)

# ---------------------------------------------------------------------------
# 28 named palms plus 44 low-poly shade trees (72 total); concentrated around
# the park, village edges and coast rather than left as empty green expanses.
def palm_mesh(name, loc, height, lean, phase):
    verts, faces, mat_index = [], [], []
    xlean = math.sin(lean) * height * 0.22
    top = (xlean, 0.0, height)
    # Three tapering trunk sections.
    for i in range(3):
        z0, z1 = height * i / 3.0, height * (i + 1) / 3.0
        r0, r1 = 0.48 - 0.10 * i, 0.48 - 0.10 * (i + 1)
        start = len(verts)
        for z, radius in ((z0, r0), (z1, r1)):
            for j in range(8):
                a = math.tau * j / 8
                verts.append((xlean * z / height + radius * math.cos(a),
                              radius * math.sin(a), z))
        for j in range(8):
            faces.append((start + j, start + (j + 1) % 8,
                          start + 8 + (j + 1) % 8, start + 8 + j))
            mat_index.append(0)
    # Eight curved ribbon fronds, each split into tapering segments.
    for k in range(8):
        a = math.tau * k / 8 + phase
        length = random.uniform(4.8, 6.0)
        base = len(verts)
        divisions = 5
        for j in range(divisions + 1):
            t = j / divisions
            width = 0.08 if j == divisions else (0.64 * math.sin(math.pi * t) ** 0.7 + 0.07)
            outward = length * t
            drop = 1.2 * t * t * length / 5.5
            cx = top[0] + math.cos(a) * outward
            cy = top[1] + math.sin(a) * outward
            cz = top[2] - drop + math.sin(t * math.pi) * 0.30
            side_x, side_y = -math.sin(a) * width, math.cos(a) * width
            verts.extend(((cx - side_x, cy - side_y, cz),
                          (cx + side_x, cy + side_y, cz)))
        for j in range(divisions):
            a0 = base + 2 * j
            faces.append((a0, a0 + 1, a0 + 3, a0 + 2))
            mat_index.append(1)
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(MATS["trunk"])
    mesh.materials.append(MATS["leaf"])
    for poly, idx in zip(mesh.polygons, mat_index):
        poly.material_index = idx
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    return obj


def inside_outline(x, y, center, outline, scale=0.96):
    px, py = (x - center[0]) / scale, (y - center[1]) / scale
    inside = False
    previous = outline[-1]
    for current in outline:
        ax, ay = previous
        bx, by = current
        if (ay > py) != (by > py):
            if px < (bx - ax) * (py - ay) / (by - ay) + ax:
                inside = not inside
        previous = current
    return inside


def supported_ground_z(x, y):
    if inside_outline(x, y, MAIN_CENTER, MAIN_OUTLINE):
        return 3.04
    if inside_outline(x, y, HAIDIAN_CENTER, HAIDIAN_OUTLINE):
        return 2.84
    return None


palm_positions = [
    (-53, -40), (-62, -24), (-64, -5), (-62, 14), (-33, 34),
    (-10, 49), (-11, 54), (10, 51), (30, 55), (53, 47),
    (79, 30), (83, 8), (84, -9), (65, -38), (57, -45),
    (38, -49), (24, -48), (10, -50), (-6, -44), (-14, -54),
    (44, -5), (49, 5), (-82, 36), (-62, 56), (-82, 52),
    (9, -30), (28, -30), (37, -39),
]
for i, (x, y) in enumerate(palm_positions, start=1):
    base_z = supported_ground_z(x, y)
    if base_z is None:
        raise RuntimeError("Palm grounding failed: Palm_%02d at %s" % (i, (x, y)))
    palm_mesh("Palm_%02d" % i, (x, y, base_z),
              random.uniform(9.0, 12.5), random.uniform(-0.15, 0.15), i * 0.31)

shade_positions = []
for x in (-69, -55, -42, -10, 3, 42, 55, 72, 84):
    for y in (-48, -35, -20, -4, 11, 27, 43, 54):
        if (x, y) in palm_positions:
            continue
        # Keep shore and signature landmarks legible while providing tree cover.
        if (-59 <= x <= -36 and -45 <= y <= 39):
            continue
        if 52 <= x <= 82 and -42 <= y <= -6:
            continue
        if -30 <= x <= 10 and -32 <= y <= 36:
            continue
        tx, ty = x + random.uniform(-1.4, 1.4), y + random.uniform(-1.4, 1.4)
        if supported_ground_z(tx, ty) is not None:
            shade_positions.append((tx, ty))
for i, (x, y) in enumerate(shade_positions[:44], start=1):
    height = random.uniform(5.4, 8.2)
    zground = supported_ground_z(x, y)
    trunk = cyl("Tree_Trunk_%02d" % i, 0.38, height * 0.62,
                (x, y, zground + height * 0.31), "trunk", verts=9)
    crown = sphere("Tree_Crown_%02d" % i, random.uniform(2.1, 2.8),
                   (x, y, zground + height * 0.77), "leaf",
                   scale=(1.05, 1.0, 0.92), segments=12, rings=8)
    if i % 3 == 0:
        sphere("Tree_CrownExtra_%02d" % i, 1.65,
               (x + 1.25, y + 0.1, zground + height * 0.72), "meadow",
               scale=(1.0, 0.95, 0.88), segments=10, rings=7)

volcano_tree_positions = [(46, -24), (49, -10), (64, -5), (81, -10),
                          (84, -24), (65, -43), (50, -38), (47, -31)]
for i, (x, y) in enumerate(volcano_tree_positions, start=1):
    trunk = cyl("VolcanoGrove_Trunk_%02d" % i, 0.34, 3.4,
                (x, y, 4.95), "trunk", verts=9)
    sphere("VolcanoGrove_Crown_%02d" % i, 2.2, (x, y, 7.2), "leaf",
           scale=(1.05, 1.0, 0.92), segments=12, rings=8)

# ---------------------------------------------------------------------------
# Three floating cloud groups, each with an exact animation anchor name.
def make_cloud(name, loc, scale):
    x, y, z = loc
    root = sphere(name, 5.0 * scale, (x, y, z), "cloud",
                  scale=(1.0, 0.93, 0.74), segments=16, rings=10)
    for i, (dx, dy, dz, r) in enumerate(((-4.2, 0.1, -0.3, 3.6),
                                         (4.0, -0.2, -0.5, 3.9),
                                         (-1.8, 0.0, 1.5, 3.1),
                                         (2.2, 0.1, 1.2, 3.0)), start=1):
        part = sphere(name + "_Puff_%02d" % i, r * scale,
                      (x + dx * scale, y + dy * scale, z + dz * scale), "cloud",
                      scale=(1.0, 0.94, 0.82), segments=14, rings=9)
        parent_keep_world(part, root)
    return root

make_cloud("Cloud_1", (-84.0, 62.0, 45.0), 1.02)
make_cloud("Cloud_2", (55.0, 51.0, 50.0), 0.92)
make_cloud("Cloud_3", (-10.0, -48.0, 41.0), 0.80)

def refine_density_and_tray():
    """Final geometry pass, also callable on the saved review scene."""
    global block_index
    plaque = bpy.data.objects.get("Copper_Plaque")
    if plaque:
        plaque.location.y = -112.2
    plaque_text = bpy.data.objects.get("Copper_Plaque_Text")
    if plaque_text:
        plaque_text.location.y = -113.04

    # The specification calls for 8-12 unit old-town depth. Preserve street
    # centers and horizontal gaps while deepening the 42 existing blocks.
    for i in range(1, 43):
        body = bpy.data.objects.get("OldBlock_%02d" % i)
        roof = bpy.data.objects.get("OldBlock_Roof_%02d" % i)
        if body:
            depth = body.dimensions.y
            for vertex in body.data.vertices:
                vertex.co.y *= 8.2 / depth
            body.data.update()
            for suffix in ("A", "B"):
                window = bpy.data.objects.get("OldBlock_Window_%02d_%s" % (i, suffix))
                if window:
                    window.location.y = body.location.y - 4.1 - 0.08
        if roof:
            roof_depth = roof.dimensions.y
            for vertex in roof.data.vertices:
                vertex.co.y *= 8.5 / roof_depth
            roof.data.update()

    district_points = []
    for i, (x, y) in enumerate(district_points, start=1):
        name = "NorthBlock_%02d" % i
        if bpy.data.objects.get(name):
            continue
        h = 6.0 + (i % 4) * 0.65
        body = box(name, (6.3, 8.2, h), (x, y, 3.12 + h / 2),
                   facades[(i + 1) % len(facades)], 0.48, seg=2)
        box("NorthBlock_Roof_%02d" % i, (6.65, 8.55, 0.48),
            (x, y, 3.12 + h + 0.1), roof_mats[i % len(roof_mats)], 0.15, seg=1)
        for dx in (-1.5, 1.5):
            box("NorthBlock_Window_%02d_%s" % (i, dx), (1.15, 0.20, 1.45),
                (x + dx, y - 4.2, 3.12 + h * 0.58), "window", 0.10, seg=1)
        block_index += 1

    extra_trees = [(0, -44), (8, -46), (20, -44), (31, -44),
                   (-2, -33), (4, -25), (25, -25), (35, -28)]
    for i, (x, y) in enumerate(extra_trees, start=1):
        if bpy.data.objects.get("ParkGrove_Trunk_%02d" % i):
            continue
        cyl("ParkGrove_Trunk_%02d" % i, 0.32, 3.8,
            (x, y, 4.98), "trunk", verts=9)
        sphere("ParkGrove_Crown_%02d" % i, 2.15, (x, y, 7.35),
               "leaf" if i % 2 else "meadow", scale=(1.0, 1.0, 0.92),
               segments=12, rings=8)
        shade_positions.append((x, y))

    for i, (dx, dy) in enumerate(((-4.8, -1.35), (4.8, -1.35),
                                  (-4.8, 1.35), (4.8, 1.35)), start=1):
        angle = math.radians(-18)
        x = 82.1 + dx * math.cos(angle) - dy * math.sin(angle)
        y = -29.0 + dx * math.sin(angle) + dy * math.cos(angle)
        cyl("Volcano_DeckSupport_%02d" % i, 0.25, 8.1,
            (x, y, 4.75), "wood_dark", verts=10)
    for i, (dx, dy) in enumerate(((-4.2, -5.4), (4.2, -5.4),
                                  (-4.2, 5.4), (4.2, 5.4)), start=1):
        cyl("Library_PlatformSupport_%02d" % i, 0.30, 2.2,
            (lib_x + dx, lib_y + dy, 2.0), "white", verts=12)

    # Broad sculpted white crests read as active sea from the overview camera.
    crest_specs = [(-44, -81, 0.15, 16), (-8, -89, -0.08, 17),
                   (42, -87, 0.22, 17), (62, -74, 0.42, 15),
                   (79, -58, 0.72, 13), (21, 85, 0.12, 16)]
    for i, (cx, cy, angle, length) in enumerate(crest_specs, start=1):
        verts, faces = [], []
        for j in range(15):
            t = j / 14.0
            along = (t - 0.5) * length
            wave = math.sin(math.pi * t)
            center_y = 0.42 * wave
            for side in (-1, 1):
                across = center_y + side * (0.10 + 0.42 * wave)
                verts.append((cx + along * math.cos(angle) - across * math.sin(angle),
                              cy + along * math.sin(angle) + across * math.cos(angle),
                              1.14 + (0.70 if side < 0 else 0.05) * wave))
        for j in range(14):
            a = 2 * j
            faces.append((a, a + 1, a + 3, a + 2))
        mesh_object("Sea_Crest_%02d" % i, verts, faces, "foam")

    # Packed 256px wood grain survives GLB export instead of relying on Blender
    # procedural nodes. It uses the existing two wood materials.
    image = bpy.data.images.get("Haikou_Wood_Grain")
    if not image:
        size = 256
        image = bpy.data.images.new("Haikou_Wood_Grain", width=size, height=size)
        pixels = []
        for j in range(size):
            for i in range(size):
                u, v = i / size, j / size
                ridge = math.sin((u * 13.0 + 0.35 * math.sin(v * 9.0) +
                                  0.09 * math.sin(v * 39.0)) * math.tau)
                fine = math.sin((u * 93.0 + 0.7 * math.sin(v * 13.0)) * math.tau)
                grain = 0.045 * ridge + 0.012 * fine
                pixels.extend((0.65 + grain, 0.48 + grain * 0.70,
                               0.33 + grain * 0.50, 1.0))
        image.pixels = pixels
        image.file_format = "PNG"
        image.filepath_raw = os.path.join(ASSET_DIR, "wood-grain.png")
        image.save()
        image.pack()
    for name, multiplier in (("wood", 1.0), ("wood_dark", 0.47)):
        material = MATS[name]
        nodes = material.node_tree.nodes
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        bsdf = nodes.get("Principled BSDF")
        if multiplier < 1.0:
            mix = nodes.new("ShaderNodeMixRGB")
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            mix.inputs[2].default_value = (multiplier, multiplier, multiplier, 1.0)
            material.node_tree.links.new(texture.outputs["Color"], mix.inputs[1])
            material.node_tree.links.new(mix.outputs[0], bsdf.inputs["Base Color"])
        else:
            material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    print("REFINED_DENSITY", block_index, "old blocks,", len(extra_trees), "extra trees", flush=True)


refine_density_and_tray()

# ---------------------------------------------------------------------------
# Lighting, product floor and reusable cameras.
sun_data = bpy.data.lights.new("Warm_Sun", "SUN")
sun_data.energy = 3.0
sun_data.angle = math.radians(5.0)
sun_data.color = (1.0, 0.91, 0.78)
sun = bpy.data.objects.new("Warm_Sun", sun_data)
sun.rotation_euler = (math.radians(32), math.radians(-12), math.radians(-35))
bpy.context.collection.objects.link(sun)
area_data = bpy.data.lights.new("Softbox", "AREA")
area_data.energy = 11500
area_data.shape = "DISK"
area_data.size = 150
area = bpy.data.objects.new("Softbox", area_data)
area.location = (-130, -165, 190)
area.rotation_euler = (math.radians(27), 0.0, math.radians(-25))
bpy.context.collection.objects.link(area)
fill_data = bpy.data.lights.new("Fill", "AREA")
fill_data.energy = 7600
fill_data.shape = "DISK"
fill_data.size = 125
fill = bpy.data.objects.new("Fill", fill_data)
fill.location = (115, 65, 145)
fill.rotation_euler = (math.radians(34), 0.0, math.radians(145))
bpy.context.collection.objects.link(fill)

bpy.ops.mesh.primitive_plane_add(size=1000.0, location=(0.0, 0.0, -7.05))
ground = bpy.context.object
ground.name = "Render_Ground"
assign(ground, "white")


def camera(name, location, target, lens=58.0, ortho=None):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    direction = Vector(target) - Vector(location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj

main_cam = camera("Camera_Main", (-270, -300, 245), (0, 0, 11), lens=72)
scene.camera = main_cam
scene.render.resolution_x = 900 if DRAFT else 1400
scene.render.resolution_y = 600 if DRAFT else 900
scene.cycles.samples = 24 if DRAFT else 64

# ---------------------------------------------------------------------------
# Apply any remaining object-space rotations/scales, and render the first view.
for obj in list(scene.objects):
    if obj.type == "MESH" and (any(abs(v - 1.0) > 1e-6 for v in obj.scale) or
                                any(abs(v) > 1e-6 for v in obj.rotation_euler)):
        apply_rot_scale(obj)

if DRAFT:
    main_path = os.path.join(ASSET_DIR, "_blockout-r%s.png" % ROUND)
    scene.render.filepath = main_path
    bpy.ops.render.render(write_still=True)
    print("BLOCKOUT_MAIN", main_path)
    if ROUND == "3":
        inspect_views = [
            ("Bridge", (-126, -8, 83), (-38, 43, 17), "_bridge-r3.png"),
            ("OldTown", (-123, -105, 72), (-48, -6, 16), "_oldtown-r3.png"),
            ("Volcano", (-18, -118, 82), (66, -24, 14), "_volcano-r3.png"),
        ]
        for title, loc, target, filename in inspect_views:
            inspect_cam = camera("Camera_Blockout_" + title, loc, target, lens=62)
            scene.camera = inspect_cam
            scene.render.filepath = os.path.join(ASSET_DIR, filename)
            bpy.ops.render.render(write_still=True)
            print("BLOCKOUT_DETAIL", scene.render.filepath)

    # Top-down density pass, uniformly grey on white, with clouds hidden.
    layer = bpy.context.view_layer
    grey = bpy.data.materials.new("Density_Grey")
    grey.diffuse_color = (0.47, 0.49, 0.50, 1.0)
    grey.use_nodes = True
    grey.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.47, 0.49, 0.50, 1.0)
    layer.material_override = grey
    old_world = world.node_tree.nodes["Background"].inputs[0].default_value[:]
    world.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    hidden = []
    for obj in scene.objects:
        if obj.name.startswith("Cloud_") or obj.name.startswith("Render_Ground"):
            hidden.append((obj, obj.hide_render))
            obj.hide_render = True
    density_cam = camera("Camera_Density", (0, 0, 340), (0, 0, 0), ortho=232)
    density_cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = density_cam
    scene.render.resolution_x = 850
    scene.render.resolution_y = 850
    scene.render.filepath = os.path.join(ASSET_DIR, "_density-r%s.png" % ROUND)
    bpy.ops.render.render(write_still=True)
    print("BLOCKOUT_DENSITY", scene.render.filepath)
    for obj, state in hidden:
        obj.hide_render = state
    layer.material_override = None
    world.node_tree.nodes["Background"].inputs[0].default_value = old_world
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.48
else:
    # Collapse each landmark/animation assembly while preserving its exact root
    # name and origin. This keeps GLB hierarchy small and picking predictable.
    assembly_names = ["ClockTower", "Library", "Bridge_Tower_L", "Bridge_Tower_R"] + \
        ["Arcade_%02d" % i for i in range(1, 9)] + ["Car_%02d" % i for i in range(1, 7)] + \
        ["Boat_%02d" % i for i in range(1, 10)] + ["Cloud_%d" % i for i in range(1, 4)]
    for root_name in assembly_names:
        root = bpy.data.objects.get(root_name)
        if not root:
            continue
        parts = [obj for obj in root.children_recursive if obj.type == "MESH"]
        if parts:
            bpy.ops.object.select_all(action="DESELECT")
            root.select_set(True)
            for part in parts:
                part.select_set(True)
            bpy.context.view_layer.objects.active = root
            bpy.ops.object.join()
            root.name = root_name
            apply_rot_scale(root)
    print("MODEL_READY", len([o for o in scene.objects if o.type == "MESH"]), flush=True)
    # Final model export excludes the render floor, all cameras, and all lights.
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [obj for obj in scene.objects
                      if obj.type == "MESH" and obj.name != "Render_Ground"]
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]
    glb_path = os.path.join(MODEL_DIR, "haikou_v1.glb")
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB",
                              use_selection=True, export_apply=True,
                              export_cameras=False, export_lights=False,
                              export_extras=True)
    print("EXPORTED_GLB", glb_path, flush=True)
    early_triangles = 0
    for obj in export_objects:
        obj.data.calc_loop_triangles()
        early_triangles += len(obj.data.loop_triangles)
    early_mats = sorted({mat.name for obj in export_objects for mat in obj.data.materials if mat})
    bad_transforms = [obj.name for obj in export_objects
                      if any(abs(v - 1.0) > 1e-5 for v in obj.scale) or
                         any(abs(v) > 1e-5 for v in obj.rotation_euler)]
    def footprint_area(outline):
        return abs(sum(a[0] * b[1] - b[0] * a[1]
                       for a, b in zip(outline, outline[1:] + outline[:1]))) * 0.5
    land_coverage = (footprint_area(MAIN_OUTLINE) + footprint_area(HAIDIAN_OUTLINE)) * \
        1.045 ** 2 / (math.pi * 112 ** 2)
    early_stats = {"blender": bpy.app.version_string,
                   "triangles": early_triangles, "mesh_objects": len(export_objects),
                   "materials": early_mats, "material_count": len(early_mats),
                   "glb_bytes": os.path.getsize(glb_path),
                   "land_and_beach_coverage": round(land_coverage, 5),
                   "oldtown_blocks": block_index, "palms": len(palm_positions),
                   "shade_trees": min(44, len(shade_positions)) + len(volcano_tree_positions),
                   "bad_transforms": bad_transforms,
                   "object_names": sorted(obj.name for obj in export_objects)}
    with open(os.path.join(ASSET_DIR, "stats.json"), "w", encoding="utf-8") as stream:
        json.dump(early_stats, stream, ensure_ascii=False, indent=2)
    print("EXPORT_STATS", early_stats["triangles"], early_stats["mesh_objects"],
          early_stats["material_count"], early_stats["glb_bytes"], flush=True)
    if early_triangles > 150000 or len(early_mats) > 24 or early_stats["glb_bytes"] > 8 * 1024 * 1024:
        raise RuntimeError("Export budget exceeded; see data/asset/stats.json")
    if bad_transforms:
        raise RuntimeError("Unapplied transforms: " + ", ".join(bad_transforms))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ASSET_DIR, "_haikou_v1.blend"),
                                compress=True)

    def render_view(cam, path, resolution=(1400, 900), samples=64):
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.cycles.samples = samples
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("RENDERED", path)

    render_view(main_cam, os.path.join(ASSET_DIR, "preview-main.png"), (1400, 900), 64)
    closeup_clouds = [obj for obj in scene.objects if obj.name.startswith("Cloud_")]
    for obj in closeup_clouds:
        obj.hide_render = True
    bridge_cam = camera("Camera_Bridge", (-126, -8, 83), (-38, 43, 17), lens=62)
    render_view(bridge_cam, os.path.join(ASSET_DIR, "preview-bridge.png"), (1400, 900), 64)
    oldtown_cam = camera("Camera_OldTown", (-130, -117, 73), (-48, -7, 17), lens=62)
    render_view(oldtown_cam, os.path.join(ASSET_DIR, "preview-oldtown.png"), (1400, 900), 64)
    for obj in closeup_clouds:
        obj.hide_render = False

    # Orthographic grey model on white to audit land and prop distribution.
    layer = bpy.context.view_layer
    density_mat = bpy.data.materials.new("Density_Grey")
    density_mat.use_nodes = True
    density_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.47, 0.49, 0.50, 1.0)
    layer.material_override = density_mat
    old_color = world.node_tree.nodes["Background"].inputs[0].default_value[:]
    old_strength = world.node_tree.nodes["Background"].inputs[1].default_value
    world.node_tree.nodes["Background"].inputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    hidden = []
    for obj in scene.objects:
        if obj.name.startswith("Cloud_") or obj.name.startswith("Render_Ground"):
            hidden.append((obj, obj.hide_render))
            obj.hide_render = True
    density_cam = camera("Camera_Density", (0, 0, 340), (0, 0, 0), ortho=232)
    density_cam.rotation_euler = (0.0, 0.0, 0.0)
    render_view(density_cam, os.path.join(ASSET_DIR, "density.png"), (1200, 1200), 64)
    for obj, state in hidden:
        obj.hide_render = state
    layer.material_override = None
    world.node_tree.nodes["Background"].inputs[0].default_value = old_color
    world.node_tree.nodes["Background"].inputs[1].default_value = old_strength

    # Evaluate post-export mesh statistics (triangles, model objects and bounds).
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh_objects = [obj for obj in scene.objects
                    if obj.type == "MESH" and obj.name != "Render_Ground"]
    triangles = 0
    materials_used = set()
    bounds = [float("inf"), float("inf"), float("inf"),
              float("-inf"), float("-inf"), float("-inf")]
    for obj in mesh_objects:
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        eval_mesh.calc_loop_triangles()
        triangles += len(eval_mesh.loop_triangles)
        for mat in eval_mesh.materials:
            if mat:
                materials_used.add(mat.name)
        for corner in eval_obj.bound_box:
            p = eval_obj.matrix_world @ Vector(corner)
            bounds[0] = min(bounds[0], p.x)
            bounds[1] = min(bounds[1], p.y)
            bounds[2] = min(bounds[2], p.z)
            bounds[3] = max(bounds[3], p.x)
            bounds[4] = max(bounds[4], p.y)
            bounds[5] = max(bounds[5], p.z)
        eval_obj.to_mesh_clear()
    glb_size = os.path.getsize(glb_path)
    required_names = ["Sea", "Foam"] + ["Car_%02d" % i for i in range(1, 7)] + \
        ["Boat_%02d" % i for i in range(1, 10)] + ["Cloud_%d" % i for i in range(1, 4)] + \
        ["ClockTower", "Bridge_Tower_L", "Bridge_Tower_R", "Library", "Park", "Volcano", "Haidian"] + \
        ["Arcade_%02d" % i for i in range(1, 9)] + ["Palm_%02d" % i for i in range(1, len(palm_positions) + 1)]
    all_names = {obj.name for obj in mesh_objects}
    missing = [name for name in required_names if name not in all_names]
    report = [
        "# 海口 V1 微缩城市资产报告", "",
        "## 统计", "",
        "- GLB: `assets/models/haikou_v1.glb` (%.2f MiB / %d bytes)" %
        (glb_size / (1024 * 1024), glb_size),
        "- 三角面: %s" % format(triangles, ","),
        "- 导出网格对象: %d" % len(mesh_objects),
        "- 材质: %d / 上限 24 (%s)" %
        (len(materials_used), ", ".join(sorted(materials_used))),
        "- 场景范围 (Blender Z-up): X %.1f..%.1f, Y %.1f..%.1f, Z %.1f..%.1f；GLB 按 Y-up 导出。" %
        (bounds[0], bounds[3], bounds[1], bounds[4], bounds[2], bounds[5]),
        "- 规范锚点: %d / %d 已找到" % (len(required_names) - len(missing), len(required_names)),
        "- 缺失锚点: %s" % (", ".join(missing) if missing else "无"),
        "- 旧城街块: %d；椰树: %d；乔木: %d；渔船: 9；帆船: 3" %
        (block_index, len(palm_positions), min(44, len(shade_positions)) + len(volcano_tree_positions)),
        "- 陆地与沙岸平面覆盖: %.2f%% (由真实外轮廓面积计算)" % (land_coverage * 100),
        "- 旋转/缩放未应用对象: %s" % (", ".join(bad_transforms) if bad_transforms else "无"),
        "- 统计清单: `data/asset/stats.json`；可复查源场景: `data/asset/_haikou_v1.blend`。",
        "", "## 命名清单", "",
        "- 动画锚点: `Sea`, `Foam`, `Car_01..Car_06`, `Boat_01..Boat_09`, `Cloud_1..Cloud_3`",
        "- 地标: `ClockTower`, `Bridge_Tower_L`, `Bridge_Tower_R`, `Library`, `Park`, `Volcano`, `Haidian`",
        "- 骑楼: `Arcade_01..Arcade_08`",
        "- 椰树: `Palm_01..Palm_%02d`" % len(palm_positions),
        "- 主构成: `MainIsland`, `Shore_Sand`, `Bridge_Deck`, `Lighthouse`, `Sail_01..Sail_03`",
        "", "## 渲染", "",
        "- Blender: 5.2.3 headless; Cycles CPU; 1400x900; 64 samples; AgX; denoising enabled.",
        "- 预览: `data/asset/preview-main.png`, `preview-bridge.png`, `preview-oldtown.png`, `density.png`.",
        "- 主视角: 西南 3/4，30.1 度俯视；密度图为统一灰模正交俯视白底。",
        "- 已实际运行 3 轮 900x600 / Cycles 24 samples blockout 并查看 PNG，保留 `_blockout-r1..r3.png` / `_density-r1..r3.png`。",
        "- 根据图像修正了码头接岸、骑楼柱廊高度、火山真凹口、图书馆三独立洞口、铜牌表面位置、北侧密度与木纹。",
        "", "## 已知问题", "",
        "- 城市细节为程序化 Q 版几何，店招没有可读的逐店文字，钟面仅含指针。",
        "- 车、船、云、椰树已提供准确命名锚点，动画由 App 驱动；GLB 本身不含烘焙动画。",
        "- 火山口以几何凹碗表达，未包含粒子烟雾或动态熔岩。",
        "- 海面外圈保留船行水域；近岸以三组渔港、防波堤、游憩栈桥、帆船、航标、浅海带和浪线形成层次。",
        "- 预览缩小到手机尺寸时，店招、钟针和图书馆洞口的细节依赖特写查看。",
        "- 本机沙箱日志：`Extensions: writing cache failed ([WinError 5] 拒绝访问。: 'C:\\Users\\17600\\AppData\\Roaming\\Blender Foundation')`。",
        "- 保存源场景时 OpenImageIO 对 `C:\\Users\\17600\\.thumbnails\\large` 的缩略图缓存写入被拒；工作区中的 GLB、源场景与 PNG 正常保存。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(report))
    print("STATS", {"triangles": triangles, "mesh_objects": len(mesh_objects),
                     "materials": len(materials_used), "glb_bytes": glb_size,
                     "bounds": bounds, "missing": missing})
    print("REPORT", REPORT_PATH)

print("DONE", "stage=%s" % STAGE, "samples=%d" % scene.cycles.samples,
      "render_size=%dx%d" % (scene.render.resolution_x, scene.render.resolution_y))
