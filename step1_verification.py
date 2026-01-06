import bpy
import bmesh

def verify_fracture_surfaces():
    """
    Verifies that fracture surfaces have the correct material assigned.
    Rules:
    1. Identify the 'Inner' material (assigned by RBDLab).
    2. Change its color to RED and Emission to high for visual verification.
    3. Count how many faces rely on this material.
    """
    
    # 1. Identify the Inner Material
    # RBDLab often creates a material named "Object_Name_Inner_mat" or similar.
    # Our object is "Lathe_Pot".
    target_mat_name = "Lathe_Pot_Inner_mat"
    
    inner_mat = bpy.data.materials.get(target_mat_name)
    
    if not inner_mat:
        print(f"Warning: Material '{target_mat_name}' not found.")
        # Try to find semi-matching material
        for mat in bpy.data.materials:
            if "Inner" in mat.name:
                inner_mat = mat
                print(f"Found alternative inner material: {mat.name}")
                break
    
    if not inner_mat:
        print("ERROR: No Inner Material found. Fracture might not have been applied or materials not assigned.")
        return

    # 2. Make it VISIBLE (Red Emission)
    inner_mat.use_nodes = True
    nodes = inner_mat.node_tree.nodes
    links = inner_mat.node_tree.links
    
    # Check for Principled BSDF
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        # Base Color -> Red
        bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
        # Emission -> Red, Strength -> 5.0
        bsdf.inputs['Emission Color'].default_value = (1.0, 0.0, 0.0, 1.0)
        bsdf.inputs['Emission Strength'].default_value = 5.0
        print(f"Material '{inner_mat.name}' updated to Glowing Red.")

    # 3. Check Shards
    # Assuming shards are selected or we check all mesh objects
    shards = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not shards:
        shards = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and "Lathe_Pot" in obj.name]

    print(f"Checking {len(shards)} shards...")

    total_inner_faces = 0
    shards_with_inner = 0

    for obj in shards:
        # Find material index for inner_mat
        mat_index = -1
        for i, mat in enumerate(obj.data.materials):
            if mat == inner_mat:
                mat_index = i
                break
        
        if mat_index == -1:
            continue
            
        # Count faces using this material
        inner_faces = [p for p in obj.data.polygons if p.material_index == mat_index]
        count = len(inner_faces)
        
        if count > 0:
            total_inner_faces += count
            shards_with_inner += 1
            # Select these faces for visualization? (Optional)
            # for p in inner_faces: p.select = True

    print("="*30)
    print(f"VERIFICATION RESULT:")
    print(f"Target Material: {inner_mat.name}")
    print(f"Shards containing Inner Material: {shards_with_inner} / {len(shards)}")
    print(f"Total Inner Faces identified: {total_inner_faces}")
    print("="*30)
    
    if total_inner_faces > 0:
        return "SUCCESS: Inner surfaces identified and highlighted."
    else:
        return "FAILED: No inner surfaces found."

result = verify_fracture_surfaces()
print(result)
