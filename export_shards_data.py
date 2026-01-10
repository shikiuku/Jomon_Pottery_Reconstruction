import bpy
import bmesh
import json
import os
import random
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def export_training_data(output_dir, num_points=2048):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Updated selector for RND_Pot
    all_shards = [obj for obj in bpy.data.objects if "RND_Pot" in obj.name and ("cell" in obj.name.lower() or "Cell" in obj.name) and obj.type == 'MESH']
    
    # Group by Pot ID (e.g. RND_Pot_0_0)
    pot_groups = {}
    for obj in all_shards:
        # standard name: RND_Pot_X_Y_cell.001
        # Extract "RND_Pot_X_Y"
        parts = obj.name.split('_cell')
        if len(parts) > 0:
            pot_id = parts[0] # RND_Pot_0_0
            if pot_id not in pot_groups: pot_groups[pot_id] = []
            pot_groups[pot_id].append(obj)
            
    print(f"Found {len(pot_groups)} distinct pots.")

    # 1. Export Data Per Pot
    current_frame = bpy.context.scene.frame_current
    
    
    # Sort for deterministic numbering
    sorted_pot_ids = sorted(pot_groups.keys())
    
    for idx, old_pot_id in enumerate(sorted_pot_ids):
        # Generate new name: Pot_001, Pot_002...
        new_pot_id = f"Pot_{idx+1:03d}"
        shards = pot_groups[old_pot_id]
        
        # Create Folder
        pot_dir = os.path.join(output_dir, new_pot_id)
        if not os.path.exists(pot_dir):
            os.makedirs(pot_dir)
            
        print(f"Processing {old_pot_id} -> {new_pot_id} ({len(shards)} shards)")

        # Create Name Mapping for this pot's shards
        # obj.name (RND_Pot_0_0_cell.001) -> new_name (Pot_001_cell.001)
        name_map = {}
        for obj in shards:
            # Simple replacement of the prefix
            new_obj_name = obj.name.replace(old_pot_id, new_pot_id)
            name_map[obj.name] = new_obj_name

        # --- A. Analyze Facets (Frame 1) ---
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        
        facet_data = []
        mat_to_id = {}
        id_counter = 1 
        
        for obj in shards:
            for i, mat in enumerate(obj.data.materials):
                if not mat or "RECON_V6_" not in mat.name: continue
                
                faces = [f for f in obj.data.polygons if f.material_index == i]
                if not faces: continue
                
                # Setup Names
                mapped_obj_name = name_map[obj.name]
                
                # Neighbor Name Logic:
                # Material name: RECON_V6_RND_Pot_0_0_cell.002_15
                # We need to parse this and map the neighbor name too!
                # Core: RND_Pot_0_0_cell.002
                core_name = mat.name[9:] 
                nb_original_name = "_".join(core_name.split('_')[:-1])
                
                # If neighbor is in our map (it should be if it's in the same pot), map it
                mapped_nb_name = name_map.get(nb_original_name, "NONE")
                
                centroid = sum((f.center for f in faces), Vector()) / len(faces)
                world_pos = obj.matrix_world @ centroid
                
                facet_id = id_counter
                id_counter += 1
                mat_to_id[(obj.name, mat.name)] = facet_id
                
                facet_data.append({
                    'id': facet_id,
                    'obj_name': mapped_obj_name, # Export NEW name
                    'nb_name': mapped_nb_name,   # Export NEW name
                    'mat_name': mat.name,
                    'pos': world_pos
                })

        # --- B. Find Pairs ---
        adjacency_list = []
        processed_pairs = set()
        MATCH_DIST_THRESHOLD = 2.0 

        for i, f1 in enumerate(facet_data):
            if f1['nb_name'] == "NONE": continue
            
            best_candidate = None
            min_match_dist = 1000.0

            for j, f2 in enumerate(facet_data):
                if i == j: continue
                if f1['nb_name'] == f2['obj_name'] and f2['nb_name'] == f1['obj_name']:
                    dist = (f1['pos'] - f2['pos']).length
                    if dist < MATCH_DIST_THRESHOLD and dist < min_match_dist:
                        min_match_dist = dist
                        best_candidate = j

            if best_candidate is not None:
                f2 = facet_data[best_candidate]
                pair = sorted([f1['id'], f2['id']])
                tuple_pair = tuple(pair)
                
                if tuple_pair not in processed_pairs:
                    processed_pairs.add(tuple_pair)
                    adjacency_list.append(pair)

        # Save Adjacency
        with open(os.path.join(pot_dir, "adjacency.json"), 'w') as f:
            json.dump(adjacency_list, f, indent=4)

        # --- C. Export Point Clouds (Scattered Frame) ---
        bpy.context.scene.frame_set(current_frame)
        bpy.context.view_layer.update()

        for obj in shards:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.transform(obj.matrix_world)
            bvh = BVHTree.FromBMesh(bm)
            bm.faces.ensure_lookup_table()
            
            total_area = sum(f.calc_area() for f in bm.faces)
            point_cloud = []
            
            for _ in range(num_points):
                r = random.uniform(0, total_area)
                acc = 0
                target_face = bm.faces[0]
                for f in bm.faces:
                    acc += f.calc_area()
                    if acc >= r:
                        target_face = f
                        break
                
                v_coords = [v.co for v in target_face.verts]
                if len(v_coords) >= 3:
                    u, v_w = random.random(), random.random()
                    if u + v_w > 1: u, v_w = 1 - u, 1 - v_w
                    w = 1 - u - v_w
                    p = u * v_coords[0] + v_w * v_coords[1] + w * v_coords[2]
                else:
                    p = target_face.calc_center_bounds()
                
                _, normal, face_idx, _ = bvh.find_nearest(p)
                orig_face = bm.faces[face_idx]
                mat = obj.data.materials[orig_face.material_index]
                
                label = 0
                if mat and "RECON_V6_" in mat.name:
                    label = mat_to_id.get((obj.name, mat.name), 0)
                
                point_cloud.append({
                    'pos': [p.x, p.y, p.z],
                    'norm': [normal.x, normal.y, normal.z],
                    'label': label
                })
            
            # Use NEW Name for filename
            new_filename = name_map[obj.name]
            filename = os.path.join(pot_dir, f"{new_filename}.json")
            with open(filename, 'w') as f:
                json.dump(point_cloud, f)
            bm.free()

    return f"Export Complete: Saved {len(sorted_pot_ids)} pots to {output_dir}"

# Run it
out_path = r"c:\Users\k4849\Documents\VibeCording\Jomon_Pottery_Reconstruction\dataset_manual_batch_001"
print(export_training_data(out_path))
