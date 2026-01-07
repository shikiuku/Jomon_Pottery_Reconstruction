import bpy
import bmesh
from mathutils import Vector

def update_adjacency_lines(scene):
    line_col = bpy.data.collections.get("Adjacency_Lines")
    if not line_col: return

    # 1. Gather Facet Centroids at current frame
    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Store world centroids: facet_name_map[mat_name] = Vector
    facet_pos = {}
    
    for obj in shards:
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name: continue
            
            # Use a cached local centroid if possible to avoid recalculating bmesh every frame
            # For now, we calculate it (simple enough for 30 shards)
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid = obj.matrix_world @ local_centroid
            facet_pos[(obj.name, mat.name)] = world_centroid

    # 2. Update line objects
    # We use a naming convention for line objects: "Line_ShardA_MatA_ShardB_MatB"
    for line_obj in line_col.objects:
        if not line_obj.name.startswith("Line_"): continue
        
        # Data is stored in the name or we can use custom properties
        parts = line_obj.get("pair_info")
        if not parts: continue
        
        # pair_info format: [objA_name, matA_name, objB_name, matB_name]
        p1 = facet_pos.get((parts[0], parts[1]))
        p2 = facet_pos.get((parts[2], parts[3]))
        
        if p1 and p2:
            # Update vertex positions
            line_obj.data.vertices[0].co = p1
            line_obj.data.vertices[1].co = p2

def setup_dynamic_visualization():
    # 1. Match pairs at Frame 1
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    facet_data = []
    
    for obj in shards:
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name: continue
            # Extract neighbor name
            core_name = mat.name[9:] 
            nb_name = "_".join(core_name.split('_')[:-1])
            
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid_f1 = obj.matrix_world @ local_centroid
            
            facet_data.append({
                'obj_name': obj.name,
                'nb_name': nb_name,
                'mat_name': mat.name,
                'f1_pos': world_centroid_f1
            })

    # 2. Create/Prepare the Line Collection
    line_col = bpy.data.collections.get("Adjacency_Lines")
    if line_col:
        for o in line_col.objects: bpy.data.objects.remove(o, do_unlink=True)
    else:
        line_col = bpy.data.collections.new("Adjacency_Lines")
        bpy.context.scene.collection.children.link(line_col)

    # 3. Pair and Create Static Line Objects (to be updated dynamically)
    matched_count = 0
    # Create a list of pairs to avoid double-processing
    processed_pairs = set()

    # Threshold for matching at Frame 1
    # Set high to 2.0m to allow matching by label even if centroids are far apart.
    MATCH_DIST_THRESHOLD = 2.0 

    for i, f1 in enumerate(facet_data):
        obj1_name = f1['obj_name']
        nb1_name = f1['nb_name']
        if nb1_name == "NONE": continue
        
        # Best candidate for f1
        best_candidate = None
        min_match_dist = 1000.0

        for j, f2 in enumerate(facet_data):
            if i == j: continue
            obj2_name = f2['obj_name']
            nb2_name = f2['nb_name']
            
            # Basic Identity Check: A points to B AND B points to A
            if nb1_name == obj2_name and nb2_name == obj1_name:
                dist = (f1['f1_pos'] - f2['f1_pos']).length
                if dist < MATCH_DIST_THRESHOLD and dist < min_match_dist:
                    min_match_dist = dist
                    best_candidate = j

        if best_candidate is not None:
            j = best_candidate
            f2 = facet_data[j]
            # Unique key for the pair
            pair_ids = sorted([f1['mat_name'] + f1['obj_name'], f2['mat_name'] + f2['obj_name']])
            pair_key = "_".join(pair_ids)
            
            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)
                # Create Line Object
                mesh = bpy.data.meshes.new(f"L_{matched_count}")
                line_obj = bpy.data.objects.new(f"Line_{matched_count}", mesh)
                line_col.objects.link(line_obj)
                
                line_obj["pair_info"] = [f1['obj_name'], f1['mat_name'], f2['obj_name'], f2['mat_name']]
                
                bm = bmesh.new()
                bm.verts.new((0,0,0))
                bm.verts.new((0,0,0))
                bm.edges.new(bm.verts)
                bm.to_mesh(mesh)
                bm.free()
                matched_count += 1

    # Return to current frame
    bpy.context.scene.frame_set(current_frame)
    bpy.context.view_layer.update()
    
    # 4. Register the Handler
    bpy.app.handlers.frame_change_post.clear()
    bpy.app.handlers.frame_change_post.append(update_adjacency_lines)
    
    # Run once immediately
    update_adjacency_lines(bpy.context.scene)
    
    return f"Dynamic Visualization Updated: {matched_count} lines registered."

print(setup_dynamic_visualization())
