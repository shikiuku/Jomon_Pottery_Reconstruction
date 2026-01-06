import bpy
import bmesh
from mathutils import Vector

def run_segmentation_v5_resolution():
    # 1. Setup Base Materials
    surf_mat = bpy.data.materials.get("RECON_Surface")
    if not surf_mat:
        surf_mat = bpy.data.materials.new(name="RECON_Surface")
    surf_mat.diffuse_color = (0.05, 0.05, 0.05, 1.0)
    
    palette = [
        (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), 
        (1, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 1), 
        (1, 1, 1, 1), (1, 0.5, 0, 1), (0.5, 0, 1, 1),
        (0.2, 0.8, 0.2, 1), (0.8, 0.2, 0.8, 1), (0.2, 0.2, 0.8, 1)
    ]

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Switch to Frame 1 for check
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    THRESHOLD = 0.001 
    total_facets_found = 0

    for obj in shards:
        obj.data.materials.clear()
        obj.data.materials.append(surf_mat)
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Identify inner faces via attribute
        attr = obj.data.attributes.get('Inner_faces')
        inner_faces = []
        if attr:
            for i, face in enumerate(bm.faces):
                if attr.data[i].value:
                    inner_faces.append(face)
        
        if not inner_faces:
            bm.free()
            continue

        # Step 1: Mapping - Face Index -> List of Neighbors within threshold
        # We find ALL neighbors to handle overlaps well.
        face_to_nb = {}
        for f in inner_faces:
            world_center = obj.matrix_world @ f.calc_center_median()
            nbs = []
            for other in shards:
                if other == obj: continue
                local_pos = other.matrix_world.inverted() @ world_center
                dist, pt, norm, f_idx = other.closest_point_on_mesh(local_pos)
                world_dist = (world_center - (other.matrix_world @ pt)).length
                if world_dist < THRESHOLD:
                    nbs.append(other.name)
            # Pick the absolute closest if multiple, or NONE
            if nbs:
                # Re-check for absolute best if multiple
                best_nb = "NONE"
                best_dist = THRESHOLD
                for nb_name in nbs:
                    other = bpy.data.objects[nb_name]
                    local_pos = other.matrix_world.inverted() @ world_center
                    dist, pt, norm, f_idx = other.closest_point_on_mesh(local_pos)
                    world_dist = (world_center - (other.matrix_world @ pt)).length
                    if world_dist < best_dist:
                        best_dist = world_dist
                        best_nb = nb_name
                face_to_nb[f.index] = best_nb
            else:
                face_to_nb[f.index] = "NONE"

        # Step 2: Spatial Propagation (Gap Filling)
        # If a face is NONE, give it the neighbor of its connected faces
        for _ in range(3): # Iterate a few times to propagate
            for f in inner_faces:
                if face_to_nb[f.index] == "NONE":
                    for e in f.edges:
                        for nf in e.link_faces:
                            if nf.index in face_to_nb and face_to_nb[nf.index] != "NONE":
                                face_to_nb[f.index] = face_to_nb[nf.index]
                                break
                        if face_to_nb[f.index] != "NONE": break

        # Step 3: Grouping (Connected AND same neighbor)
        unvisited = set(inner_faces)
        facets = []
        while unvisited:
            curr = unvisited.pop()
            nb_id = face_to_nb[curr.index]
            island = [curr]
            queue = [curr]
            while queue:
                f = queue.pop(0)
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf in unvisited and face_to_nb[nf.index] == nb_id:
                            unvisited.remove(nf)
                            island.append(nf)
                            queue.append(nf)
            facets.append(island)

        # Step 4: Apply Materials
        for i, facet in enumerate(facets):
            mat_name = f"RECON_V5_F{i}"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                mat.diffuse_color = palette[(total_facets_found + i) % len(palette)]
            obj.data.materials.append(mat)
            idx = len(obj.data.materials) - 1
            for f in facet:
                f.material_index = idx
        
        total_facets_found += len(facets)
        bm.to_mesh(obj.data)
        bm.free()

    bpy.context.scene.frame_set(current_frame)
    return f"V5 Resolution Complete: Found {total_facets_found} facets."

print(run_segmentation_v5_resolution())
