import bpy
import bmesh
from mathutils import Vector, Matrix

def create_red_pipe(p1, p2, radius, name):
    v = p2 - p1
    dist = v.length
    if dist < 0.001: return None
    
    center = (p1 + p2) / 2
    q = v.to_track_quat('Z', 'Y')
    
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, radius1=radius, radius2=radius, depth=dist, segments=8)
    
    rot_mat = q.to_matrix().to_4x4()
    loc_mat = Matrix.Translation(center)
    transform = loc_mat @ rot_mat
    bmesh.ops.transform(bm, matrix=transform, verts=bm.verts)
    
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()
    
    obj = bpy.data.objects.new(name, mesh)
    # Link to Main Scene Collection (safest visibility)
    bpy.context.scene.collection.objects.link(obj)
    
    obj.show_in_front = True
    return obj

def setup_dynamic_visualization():
    print("--- Generating RED VISIBLE PIPES ---")
    
    # 0. Red Material (Robust)
    mat = bpy.data.materials.get("FINAL_RED_MAT")
    if not mat:
        mat = bpy.data.materials.new("FINAL_RED_MAT")
        mat.diffuse_color = (1.0, 0.0, 0.0, 1.0) # Red Viewport
    
    # 1. Cleanup old lines/pipes
    # Remove objects starting with "Line_" or "FinalPipe_"
    to_delete = []
    for obj in bpy.data.objects:
        if obj.name.startswith("Line_") or obj.name.startswith("FinalPipe_"):
            to_delete.append(obj)
    
    # Batch delete
    if to_delete:
        bpy.ops.object.select_all(action='DESELECT')
        for o in to_delete: o.select_set(True)
        bpy.ops.object.delete()

    # 2. Gather Data
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    shards = [obj for obj in bpy.data.objects if "RND_Pot" in obj.name and ("cell" in obj.name.lower() or "Cell" in obj.name) and obj.type == 'MESH']
    facet_data = []

    for obj in shards:
        for i, m in enumerate(obj.data.materials):
            if not m or "RECON_V6_" not in m.name: continue
            
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid = obj.matrix_world @ local_centroid
            
            core_name = m.name[9:] 
            nb_name = "_".join(core_name.split('_')[:-1])
            facet_data.append({
                'obj_name': obj.name, 
                'nb_name': nb_name, 
                'mat_name': m.name, 
                'pos': world_centroid
            })

    # 3. Create Pipes
    processed_pairs = set()
    count = 0
    MATCH_DIST_THRESHOLD = 2.0 
    
    for i, f1 in enumerate(facet_data):
        if f1['nb_name'] == "NONE": continue
        
        best_candidate = None
        min_dist = 1000.0

        for j, f2 in enumerate(facet_data):
            if i == j: continue
            if f1['nb_name'] == f2['obj_name'] and f2['nb_name'] == f1['obj_name']:
                dist = (f1['pos'] - f2['pos']).length
                if dist < MATCH_DIST_THRESHOLD and dist < min_dist:
                    min_dist = dist
                    best_candidate = j
                    
        if best_candidate is not None:
            f2 = facet_data[best_candidate]
            pair_ids = sorted([f1['mat_name'] + f1['obj_name'], f2['mat_name'] + f2['obj_name']])
            pair_key = "_".join(pair_ids)
            
            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)
                
                # Create RED THICK PIPE (4cm diameter)
                pipe = create_red_pipe(
                    f1['pos'], f2['pos'], 
                    radius=0.02, 
                    name=f"FinalPipe_{count}"
                )
                if pipe:
                    pipe.data.materials.append(mat)
                    count += 1

    bpy.context.scene.frame_set(current_frame)
    return f"Created {count} RED THICK PIPES."

if __name__ == "__main__":
    print(setup_dynamic_visualization())
