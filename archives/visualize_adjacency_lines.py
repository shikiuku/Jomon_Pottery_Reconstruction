import bpy
import bmesh
from mathutils import Vector

def visualize_facet_adjacency():
    # 1. Gather all facets and their metadata (At Frame 1 for matching)
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Store facet info: (shard_obj, neighbor_name, local_centroid, f1_centroid, mat_name)
    facet_data = []
    
    print("Gathering facet data at Frame 1...")
    for obj in shards:
        # Materials RECON_V6_{neighbor}_{index}
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name:
                continue
            
            # Extract neighbor name from mat name: RECON_V6_Lathe_Pot_cell.015_0
            parts = mat.name.split('_')
            # The neighbor name might contain underscores if it's 'Lathe_Pot_cell.xxx'
            # Format is RECON_V6_{NBNAME}_{ID}
            # Since NBNAME might have underscores, we remove the prefix and suffix
            # RECON_V6_ (9 chars) and _ID (last part)
            # Example: RECON_V6_Lathe_Pot_cell.015_0
            core_name = mat.name[9:] # Remove 'RECON_V6_'
            parts = core_name.split('_')
            nb_name = "_".join(parts[:-1]) # Rejoin all but the last ID part
            
            if nb_name == "NONE": continue

            # Calculate Centroid
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid_at_f1 = obj.matrix_world @ local_centroid
            
            facet_data.append({
                'obj': obj,
                'nb_name': nb_name,
                'local_centroid': local_centroid,
                'f1_centroid': world_centroid_at_f1,
                'mat_name': mat.name
            })

    # Return to scattered frame
    bpy.context.scene.frame_set(current_frame)
    bpy.context.view_layer.update()

    # 2. Match pairs and Draw Lines (At Scattered Frame)
    print(f"Matching {len(facet_data)} facets...")
    
    # Create a collection for lines
    line_col = bpy.data.collections.get("Adjacency_Lines")
    if line_col:
        # Clear existing
        for obj in line_col.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    else:
        line_col = bpy.data.collections.new("Adjacency_Lines")
        bpy.context.scene.collection.children.link(line_col)

    matched_count = 0
    # To avoid double lines, keep track of processed pairs
    seen_pairs = set()

    for i, f1 in enumerate(facet_data):
        obj1 = f1['obj']
        nb1 = f1['nb_name']
        
        # Look for the counterpart in facet_data
        for j, f2 in enumerate(facet_data):
            if i >= j: continue # Avoid self and double check
            
            obj2 = f2['obj']
            nb2 = f2['nb_name']
            
            # Condition: f1's neighbor is f2's object AND vice versa
            if nb1 == obj2.name and nb2 == obj1.name:
                # Use f1_centroid for distance matching at Frame 1
                dist = (f1['f1_centroid'] - f2['f1_centroid']).length
                if dist < 0.005: # Closer match at Frame 1
                    
                    # Create Line at Current Frame positions
                    # Use local_centroid transformed by current matrix_world
                    p1 = obj1.matrix_world @ f1['local_centroid']
                    p2 = obj2.matrix_world @ f2['local_centroid']

                    mesh = bpy.data.meshes.new(f"Line_{obj1.name}_{obj2.name}")
                    line_obj = bpy.data.objects.new(mesh.name, mesh)
                    line_col.objects.link(line_obj)
                    
                    bm = bmesh.new()
                    v1 = bm.verts.new(p1)
                    v2 = bm.verts.new(p2)
                    bm.edges.new((v1, v2))
                    bm.to_mesh(mesh)
                    bm.free()
                    
                    matched_count += 1

    return f"Visualization Complete: Drew {matched_count} adjacency lines."

print(visualize_facet_adjacency())
