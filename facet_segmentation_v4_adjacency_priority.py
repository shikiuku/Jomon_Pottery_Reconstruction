import bpy
import bmesh
from mathutils import Vector

def run_segmentation_v4():
    # 1. Setup Base Materials
    surf_mat = bpy.data.materials.get("RECON_Surface")
    if not surf_mat:
        surf_mat = bpy.data.materials.new(name="RECON_Surface")
    surf_mat.diffuse_color = (0.05, 0.05, 0.05, 1.0)
    
    palette = [
        (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), 
        (1, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 1), 
        (1, 1, 1, 1), (1, 0.5, 0, 1), (0.5, 0, 1, 1)
    ]

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Switch to Frame 1 for adjacency check
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    # Threshold: slightly larger to avoid "unassigned" holes due to precision
    PROXIMITY_THRESHOLD = 0.001 

    total_facets_found = 0

    for obj in shards:
        obj.data.materials.clear()
        obj.data.materials.append(surf_mat)
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Identify inner faces
        attr = obj.data.attributes.get('Inner_faces')
        inner_faces = []
        if attr:
            for i, face in enumerate(bm.faces):
                if attr.data[i].value:
                    inner_faces.append(face)
        
        if not inner_faces:
            bm.free()
            continue

        # Step 1: For each face, find the closest neighbor shard
        face_neighbor_map = {} # face.index -> neighbor_name
        
        for f in inner_faces:
            world_center = obj.matrix_world @ f.calc_center_median()
            best_nb = "NONE"
            min_dist = PROXIMITY_THRESHOLD
            
            for other in shards:
                if other == obj: continue
                
                # Check closest point
                local_pos = other.matrix_world.inverted() @ world_center
                dist, pt, norm, f_idx = other.closest_point_on_mesh(local_pos)
                world_dist = (world_center - (other.matrix_world @ pt)).length
                
                if world_dist < min_dist:
                    min_dist = world_dist
                    best_nb = other.name
            
            face_neighbor_map[f.index] = best_nb

        # Step 2: Fill "NONE" gaps with neighbors' IDs (Majority vote or simpler)
        # We'll do a simple second pass for NONE faces
        for f in inner_faces:
            if face_neighbor_map[f.index] == "NONE":
                # Look at connected faces
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf.index in face_neighbor_map and face_neighbor_map[nf.index] != "NONE":
                            face_neighbor_map[f.index] = face_neighbor_map[nf.index]
                            break
                    if face_neighbor_map[f.index] != "NONE": break

        # Step 3: Group faces: same neighbor AND connected
        unvisited = set(inner_faces)
        final_facets = []
        
        while unvisited:
            start_f = unvisited.pop()
            nb_id = face_neighbor_map[start_f.index]
            current_facet = [start_f]
            queue = [start_f]
            
            while queue:
                f = queue.pop(0)
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf != f and nf in unvisited:
                            # Must share same neighbor to be in same facet
                            if face_neighbor_map[nf.index] == nb_id:
                                unvisited.remove(nf)
                                current_facet.append(nf)
                                queue.append(nf)
            final_facets.append(current_facet)

        # Step 4: Visualization
        for i, facet in enumerate(final_facets):
            mat_name = f"RECON_V4_Facet_{i}"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                mat.diffuse_color = palette[(total_facets_found + i) % len(palette)]
            
            obj.data.materials.append(mat)
            slot_idx = len(obj.data.materials) - 1
            for f in facet:
                f.material_index = slot_idx
        
        total_facets_found += len(final_facets)
        bm.to_mesh(obj.data)
        bm.free()

    bpy.context.scene.frame_set(current_frame)
    # Shading
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D':
                space.shading.color_type = 'MATERIAL'

    return f"V4 Adjacency-First Complete: Found {total_facets_found} facets."

print(run_segmentation_v4())
