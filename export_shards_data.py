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

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # 1. Export Adjacency Mapping
    # We'll use the visualization logic to find pairs
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    
    facet_data = []
    mat_to_id = {}
    id_counter = 101 # Starting ID for facets

    print("Analyzing facets...")
    for obj in shards:
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name: continue
            
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            core_name = mat.name[9:] 
            nb_name = "_".join(core_name.split('_')[:-1])
            
            centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_pos = obj.matrix_world @ centroid
            
            facet_id = id_counter
            id_counter += 1
            mat_to_id[(obj.name, mat.name)] = facet_id
            
            facet_data.append({
                'id': facet_id,
                'obj_name': obj.name,
                'nb_name': nb_name,
                'mat_name': mat.name,
                'pos': world_pos
            })

    # Find pairs
    adjacency_list = []
    processed_pairs = set()
    for i, f1 in enumerate(facet_data):
        for j, f2 in enumerate(facet_data):
            if i >= j: continue
            if f1['nb_name'] == f2['obj_name'] and f2['nb_name'] == f1['obj_name']:
                if (f1['pos'] - f2['pos']).length < 0.5: # loose threshold as before
                    adjacency_list.append([f1['id'], f2['id']])

    # Save Adjacency
    with open(os.path.join(output_dir, "adjacency.json"), 'w') as f:
        json.dump(adjacency_list, f, indent=4)
    print(f"Saved {len(adjacency_list)} adjacency pairs.")

    # 2. Export Point Clouds
    # Go back to scattered frame or stay at Frame 1? 
    # Usually for training, we want the scattered positions or canonical (at origin).
    # Let's export at the current frame (scattered).
    bpy.context.scene.frame_set(current_frame)
    bpy.context.view_layer.update()

    print("Sampling point clouds...")
    for obj in shards:
        # Create a BVH tree for the mesh to find nearest faces efficiently
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world) # points in world space
        bvh = BVHTree.FromBMesh(bm)
        
        # Prepare lookup tables
        bm.faces.ensure_lookup_table()
        
        # Sample points on surface
        total_area = sum(f.calc_area() for f in bm.faces)
        point_cloud = []
        
        for _ in range(num_points):
            # Pick a face
            r = random.uniform(0, total_area)
            acc = 0
            target_face = bm.faces[0]
            for f in bm.faces:
                acc += f.calc_area()
                if acc >= r:
                    target_face = f
                    break
            
            # Sample random point in triangle/quad
            # (Simplification: just get centroid of face for now, or barycentric)
            # Better: random barycentric
            v_coords = [v.co for v in target_face.verts]
            if len(v_coords) >= 3:
                # Barycentric for triangle
                u, v_w = random.random(), random.random()
                if u + v_w > 1:
                    u, v_w = 1 - u, 1 - v_w
                w = 1 - u - v_w
                p = u * v_coords[0] + v_w * v_coords[1] + w * v_coords[2]
            else:
                p = target_face.calc_center_bounds()
            
            # Find closest face to determine label
            _, normal, face_idx, _ = bvh.find_nearest(p)
            
            # Get material index of that face
            # We need original face index mapping. bm.faces[face_idx] works
            orig_face = bm.faces[face_idx]
            mat_idx = orig_face.material_index
            mat = obj.data.materials[mat_idx]
            
            label = 0
            if mat and "RECON_V6_" in mat.name:
                label = mat_to_id.get((obj.name, mat.name), 0)
            
            point_cloud.append({
                'pos': [p.x, p.y, p.z],
                'norm': [normal.x, normal.y, normal.z],
                'label': label
            })
        
        # Save PC
        filename = os.path.join(output_dir, f"{obj.name}.json")
        with open(filename, 'w') as f:
            json.dump(point_cloud, f)
        
        bm.free()
        print(f"Exported {obj.name} ({num_points} points)")

    return "Export Complete"

# Run it
out_path = r"c:\Users\k4849\Documents\VibeCording\Jomon_Pottery_Reconstruction\training_data_v1"
print(export_training_data(out_path))
