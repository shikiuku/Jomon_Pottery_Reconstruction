import bpy
import bmesh
import random

def run_segmentation_v2():
    # 1. Setup Base Materials
    # Surface (Slot 0) - Dark Grey/Black for contrast
    surf_mat = bpy.data.materials.get("RECON_Surface")
    if not surf_mat:
        surf_mat = bpy.data.materials.new(name="RECON_Surface")
    surf_mat.diffuse_color = (0.05, 0.05, 0.05, 1.0)
    
    # 2. Distinct Color Palette for Facets (Red, Green, Blue, Yellow, Cyan, Magenta, White)
    palette = [
        (1, 0, 0, 1), # Red
        (0, 1, 0, 1), # Green
        (0, 0, 1, 1), # Blue
        (1, 1, 0, 1), # Yellow
        (0, 1, 1, 1), # Cyan
        (1, 0, 1, 1), # Magenta
        (1, 1, 1, 1), # White
        (1, 0.5, 0, 1), # Orange
        (0.5, 0, 1, 1), # Purple
    ]

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    print(f"Starting segmentation on {len(shards)} shards...")

    total_facets_found = 0

    for obj in shards:
        # Reset Materials
        obj.data.materials.clear()
        obj.data.materials.append(surf_mat) # Slot 0 always surface
        
        # Open BMesh
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # Find fracture faces via attribute
        attr = obj.data.attributes.get('Inner_faces')
        inner_faces = []
        if attr:
            for i, face in enumerate(bm.faces):
                if attr.data[i].value:
                    inner_faces.append(face)
        
        # If no attribute, fallback to material index or name (but attribute is best)
        
        if not inner_faces:
            bm.free()
            continue

        # Segment Islands
        unvisited = set(inner_faces)
        islands = []
        angle_threshold = 0.7 # Approx 40 degrees (looser to catch subtle curves)
        
        while unvisited:
            start_face = unvisited.pop()
            current_island = [start_face]
            queue = [start_face]
            
            while queue:
                f = queue.pop(0)
                for edge in f.edges:
                    for nf in edge.link_faces:
                        if nf != f and nf in unvisited:
                            # Group if angle is smooth
                            if f.normal.angle(nf.normal) < angle_threshold:
                                unvisited.remove(nf)
                                current_island.append(nf)
                                queue.append(nf)
            islands.append(current_island)

        # Assign materials to islands
        for i, island in enumerate(islands):
            mat_name = f"RECON_Facet_{i}"
            f_mat = bpy.data.materials.get(mat_name)
            if not f_mat:
                f_mat = bpy.data.materials.new(name=mat_name)
                # Assign from palette or random if out of palette
                if i < len(palette):
                    f_mat.diffuse_color = palette[i]
                else:
                    f_mat.diffuse_color = (random.random(), random.random(), random.random(), 1.0)
            
            # Add to object slots if not there
            if f_mat.name not in [m.name for m in obj.data.materials if m]:
                obj.data.materials.append(f_mat)
            
            # Find the actual index in this object
            actual_idx = -1
            for slot_idx, m in enumerate(obj.data.materials):
                if m == f_mat:
                    actual_idx = slot_idx
                    break
            
            for face in island:
                face.material_index = actual_idx
        
        total_facets_found += len(islands)
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    # 3. Viewport Correction
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D':
                space.shading.type = 'SOLID'
                space.shading.light = 'FLAT'
                space.shading.color_type = 'MATERIAL'

    return f"Processed {len(shards)} shards. Found {total_facets_found} facets total. Viewport: Black Surface, Rainbow Facets."

print(run_segmentation_v2())
