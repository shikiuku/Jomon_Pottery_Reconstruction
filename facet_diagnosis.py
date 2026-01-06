import bpy
import bmesh

def diagnose_facets_v5():
    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Switch to Frame 1 for check
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    THRESHOLD = 0.0005 # 0.5mm
    
    print("\n--- Diagnostic: Multi-Neighbor Facets ---")
    conflict_count = 0

    for obj in shards:
        # We assume materials represent facets (from previous V4 run)
        # Skip slot 0 (surface)
        for slot_idx in range(1, len(obj.data.materials)):
            mat = obj.data.materials[slot_idx]
            if not mat or "RECON" not in mat.name: continue
            
            # Find faces in this facet
            facet_faces = [f for f in obj.data.polygons if f.material_index == slot_idx]
            if not facet_faces: continue
            
            # Find ALL unique neighbors for this entire facet
            neighbors = set()
            for f in facet_faces:
                world_center = obj.matrix_world @ f.center
                for other in shards:
                    if other == obj: continue
                    local_pos = other.matrix_world.inverted() @ world_center
                    dist, pt, norm, f_idx = other.closest_point_on_mesh(local_pos)
                    world_dist = (world_center - (other.matrix_world @ pt)).length
                    
                    if world_dist < THRESHOLD:
                        neighbors.add(other.name)
            
            if len(neighbors) > 1:
                print(f"CONFLICT: Facet '{mat.name}' on {obj.name} touches multiple: {list(neighbors)}")
                conflict_count += 1
            elif len(neighbors) == 0:
                # This might also be an issue (orphan facet)
                # print(f"ORPHAN: Facet '{mat.name}' on {obj.name} touches NO ONE.")
                pass

    bpy.context.scene.frame_set(current_frame)
    return f"Diagnosis complete. Found {conflict_count} facets that need further splitting."

print(diagnose_facets_v5())
