import bpy
import random
import math

def create_random_pot(name, location):
    # 1. Create Curve for the profile
    curve_data = bpy.data.curves.new(name + "_Curve", type='CURVE')
    curve_data.dimensions = '3D'
    polyline = curve_data.splines.new('BEZIER')
    
    # --- YAYOI STYLE: TSUBO ONLY (50-60cm) ---
    # User requested: "Size 50-60cm", "Tsubo only".
    
    archetype = 'TSUBO'
    
    # Defaults
    p0_center = [0, 0, 0]
    handles = ['VECTOR', 'VECTOR', 'AUTO', 'AUTO', 'AUTO', 'AUTO', 'AUTO']
    
    # --- STANDARD VESSEL TOPOLOGY ---
    
    if archetype == 'TSUBO':
        # TYPE 1: TSUBO (Jar - 貯蔵用)
        # Reference: Round belly, Distinct neck, Flared rim.
        # Scale: 30cm - 50cm
        total_height = random.uniform(0.3, 0.5)
        max_width = total_height * random.uniform(0.7, 0.9)
    # 1. EXPLODED GLOBAL SCALE (Restricted)
    # User requested strict range: Fixed 60cm
    total_height = 0.60
    
    if archetype == 'TSUBO':
        # TYPE 1: TSUBO (Jar) - S-Curve
        # Variance Factor: CENTER OF GRAVITY & STOUTNESS
        
        # Stoutness: Wide vs Slender
        # User requested: "Allow Bucket shapes too"
        # 25cm - 40cm range allows for both slender cylinders and typical jars.
        max_width = random.uniform(0.25, 0.40)
        # aspect_ratio = max_width / total_height (Implicit)
        
        # 1. BELLY POSITION (Center of Gravity)
        # 0.35 (Low/Stable) to 0.75 (High Shoulder/Bucket-like)
        belly_h_ratio = random.uniform(0.35, 0.75)
        belly_h = total_height * belly_h_ratio
        
        # 2. NECK DEFINITION
        # Neck width relative to belly
        # 0.35 = Tight (Jar), 1.0 = Straight (Cylinder/No Neck)
        neck_w_ratio = random.uniform(0.35, 1.0)
        neck_w = max_width * neck_w_ratio
        
        # Neck Height (Distance from belly to rim)
        # If belly is high, neck is short. If belly is low, neck is long.
        neck_h_ratio = random.uniform(0.8, 0.9)
        neck_h = total_height * neck_h_ratio
        
        # 3. RIM FLARE
        # 0.85 (Inverted/No Mouth) to 1.35 (Flare)
        rim_flare_ratio = random.uniform(0.85, 1.35)
        rim_w = neck_w * rim_flare_ratio
        
        # Bottom (Stable)
        # 10cm (Tapered) to 35cm (Wide/Bucket Base)
        bottom_w = random.uniform(0.10, 0.35)

        # Topology
        p1_bot_flat = [bottom_w * 0.8, 0, 0]
        p2_bot_curve = [bottom_w, 0, belly_h * 0.15]
        p3_belly = [max_width, 0, belly_h]
        p4_neck = [neck_w, 0, neck_h]
        
        # Rim Flare Logic
        rim_flare_start_h = (total_height + neck_h) * 0.5
        rim_flare_w = neck_w * (1.0 + (rim_flare_ratio - 1.0) * 0.3)
        p5_rim_base = [rim_flare_w, 0, rim_flare_start_h]
        p6_rim_tip = [rim_w, 0, total_height]
        
    else: # KAME
        # TYPE 2: KAME (Pot) - Bucket/Cylinder
        # Variance Factor: TAPER ANGLE
        
        # Width: Generally wider than Tsubo relative to height
        aspect_ratio = random.uniform(0.7, 1.3)
        max_width = total_height * aspect_ratio
        
        # 1. TAPER ANGLE (Base vs Rim)
        # 0.9-1.0 = Cylinder (Zundou)
        # 0.5-0.6 = Sharp Bucket (V-shape)
        base_rim_ratio = random.uniform(0.4, 0.95)
        
        # RIM is the widest point (Max Width)
        rim_w = max_width
        
        # BOTTOM is derived from ratio
        bottom_w = rim_w * base_rim_ratio
        
        # NECK (Definition for topology, but practically same as Rim)
        neck_h = total_height * 0.95
        # Ensure neck is NOT wider than rim to keep inverted cone shape
        neck_w = rim_w * random.uniform(0.95, 0.99) 
        
        # BELLY (Linear Interpolation for Straight Walls)
        belly_h = total_height * random.uniform(0.4, 0.6)
        
        # Lerp: Bottom -> Neck
        t = belly_h / neck_h
        belly_w_linear = bottom_w + (neck_w - bottom_w) * t
        
        # Tiny organic jitter (optional, keep small for now)
        p3_belly_w = belly_w_linear * random.uniform(0.98, 1.02)
        
        # Topology
        p1_bot_flat = [bottom_w * 0.8, 0, 0]
        p2_bot_curve = [bottom_w, 0, belly_h * 0.1]
        p3_belly = [p3_belly_w, 0, belly_h]
        p4_neck = [neck_w, 0, neck_h]
        
        p5_rim_base = [rim_w * 0.98, 0, total_height * 0.99]
        p6_rim_tip = [rim_w, 0, total_height]

    # Shared Topology List
    coords = [p0_center, p1_bot_flat, p2_bot_curve, p3_belly, p4_neck, p5_rim_base, p6_rim_tip]

    polyline.bezier_points.add(len(coords) - 1)
    for i, coord in enumerate(coords):
        p = polyline.bezier_points[i]
        p.co = coord
        
        h_type = handles[i]
        p.handle_left_type = h_type
        p.handle_right_type = h_type
        
    curve_obj = bpy.data.objects.new(name + "_Profile", curve_data)
    bpy.context.collection.objects.link(curve_obj)
    curve_obj.location = location
    
    # 2. Add Screw Modifier and Solidify
    screw_mod = curve_obj.modifiers.new(name="Screw", type='SCREW')
    screw_mod.axis = 'Z'
    # User requested: "Reduce vertex count". 64 -> 32
    screw_mod.steps = 32 
    screw_mod.use_merge_vertices = True 
    screw_mod.merge_threshold = 0.001
    screw_mod.use_smooth_shade = True 
    
    solid_mod = curve_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid_mod.thickness = 0.03 # 3cm
    
    # 3. CONVERT TO MESH (CRITICAL for RBDLab)
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.active_object
    mesh_obj.name = name
    
    # 4. Apply Materials and fix Indices
    # Helper to get BSDF
    def get_principled_bsdf(mat):
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                return node
        return mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')

    # 4. Apply Materials and fix Indices
    outer_mat = bpy.data.materials.get("Lathe_Pot_Outer_mat")
    if not outer_mat:
        outer_mat = bpy.data.materials.new("Lathe_Pot_Outer_mat")
        outer_mat.use_nodes = True
        bsdf = get_principled_bsdf(outer_mat)
        bsdf.inputs[0].default_value = (0.8, 0.5, 0.3, 1) # Yayoi Reddish Brown
    
    # Always set viewport color 
    outer_mat.diffuse_color = (0.8, 0.5, 0.3, 1) # Match Yayoi color
    
    inner_mat = bpy.data.materials.get("Lathe_Pot_Inner_mat")
    if not inner_mat:
        inner_mat = bpy.data.materials.new("Lathe_Pot_Inner_mat")
        inner_mat.use_nodes = True
        bsdf = get_principled_bsdf(inner_mat)
        bsdf.inputs[0].default_value = (0.8, 0.1, 0.1, 1) # Redish
    
    # Set viewport color to reddish for inner
    inner_mat.diffuse_color = (0.8, 0.1, 0.1, 1)
    
    # Ensure slots exist
    if not mesh_obj.data.materials:
        mesh_obj.data.materials.append(outer_mat)
        mesh_obj.data.materials.append(inner_mat)
    else:
        mesh_obj.data.materials[0] = outer_mat
        if len(mesh_obj.data.materials) < 2:
            mesh_obj.data.materials.append(inner_mat)
        else:
            mesh_obj.data.materials[1] = inner_mat

    # Set all faces to index 0 (Outer)
    for f in mesh_obj.data.polygons:
        f.material_index = 0
        
    # Set Object color for viewport (Solid mode)
    mesh_obj.color = (0.8, 0.8, 0.8, 1)
    
    # --- ADD WEATHERING (Excavated Look) ---
    add_surface_roughness(mesh_obj)
    # rim_w is Radius (from screw modifier logic). total_height is Height.
    add_rim_chipping(mesh_obj, total_height, rim_w)
    
    return mesh_obj

def create_floor(size=20, location=(4.5, 4.5, 0)):
    if "Floor" not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=size, location=location)
        plane = bpy.context.active_object
        plane.name = "Floor"
        
        # Add a simple material
        mat = bpy.data.materials.new(name="FloorMat")
        mat.diffuse_color = (0.3, 0.3, 0.3, 1) # Darker grey
        plane.data.materials.append(mat)
        
        # Hide floor (User Request)
        plane.hide_viewport = True
        plane.hide_render = True
        
        # Add Physics (Passive)
        bpy.context.view_layer.objects.active = plane
        if not bpy.context.scene.rigidbody_world:
            bpy.ops.rigidbody.world_add()
        bpy.ops.rigidbody.object_add(type='PASSIVE')
        plane.rigid_body.collision_shape = 'MESH'

def add_surface_roughness(obj):
    """Adds excavated-like surface roughness."""
    try:
        # 1. Subdivision (Levels=2)
        sub = obj.modifiers.new("Roughness_Sub", 'SUBSURF')
        # User Feedback: "Reduce vertex". 2 -> 1
        sub.levels = 1
        sub.render_levels = 1
        
        # 2. Displacement (Fine Grain)
        disp = obj.modifiers.new("Roughness_Disp", 'DISPLACE')
        # User Feedback: "Too intense" -> Reduced to subtle realism.
        disp.strength = 0.008 
        
        tex_name = "Excavated_Noise"
        tex = bpy.data.textures.get(tex_name)
        if not tex:
            tex = bpy.data.textures.new(tex_name, 'CLOUDS')
            tex.noise_scale = 0.05 # Higher freq
        disp.texture = tex
        
        # Apply
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="Roughness_Sub")
        bpy.ops.object.modifier_apply(modifier="Roughness_Disp")
    except Exception as e:
        print(f"Roughness Error: {e}")

def add_rim_chipping(obj, height, radius):
    """Subtracts a random chunk from the rim."""
    import math
    # User Feedback: "Too intense" -> Revert to probability (40%)
    if random.random() < 0.6: return # 60% chance SAFE, 40% chance CHIP
    
    try:
        # Create Jagged Rock
        # Realistic chip size: 5cm - 12cm
        bpy.ops.mesh.primitive_cube_add(size=random.uniform(0.05, 0.12)) 
        cutter = bpy.context.active_object
        
        # Make it jagged
        sub = cutter.modifiers.new("Sub", 'SUBSURF')
        sub.levels = 3
        disp = cutter.modifiers.new("Disp", 'DISPLACE')
        disp.strength = 0.1
        tex = bpy.data.textures.new("Chip_Rock_Tex", 'VORONOI')
        disp.texture = tex
        
        bpy.ops.object.modifier_apply(modifier="Sub")
        bpy.ops.object.modifier_apply(modifier="Disp")
        
        # Position at Rim
        angle = random.uniform(0, 6.28)
        # Place firmly ON the rim radius
        r_perturb = radius 
        x = math.cos(angle) * r_perturb
        y = math.sin(angle) * r_perturb
        
        # Height: Rim is at 'height'.
        cutter.location = (x, y, height)
        cutter.rotation_euler = (random.random(), random.random(), random.random())
        
        # Boolean Difference
        bool_mod = obj.modifiers.new("Chip_Hole", 'BOOLEAN')
        bool_mod.operation = 'DIFFERENCE'
        bool_mod.object = cutter
        bool_mod.solver = 'FAST'
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="Chip_Hole")
        
        # Cleanup
        bpy.data.objects.remove(cutter, do_unlink=True)
        
    except Exception as e:
        print(f"Chipping Error: {e}")

def generate_verification_grid(rows=3, cols=3, spacing=3.0):
    # Cleanup previous random pots (but keep floor if exists, or recreate)
    for obj in bpy.data.objects:
        if "RND_Pot" in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Ensure floor exists
    create_floor(size=30, location=(cols*spacing/2 - spacing/2, rows*spacing/2 - spacing/2, -0.2))
            
    for r in range(rows):
        for c in range(cols):
            name = f"RND_Pot_{r}_{c}"
            loc = (c * spacing, r * spacing, 0)
            create_random_pot(name, loc)
            
    print(f"Generated {rows*cols} random pots for verification.")

if __name__ == "__main__":
    generate_verification_grid()
