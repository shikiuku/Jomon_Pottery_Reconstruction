import bpy
import os
import random
import time

# --- Configuration ---
BASE_BLEND_FILE = r"c:\Users\k4849\Documents\VibeCording\Jomon_Pottery_Reconstruction\Jomon_Pottery_Base.blend"

def cleanup_scene():
    """Removes all mesh objects including those in RBDLab collections."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Optional: cleanup specific RBDLab collections if they exist
    for coll in bpy.data.collections:
        if any(x in coll.name for x in ["RBDLab", "Fracture", "Internal", "Chunks"]):
            for obj in coll.objects:
                bpy.data.objects.remove(obj, do_unlink=True)

def create_random_pot():
    """Creates a random pottery mesh (simplified version of generate_random_pots.py)."""
    # Create spline
    curve_data = bpy.data.curves.new('PotSpline', type='CURVE')
    curve_data.dimensions = '3D'
    polyline = curve_data.splines.new('BEZIER')
    
    # Randomize profile
    height = random.uniform(1.5, 2.5)
    width = random.uniform(0.6, 1.2)
    curvature = random.uniform(0.4, 0.8)
    
    points = [
        (0, 0, 0),        # Bottom center
        (width * 0.7, 0, height * 0.2), # Lower body
        (width, 0, height * 0.6),      # Upper body
        (width * 0.8, 0, height * 0.95),# Rim neck
        (width * 0.9, 0, height)        # Rim top
    ]
    
    polyline.bezier_points.add(len(points) - 1)
    for i, p in enumerate(points):
        polyline.bezier_points[i].co = p
        polyline.bezier_points[i].handle_left_type = 'AUTO'
        polyline.bezier_points[i].handle_right_type = 'AUTO'

    obj = bpy.data.objects.new('PotBase', curve_data)
    bpy.context.collection.objects.link(obj)
    
    # Add Screw modifier
    screw = obj.modifiers.new(name="Screw", type='SCREW')
    screw.angle = 6.28319 # 360 degrees
    screw.steps = 32
    screw.render_steps = 32
    
    # Add Solidify modifier
    solid = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid.thickness = 0.05
    
    # Convert to mesh
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    
    # Remove specific material creation to use defaults
    # mat_outer = ...
    # mat_inner = ...
    
    # if len(obj.data.materials) == 0:
    #     obj.data.materials.append(mat_outer)
    #     obj.data.materials.append(mat_inner)
    
    return obj

def run_automation():
    print("--- Starting RBDLab Automation Verification ---")
    
    # 0. Prep
    cleanup_scene()
    bpy.ops.wm.save_as_mainfile(filepath=BASE_BLEND_FILE)
    
    # 1. Create Pot
    pot = create_random_pot()
    bpy.context.view_layer.objects.active = pot
    pot.select_set(True)
    print(f"Created Pot: {pot.name}")

    # 2. Scatter Points
    bpy.context.scene.rbdlab.scatter_count = 50
    bpy.ops.rbdlab.scatter_add()
    print("Points scattered.")

    # 3. Setup Fracture Mode (Cell Fracture - Standard)
    bpy.context.scene.rbdlab.current_using_cell_fracture = True
    print(f"Fracture mode set (CellFracture={bpy.context.scene.rbdlab.current_using_cell_fracture})")

    # 4. Apply Fracture
    # Use the standard cell fracture operator
    bpy.ops.rbdlab.cellfracture()
    print("Standard Cell Fracture applied.")

    # 5. Physics Simulation ("Apply Fractures" logic)
    # Based on external research, the "Apply Fractures" button for Standard Cell Fracture 
    # executes 'make_rigidbodies', which finalizes the physics.
    print("Applying fractures (creating rigid bodies)...")
    
    # We must select the fractured chunks (shards) first
    # Cell Fracture typically creates new objects and hides the original
    bpy.ops.object.select_all(action='DESELECT')
    
    # Simple heuristic to find shards: they contain the original name and are visible
    chunks = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and "PotBase" in obj.name and not obj.hide_viewport:
            obj.select_set(True)
            chunks.append(obj)
            
    if chunks:
        # Ensure Rigid Body World exists (as advised by AI expert 1)
        scene = bpy.context.scene
        if not scene.rigidbody_world:
            bpy.ops.rigidbody.world_add()

        # Apply Rigid Body to each shard (The true identity of "Apply Fractures")
        for obj in chunks:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            
            # Add Rigid Body (Active)
            # Check if RB already exists to avoid errors
            if not obj.rigid_body:
                bpy.ops.rigidbody.object_add(type='ACTIVE')
            
            # Configure settings (Mass, Collision, etc.)
            rb = obj.rigid_body
            if rb:
                rb.mass = 1.0 # Default mass
                rb.collision_shape = 'CONVEX_HULL' # Best for shards
                rb.use_margin = True
                rb.collision_margin = 0.001
                
        print(f"Success: Physics (Rigid Body) applied to {len(chunks)} shards using standard API.")

    # 6. Save and Verify
    bpy.ops.wm.save_as_mainfile(filepath=BASE_BLEND_FILE)
    print(f"Workflow complete. File saved to {BASE_BLEND_FILE}")

def fracture_existing_grid():
    print("--- Starting Batch Fracture for Grid ---")
    
    # 1. Find all target pots
    targets = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and "RND_Pot" in obj.name and "Cell" not in obj.name:
            targets.append(obj)
            
    # Sort to process in order (0_0, 0_1, etc.)
    targets.sort(key=lambda x: x.name)
    
    print(f"Found {len(targets)} pots to fracture.")
    
    # 2. Process each pot
    for i, pot in enumerate(targets):
        print(f"Processing {i+1}/{len(targets)}: {pot.name}")
        
        # Set Active and Selected
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = pot
        pot.select_set(True)
        
        # Configure RBDLab settings
        bpy.context.scene.rbdlab.scatter_count = 30 # Keep it light for test
        bpy.context.scene.rbdlab.current_using_cell_fracture = True
        
        # Scatter
        try:
            bpy.ops.rbdlab.scatter_add()
        except Exception as e:
            print(f"Scatter failed on {pot.name}: {e}")
            continue

        # Fracture
        try:
            bpy.ops.rbdlab.cellfracture()
            print(f"Fractured {pot.name}")
        except Exception as e:
            print(f"Fracture failed on {pot.name}: {e}")
            continue
            
    print("--- Batch Fracture Complete (Physics Apply NOT executed) ---")

if __name__ == "__main__":
    # run_automation() # Disabled single pot test
    fracture_existing_grid()
