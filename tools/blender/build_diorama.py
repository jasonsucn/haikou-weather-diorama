"""Q-style Haikou weather diorama 鈥?pilot scene v3 (coastal composition).

Sea in the foreground, Haidian Island across the bay on the left, the Century
Bridge (涓栫邯澶фˉ) crossing the water as the hero silhouette, the Qilou arcade
street (楠戞ゼ鑰佽) + clock tower (閽熸ゼ) along the waterfront, Cloud Cave Library
(浜戞礊鍥句功棣?, CBD towers, palms, boats and clouds.

Run:
  blender --background --factory-startup --python tools/blender/build_diorama.py
Env:
  DIORAMA_DRAFT=0  -> final resolution / samples
"""
import bpy
import math
import os
import random
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(ROOT, "..", ".."))
DRAFT = os.environ.get("DIORAMA_DRAFT", "1") == "1"
random.seed(11)

bpy.ops.wm.read_factory_settings(use_empty=True)

# ---------------------------------------------------------------- palette
PALETTE = {
    "plinth":    ((0.56, 0.46, 0.33), 0.8),
    "plinth2":   ((0.30, 0.21, 0.16), 0.85),
    "sea":       ((0.03, 0.29, 0.43), 0.10),
    "foam":      ((0.88, 0.94, 0.93), 0.7),
    "sand":      ((0.93, 0.78, 0.48), 0.9),
    "grass":     ((0.34, 0.56, 0.26), 0.95),
    "road":      ((0.72, 0.70, 0.64), 0.9),
    "cream":     ((0.97, 0.89, 0.71), 0.8),
    "terracotta": ((0.83, 0.38, 0.25), 0.75),
    "butter":    ((0.98, 0.75, 0.34), 0.75),
    "mint":      ((0.40, 0.70, 0.56), 0.72),
    "skyblue":   ((0.40, 0.61, 0.80), 0.72),
    "teal":      ((0.09, 0.36, 0.38), 0.5),
    "coral":     ((0.92, 0.43, 0.32), 0.6),
    "white":     ((0.97, 0.95, 0.90), 0.45),
    "glass":     ((0.52, 0.71, 0.83), 0.18),
    "dark":      ((0.19, 0.21, 0.24), 0.65),
    "gold":      ((0.93, 0.69, 0.28), 0.3),
    "brick":     ((0.63, 0.27, 0.20), 0.85),
    "trunk":     ((0.51, 0.36, 0.23), 0.9),
    "leaf":      ((0.18, 0.50, 0.29), 0.75),
    "cloud":     ((0.99, 0.99, 1.00), 0.95),
    "window":    ((0.25, 0.40, 0.48), 0.22),
    "car1":      ((0.96, 0.58, 0.26), 0.35),
    "car2":      ((0.84, 0.28, 0.26), 0.35),
    "car3":      ((0.28, 0.56, 0.78), 0.35),
    "hill":      ((0.36, 0.58, 0.34), 0.95),
    "roof_red":  ((0.71, 0.30, 0.23), 0.8),
    "roof_teal": ((0.14, 0.42, 0.42), 0.55),
    "tree":      ((0.22, 0.53, 0.31), 0.85),
}
MATS = {}
for name, (rgb, rough) in PALETTE.items():
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    MATS[name] = m

# ---------------------------------------------------------------- helpers
def apply_mods(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)


def smooth(obj, angle=36.0):
    for p in obj.data.polygons:
        p.use_smooth = True
    mod = obj.modifiers.new("edge", "EDGE_SPLIT")
    mod.split_angle = math.radians(angle)
    apply_mods(obj)


def box(name, size, loc, mat, bevel=0.5, rot=(0, 0, 0), seg=3, do_smooth=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_euler = rot
    o.data.materials.append(MATS[mat])
    if bevel > 0:
        bw = min(bevel, min(size) * 0.45)
        mod = o.modifiers.new("bev", "BEVEL")
        mod.width = bw
        mod.segments = seg
        mod.limit_method = "ANGLE"
        apply_mods(o)
    if do_smooth:
        smooth(o)
    return o


def cyl(name, r, depth, loc, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(MATS[mat])
    smooth(o, 50)
    return o


def cone(name, r1, r2, depth, loc, mat, verts=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(MATS[mat])
    smooth(o, 50)
    return o


def sphere(name, r, loc, mat, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=26, ring_count=14, radius=r,
                                         location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(MATS[mat])
    smooth(o, 80)
    return o


def cyl_between(name, p1, p2, r, mat, verts=8):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d.length,
                                        location=(p1 + p2) / 2)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(MATS[mat])
    smooth(o, 50)
    return o


def disc(name, r, depth, loc, mat, rot=(0, 0, 0)):
    return cyl(name, r, depth, loc, mat, rot=rot, verts=36)


# ---------------------------------------------------------------- scene
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 28 if DRAFT else 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 960 if DRAFT else 1400
scene.render.resolution_y = 640 if DRAFT else 900
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = -0.1

world = bpy.data.worlds.new("sky")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.46, 0.68, 0.88, 1.0)
bg.inputs[1].default_value = 0.38

# ---------------------------------------------------------------- base + water tray
box("plinth_base", (222, 162, 6), (0, 0, -3.5), "plinth2", bevel=6.0, seg=5)
box("sea", (208, 148, 1.6), (0, 0, 0.3), "sea", bevel=2.0, seg=3)
box("tray_n", (216, 9, 2.3), (0, 76.5, 1.1), "plinth", bevel=1.2, seg=3)
box("tray_s", (216, 9, 2.3), (0, -76.5, 1.1), "plinth", bevel=1.2, seg=3)
box("tray_e", (9, 158, 2.3), (103.5, 0, 1.1), "plinth", bevel=1.2, seg=3)
box("tray_w", (9, 158, 2.3), (-103.5, 0, 1.1), "plinth", bevel=1.2, seg=3)

# ---------------------------------------------------------------- land mass (coast on the west/south)
LAND = 2.4
box("mainland", (150, 94, LAND), (45, -5, LAND / 2), "grass", bevel=14.0, seg=6)
box("island", (54, 30, LAND), (-70, 50, LAND / 2), "grass", bevel=9.0, seg=5)
box("main_foam", (156, 100, 0.3), (45, -5, 1.05), "foam", bevel=14.0, seg=4)
box("isl_foam", (60, 36, 0.3), (-70, 50, 1.05), "foam", bevel=9.0, seg=4)
box("main_sand", (152, 96, 0.9), (45, -5, 1.35), "sand", bevel=14.0, seg=4)
box("isl_sand", (56, 32, 0.9), (-70, 50, 1.35), "sand", bevel=9.0, seg=4)

# ---------------------------------------------------------------- roads
box("road_coast", (5.4, 88, 0.45), (-26, -2, LAND + 0.2), "road", bevel=1.4, seg=2)
box("road_avenue", (108, 6.2, 0.45), (34, -30, LAND + 0.2), "road", bevel=1.5, seg=2)
box("road_cross", (5.8, 70, 0.45), (36, -10, LAND + 0.2), "road", bevel=1.5, seg=2)
box("road_isl", (44, 5.0, 0.45), (-70, 42, LAND + 0.2), "road", bevel=1.2, seg=2)

# ---------------------------------------------------------------- Century Bridge (rotated group)
span, deck_z = 40.0, 13.5
ang = math.radians(-37)
root = bpy.data.objects.new("bridge_root", None)
root.location = (-50, 35, 0)
root.rotation_euler = (0, 0, ang)
bpy.context.collection.objects.link(root)


def br(name, size, loc, mat, **kw):
    o = box(name, size, loc, mat, **kw)
    o.parent = root
    return o


def br_cyl(name, p1, p2, r, mat, verts=6):
    o = cyl_between(name, p1, p2, r, mat, verts=verts)
    o.parent = root
    return o


br("deck", (span, 10, 1.7), (0, 0, deck_z), "white", bevel=1.3, seg=3)
br("girder_l", (span, 1.0, 1.3), (0, -5.0, deck_z - 1.1), "white", bevel=0.4, seg=2)
br("girder_r", (span, 1.0, 1.3), (0, 5.0, deck_z - 1.1), "white", bevel=0.4, seg=2)
br("rail_l", (span, 0.5, 1.4), (0, -5.4, deck_z + 1.2), "coral", bevel=0.2, seg=2)
br("rail_r", (span, 0.5, 1.4), (0, 5.4, deck_z + 1.2), "coral", bevel=0.2, seg=2)
for px in (-17.5, 17.5):
    for py in (-4.0, 4.0):
        br(f"pier_{px}_{py}", (2.6, 2.6, deck_z + 1.0), (px, py, (deck_z + 1.0) / 2),
           "white", bevel=0.4, seg=2)
TOP = deck_z + 33.0
for tx_ in (-10.0, 10.0):
    for py in (-4.4, 4.4):
        br(f"leg_{tx_}_{py}", (2.2, 2.4, 35), (tx_, py, deck_z + 16.5), "white",
           bevel=0.7, seg=3)
    br(f"beam_{tx_}", (3.0, 11.0, 2.2), (tx_, 0, TOP), "white", bevel=0.6, seg=3)
    br(f"beam2_{tx_}", (2.6, 10.4, 1.8), (tx_, 0, deck_z + 9.0), "white",
       bevel=0.5, seg=3)
    br(f"cap_{tx_}", (3.4, 3.0, 2.4), (tx_, 0, TOP + 1.0), "coral", bevel=0.5, seg=3)
    for i in range(8):
        dx = 2.4 + i * 2.4
        for side in (-1, 1):
            br_cyl(f"cab_{tx_}_{i}_{side}",
                   (tx_ + side * dx, -4.2, deck_z + 1.0),
                   (tx_ + side * 1.0, 0, TOP - 1.0), 0.10, "white")

car_mats = ["car1", "car2", "car3", "butter"]
for i, (cx_, cm) in enumerate(zip((-14, -8, -2, 6, 12, 16), car_mats * 2)):
    box(f"car_{i}", (3.8, 2.2, 1.3), (cx_, -2.2 + (i % 2) * 4.4, deck_z + 1.8),
        cm, bevel=0.45, seg=2).parent = root
    box(f"car_top_{i}", (2.1, 1.9, 0.9), (cx_, -2.2 + (i % 2) * 4.4, deck_z + 2.7),
        "window", bevel=0.35, seg=2).parent = root

for ab in (19.5, -19.5):
    box(f"abutment_{ab}", (7.0, 12.0, 4.0), (root.location.x + ab * math.cos(ang),
        root.location.y + ab * math.sin(ang), 2.2), "sand", bevel=1.2, seg=3)

# ---------------------------------------------------------------- Qilou arcade street (faces west)
FACADES = ["cream", "terracotta", "butter", "mint", "skyblue", "cream"]
ROOFS = ["roof_teal", "roof_red", "roof_teal", "roof_red", "roof_teal", "roof_red"]
unit_w, unit_d = 9.8, 12.0
front_x = -25.0
start_y = -30.0
N = 7
for i in range(N):
    y = start_y + i * (unit_w + 0.25)
    h = 12.0 + (i % 3) * 1.0
    fac = FACADES[i % len(FACADES)]
    roof = ROOFS[i % len(ROOFS)]
    box(f"ql_body_{i}", (unit_d, unit_w, h - 4.2), (front_x + unit_d / 2, y,
        4.2 + (h - 4.2) / 2), fac, bevel=0.9, seg=3)
    for k in range(3):
        cy = y - unit_w / 2 + 1.0 + k * (unit_w - 2.0) / 2
        cyl(f"ql_col_{i}_{k}", 0.62, 4.2, (front_x - 0.7, cy, 2.1), "cream", verts=20)
        box(f"ql_cap_{i}_{k}", (1.6, 1.6, 0.5), (front_x - 0.7, cy, 4.35), "cream",
            bevel=0.35, seg=2)
    box(f"ql_back_{i}", (1.0, unit_w, 4.2), (front_x + unit_d - 0.5, y, 2.1), fac,
        bevel=0.4, seg=2)
    box(f"ql_shop_{i}", (0.5, unit_w - 3.0, 3.0), (front_x + 1.2, y, 1.8), "window",
        bevel=0.35, seg=2)
    box(f"ql_awn_{i}", (3.2, unit_w - 1.6, 0.4), (front_x - 0.9, y, 4.1),
        "coral" if i % 2 else "mint", bevel=0.25, seg=2, rot=(0, math.radians(12), 0))
    for row, wz in enumerate((h - 2.6, h - 5.6)):
        for wy in (-2.7, 2.7):
            box(f"ql_frame_{i}_{row}_{wy}", (0.35, 2.8, 2.3),
                (front_x - 0.05, y + wy, wz), "white", bevel=0.26, seg=2)
            box(f"ql_win_{i}_{row}_{wy}", (0.3, 2.1, 1.7),
                (front_x - 0.18, y + wy, wz), "window", bevel=0.24, seg=2)
            box(f"ql_shut_{i}_{row}_{wy}", (0.3, 0.5, 1.7),
                (front_x - 0.2, y + wy - 1.45, wz), "mint", bevel=0.14, seg=1)
    box(f"ql_parapet_{i}", (0.9, unit_w, 1.1), (front_x + 0.4, y, h + 0.45), "white",
        bevel=0.35, seg=2)
    box(f"ql_roof_{i}", (unit_d, unit_w, 0.6), (front_x + unit_d / 2, y, h + 0.25),
        roof, bevel=0.45, seg=2)
    cyl(f"ql_tank_{i}", 1.05, 1.8, (front_x + 3.2, y + 2.4, h + 1.2), "white", verts=14)
    box(f"ql_sign_{i}", (0.4, 1.3, 3.0), (front_x - 0.5, y - unit_w / 2 + 0.2, 7.4),
        "butter" if i % 2 else "white", bevel=0.2, seg=2)

# ---------------------------------------------------------------- clock tower
tx, ty = -22.0, -40.0
box("clock_base", (11, 11, 10), (tx, ty, 7.3), "brick", bevel=1.0, seg=3)
box("clock_shaft", (8.0, 8.0, 14), (tx, ty, 19.3), "white", bevel=0.9, seg=3)
box("clock_cornice", (10.4, 10.4, 1.4), (tx, ty, 12.5), "brick", bevel=0.6, seg=3)
box("clock_cornice2", (9.4, 9.4, 1.2), (tx, ty, 26.7), "brick", bevel=0.5, seg=3)
for a_deg in (0, 90, 180, 270):
    a = math.radians(a_deg)
    nx, ny = math.sin(a), math.cos(a)
    disc(f"clock_face_{a_deg}", 2.9, 0.4, (tx + nx * 3.9, ty + ny * 3.9, 23.5),
         "cream", rot=(math.radians(90), 0, a))
    disc(f"clock_ring_{a_deg}", 3.2, 0.3, (tx + nx * 4.05, ty + ny * 4.05, 23.5),
         "gold", rot=(math.radians(90), 0, a))
    box(f"clock_hour_{a_deg}", (1.9, 0.3, 0.25), (tx + nx * 4.25, ty + ny * 4.25,
        23.5), "dark", bevel=0.08, seg=1, rot=(0, 0, a))
    box(f"clock_min_{a_deg}", (1.3, 0.22, 0.22), (tx + nx * 4.3, ty + ny * 4.3,
        24.2), "dark", bevel=0.06, seg=1, rot=(0, 0, a + 0.6))
box("clock_top", (6.6, 6.6, 1.2), (tx, ty, 28.1), "white", bevel=0.4, seg=2)
cone("clock_roof", 5.6, 0.7, 6.4, (tx, ty, 31.8), "roof_teal", verts=4)
cyl("clock_spire", 0.28, 3.6, (tx, ty, 36.7), "gold", verts=10)
sphere("clock_ball", 0.7, (tx, ty, 38.9), "gold")

# ---------------------------------------------------------------- Cloud Cave Library
cx, cy, cz = -20.0, 8.0, 8.0
lib = sphere("cloud_lib", 1.0, (cx, cy, cz), "white", scale=(6.2, 9.2, 5.0))
for i, (ox, oy, oz, rr) in enumerate(((0.0, -3.0, 1.2, 1.9), (0.0, 2.8, 1.9, 1.5),
                                      (0.0, 0.2, 3.5, 1.1))):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=rr, depth=26,
                                        location=(cx + ox, cy + oy, cz + oz),
                                        rotation=(math.radians(90), 0, 0))
    cut = bpy.context.object
    boo = lib.modifiers.new(f"cut{i}", "BOOLEAN")
    boo.operation = "DIFFERENCE"
    boo.object = cut
    apply_mods(lib)
    bpy.data.objects.remove(cut, do_unlink=True)
smooth(lib, 50)
box("lib_base", (9.0, 13.0, 1.2), (cx, cy, 2.9), "sand", bevel=2.2, seg=3)

# ---------------------------------------------------------------- CBD towers
towers = [
    (8, 8, 9, 9, 34, "skyblue"),
    (22, 14, 8, 8, 44, "glass"),
    (36, 6, 10, 10, 30, "white"),
    (52, 16, 11, 11, 50, "skyblue"),
    (66, 4, 9, 9, 36, "white"),
]
for i, (x, y, w, d, h, m) in enumerate(towers):
    box(f"tower_{i}", (w, d, h), (x, y, LAND + h / 2), m, bevel=2.6, seg=4)
    for k in range(4):
        box(f"tower_band_{i}_{k}", (w + 0.5, d + 0.5, 0.6),
            (x, y, LAND + 6 + k * (h - 8) / 3.6), "white", bevel=0.2, seg=1)
    box(f"tower_cap_{i}", (w * 0.62, d * 0.62, 2.2), (x, y, LAND + h + 1.1), "white",
        bevel=0.8, seg=3)

# ---------------------------------------------------------------- filler blocks behind the arcade
FILL = ["cream", "butter", "mint", "terracotta", "skyblue", "white"]
for i in range(22):
    x = 0 + (i % 7) * 12.0 + random.uniform(-1.5, 1.5)
    y = -18 + (i // 7) * 10.5 + random.uniform(-1.0, 1.0)
    w = random.uniform(6.0, 8.5)
    d = random.uniform(6.0, 8.0)
    h = random.uniform(6, 10)
    box(f"fill_{i}", (w, d, h), (x, y, LAND + h / 2), FILL[i % len(FILL)],
        bevel=0.9, seg=3)
    if i % 3 == 0:
        cone(f"fill_roof_{i}", w * 0.75, 0.35, 3.0, (x, y, LAND + h + 1.5),
             "roof_red", verts=4)

# ---------------------------------------------------------------- island village + hill + lighthouse
for i in range(7):
    x = -88 + i * 9.0
    y = 48 + (i % 2) * 4
    w, d, h = random.uniform(5.5, 7.0), random.uniform(5.5, 7.0), random.uniform(5, 8)
    box(f"village_{i}", (w, d, h), (x, y, LAND + h / 2), FILL[i % len(FILL)],
        bevel=0.8, seg=3)
    cone(f"village_roof_{i}", w * 0.78, 0.3, 2.6, (x, y, LAND + h + 1.3),
         "roof_teal" if i % 2 else "roof_red", verts=4)
sphere("hill1", 1.0, (-84, 55, 2.8), "hill", scale=(11, 7, 5.5))
sphere("hill2", 1.0, (-52, 53, 2.8), "hill", scale=(9, 6, 4.2))
cyl("lh_base", 2.2, 6.0, (-66, 57, LAND + 3.0), "white", verts=16)
cyl("lh_top", 1.6, 2.2, (-66, 57, LAND + 7.2), "coral", verts=16)
cone("lh_roof", 2.0, 0.3, 2.2, (-66, 57, LAND + 9.4), "roof_teal", verts=16)

# ---------------------------------------------------------------- palms & trees
def palm(name, loc, height=12.0, lean=0.0):
    x, y, z = loc
    tx_ = x + math.sin(lean) * height * 0.25
    top = Vector((tx_, y, z + height))
    for seg in range(3):
        t0, t1 = seg / 3, (seg + 1) / 3
        p0 = Vector((x + (tx_ - x) * t0, y, z + height * t0))
        p1 = Vector((x + (tx_ - x) * t1, y, z + height * t1))
        cyl_between(f"{name}_trunk{seg}", p0, p1, 0.6 - seg * 0.09, "trunk", verts=10)
    for k in range(9):
        ang = k * math.tau / 9 + 0.3
        verts, faces = [], []
        n = 6
        length = 5.8
        for i in range(n + 1):
            t = i / n
            along = t * length
            width = (1.0 if t < 0.3 else (1.0 - (t - 0.3) / 0.7)) * 0.85 + 0.08
            drop = 1.0 * t * t * length * 0.55
            px = top.x + math.cos(ang) * along
            py = top.y + math.sin(ang) * along
            pz = top.z - drop + math.sin(t * math.pi) * 0.35
            verts += [(px - math.sin(ang) * width, py + math.cos(ang) * width, pz),
                      (px + math.sin(ang) * width, py - math.cos(ang) * width, pz)]
        for i in range(n):
            a = 2 * i
            faces.append((a, a + 1, a + 3, a + 2))
        me = bpy.data.meshes.new(f"{name}_frond{k}")
        me.from_pydata(verts, [], faces)
        me.update()
        ob = bpy.data.objects.new(f"{name}_frond{k}", me)
        bpy.context.collection.objects.link(ob)
        ob.data.materials.append(MATS["leaf"])
        mod = ob.modifiers.new("sol", "SOLIDIFY")
        mod.thickness = 0.10
        apply_mods(ob)
        smooth(ob, 70)
    for k in range(3):
        sphere(f"{name}_coco{k}", 0.32,
               (top.x + math.cos(k * 2.1) * 0.5, top.y + math.sin(k * 2.1) * 0.5,
                top.z - 0.5), "trunk")


for i, (px, py, h, ln) in enumerate([
    (-29, -52, 12, 0.12), (-29, -24, 13, -0.1), (-28, 2, 11, 0.08),
    (-27, 28, 12, -0.12), (-27, 46, 13, 0.1), (-95, 34, 12, 0.1),
    (-48, 60, 12, -0.1), (-90, 58, 11, 0.12), (6, -44, 12, 0.08),
    (22, -46, 13, -0.1), (94, -34, 12, 0.12), (100, 10, 11, -0.1),
]):
    palm(f"palm{i}", (px, py, LAND + 0.4), height=h, lean=ln)

for i in range(12):
    x = 0 + (i * 13.7) % 96
    y = -40 + (i % 4) * 12
    cyl(f"tree_trunk_{i}", 0.4, 3.6, (x, y, LAND + 1.8), "trunk", verts=8)
    sphere(f"tree_{i}", 2.4, (x, y, LAND + 4.8), "tree", scale=(1, 1, 1.05))

# ---------------------------------------------------------------- boats
def boat(name, loc):
    x, y = loc
    box(f"{name}_hull", (9, 4.0, 1.5), (x, y, 1.9), "white", bevel=1.3, seg=3)
    box(f"{name}_cabin", (3.6, 2.6, 1.9), (x - 1.2, y, 3.1), "skyblue", bevel=0.7, seg=3)
    cyl(f"{name}_mast", 0.2, 8.0, (x + 2.0, y, 5.2), "trunk", verts=8)
    box(f"{name}_sail", (0.16, 3.4, 5.2), (x + 2.0, y + 1.8, 6.9), "white",
        bevel=0.2, seg=2)

boat("boat1", (-72, 18))
boat("boat2", (-44, -18))
boat("boat3", (-58, 6))

# ---------------------------------------------------------------- clouds
def cloud(name, loc, s=1.0):
    x, y, z = loc
    for i, (dx, dy, dz, r) in enumerate([(0, 0, 0, 6.0), (-5.6, 0.8, -0.8, 4.2),
                                          (5.6, -0.5, -0.5, 4.5), (1.6, 1.0, 1.9, 3.8),
                                          (-2.8, 0.3, 1.7, 3.4)]):
        sphere(f"{name}_{i}", r, (x + dx * s, y + dy * s, z + dz * s), "cloud",
               scale=(1, 0.9, 0.8))

cloud("cloud1", (-76, 30, 40), 1.1)
cloud("cloud2", (52, 34, 46), 0.9)
cloud("cloud3", (-20, -34, 34), 0.65)

# ---------------------------------------------------------------- lights + camera
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 6.6
sun.angle = math.radians(1.2)
sun.color = (1.0, 0.95, 0.86)
sun_obj = bpy.data.objects.new("sun", sun)
sun_obj.rotation_euler = (math.radians(50), 0, math.radians(-38))
bpy.context.collection.objects.link(sun_obj)

fill = bpy.data.lights.new("fill", "AREA")
fill.energy = 500
fill.size = 150
fill_obj = bpy.data.objects.new("fill", fill)
fill_obj.location = (-120, -140, 110)
fill_obj.rotation_euler = (math.radians(55), 0, math.radians(30))
bpy.context.collection.objects.link(fill_obj)

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 60
cam = bpy.data.objects.new("cam", cam_data)
cam.location = (-158, -238, 150)
bpy.context.collection.objects.link(cam)
scene.camera = cam

target = bpy.data.objects.new("target", None)
target.location = (2, 0, 15)
bpy.context.collection.objects.link(target)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
cam_data.dof.use_dof = True
cam_data.dof.focus_object = target
cam_data.dof.aperture_fstop = 32

# ---------------------------------------------------------------- export + render
os.makedirs(os.path.join(PROJECT, "assets", "models"), exist_ok=True)
glb = os.path.join(PROJECT, "assets", "models", "haikou_diorama_pilot.glb")
bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_apply=True,
                          use_selection=False, export_cameras=False, export_lights=False)
print("EXPORTED", glb)

scene.render.filepath = os.path.join(PROJECT, "data",
                                     "preview-draft.png" if DRAFT else "preview-final.png")
bpy.ops.render.render(write_still=True)
print("RENDERED", scene.render.filepath)




