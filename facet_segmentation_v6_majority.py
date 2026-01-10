import bpy
import bmesh
from collections import Counter

def run_segmentation_v6_majority(target_objects=None):
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

    if target_objects:
        shards = target_objects
    else:
        # Default selector for testing (supports RND_Pot and Pot_XXX)
        shards = [obj for obj in bpy.data.objects if ("RND_Pot" in obj.name or "Pot_" in obj.name) and ("cell" in obj.name.lower() or "Cell" in obj.name) and obj.type == 'MESH']
    
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    THRESHOLD = 0.001 # 1mm for contact
    ITERATIONS = 5    # Number of smoothing passes

    total_facets_found = 0

    for obj in shards:
        # Reset Materials
        obj.data.materials.clear()
        obj.data.materials.append(surf_mat)
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        
        # Identify inner faces
        attr = obj.data.attributes.get('Inner_faces')
        inner_faces = []
        if attr:
            try:
                for i, face in enumerate(bm.faces):
                    if attr.data[i].value:
                        inner_faces.append(face)
            except: pass
        
        if not inner_faces:
            bm.free()
            continue

        # Step 1: Initial Labeling (Closest Neighbor)
        face_labels = {} # face.index -> neighbor_name
        for f in inner_faces:
            world_center = obj.matrix_world @ f.calc_center_median()
            best_nb = "NONE"
            best_dist = THRESHOLD
            
            for other in shards:
                if other == obj: continue
                local_pos = other.matrix_world.inverted() @ world_center
                dist, pt, norm, f_idx = other.closest_point_on_mesh(local_pos)
                world_dist = (world_center - (other.matrix_world @ pt)).length
                if world_dist < best_dist:
                    best_dist = world_dist
                    best_nb = other.name
            face_labels[f.index] = best_nb

        # Step 2: Spatial Smoothing (Majority Vote Propagation)
        # This handles noise and orphans.
        for _ in range(ITERATIONS):
            new_labels = face_labels.copy()
            for f in inner_faces:
                # Get labels of all connected faces (including self)
                neighbor_labels = [face_labels[f.index]]
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf.index in face_labels:
                            neighbor_labels.append(face_labels[nf.index])
                
                # Exclude NONE from vote if there are alternatives
                votes = [L for L in neighbor_labels if L != "NONE"]
                if votes:
                    majority_label = Counter(votes).most_common(1)[0][0]
                    new_labels[f.index] = majority_label
                else:
                    new_labels[f.index] = "NONE"
            face_labels = new_labels

        # Step 3: Island Grouping (Connected AND Same Label)
        unvisited = set(inner_faces)
        final_facets = []
        while unvisited:
            start_f = unvisited.pop()
            label = face_labels[start_f.index]
            island = [start_f]
            queue = [start_f]
            while queue:
                f = queue.pop(0)
                for e in f.edges:
                    for nf in e.link_faces:
                        if nf in unvisited and face_labels[nf.index] == label:
                            unvisited.remove(nf)
                            island.append(nf)
                            queue.append(nf)
            final_facets.append(island)

        # Step 4: Final Visualization
        for i, facet in enumerate(final_facets):
            # Final 1-to-1 Check: If a facet still touches NO ONE (NONE), 
            # we should probably give it a 'Void' color or merge with the largest colored neighbor.
            label = face_labels[facet[0].index]
            
            mat_name = f"RECON_V6_{label}_{i}"
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                mat = bpy.data.materials.new(name=mat_name)
                # Assign distinct color
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

    return f"V6 Majority-Vote Complete: Found {total_facets_found} facets."

# Alias for external tools
def apply_segmentation_to_objects(objects):
    return run_segmentation_v6_majority(target_objects=objects)

if __name__ == "__main__":
    print(run_segmentation_v6_majority())
