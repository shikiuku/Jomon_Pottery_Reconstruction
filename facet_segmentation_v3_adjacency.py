import bpy
import bmesh
from mathutils import Vector, kdtree

def run_segmentation_v3_adjacency():
    # 1. Setup Base Materials
    surf_mat = bpy.data.materials.get("RECON_Surface")
    if not surf_mat:
        surf_mat = bpy.data.materials.new(name="RECON_Surface")
    surf_mat.diffuse_color = (0.05, 0.05, 0.05, 1.0)
    
    # Material palette for facets
    palette = [
        (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), 
        (1, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 1), 
        (1, 1, 1, 1), (1, 0.5, 0, 1), (0.5, 0, 1, 1),
        (0.5, 0.5, 0, 1), (0, 0.5, 0.5, 1), (0.5, 0, 0.5, 1)
    ]

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    print(f"Starting Adjacency-Based Segmentation on {len(shards)} shards...")

    # Save current frame and go to Frame 1 (initial contact)
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    # Threshold for proximity (0.2mm - adjust if fragmentation is rough)
    PROXIMITY_THRESHOLD = 0.0002 

    # 2. Build KDTree for center of all other shards' faces to speed up search?
    # Actually, let's do it per-shard to find the "neighbor shard".
    
    total_refined_facets = 0

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
            for i, face in enumerate(bm.faces):
                if attr.data[i].value:
                    inner_faces.append(face)
        
        if not inner_faces:
            bm.free()
            continue

        # A. Geometric Segmentation (Islands)
        unvisited = set(inner_faces)
        geo_islands = []
        angle_threshold = 0.7 
        
        while unvisited:
            start_face = unvisited.pop()
            current_island = [start_face]
            queue = [start_face]
            while queue:
                f = queue.pop(0)
                for edge in f.edges:
                    for nf in edge.link_faces:
                        if nf != f and nf in unvisited:
                            if f.normal.angle(nf.normal) < angle_threshold:
                                unvisited.remove(nf)
                                current_island.append(nf)
                                queue.append(nf)
            geo_islands.append(current_island)

        # B. Adjacency Refinement (Split islands by neighbor)
        refined_facets = [] # List of face groups
        
        for island in geo_islands:
            # Map each face in this island to the nearest OTHER shard
            face_to_neighbor = {} # Face index -> Neighbor Object Name
            
            for face in island:
                face_center_world = obj.matrix_world @ face.calc_center_median()
                
                closest_neighbor_name = "NONE"
                min_dist = PROXIMITY_THRESHOLD
                
                for other in shards:
                    if other == obj: continue
                    
                    # Find closest point on neighbor mesh
                    # Using world space coordinates
                    local_pos = other.matrix_world.inverted() @ face_center_world
                    dist, pt, normal, face_idx = other.closest_point_on_mesh(local_pos)
                    
                    world_dist = (face_center_world - (other.matrix_world @ pt)).length
                    
                    if world_dist < min_dist:
                        min_dist = world_dist
                        closest_neighbor_name = other.name
                
                face_to_neighbor[face.index] = closest_neighbor_name
            
            # Group faces in this geometric island by neighbor
            neighbor_groups = {}
            for face in island:
                nb = face_to_neighbor[face.index]
                if nb not in neighbor_groups:
                    neighbor_groups[nb] = []
                neighbor_groups[nb].append(face)
            
            # Each neighbor group becomes a separate Refined Facet
            for nb_name, faces in neighbor_groups.items():
                refined_facets.append(faces)

        # C. Visualization
        for i, facet_faces in enumerate(refined_facets):
            mat_name = f"RECON_Refined_{i % 100}" # Reuse names if too many
            f_mat = bpy.data.materials.get(mat_name)
            if not f_mat:
                f_mat = bpy.data.materials.new(name=mat_name)
                # Color from palette
                color_idx = (total_refined_facets + i) % len(palette)
                f_mat.diffuse_color = palette[color_idx]
            
            obj.data.materials.append(f_mat)
            slot_idx = len(obj.data.materials) - 1
            
            for face in facet_faces:
                face.material_index = slot_idx

        total_refined_facets += len(refined_facets)
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # Restore frame
    bpy.context.scene.frame_set(current_frame)
    
    # Shading update
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'
                space.shading.light = 'FLAT'
                space.shading.color_type = 'MATERIAL'

    return f"Refinement Complete: Processed {len(shards)} shards. Found {total_refined_facets} unique facets (1-to-1 candidates)."

print(run_segmentation_v3_adjacency())
