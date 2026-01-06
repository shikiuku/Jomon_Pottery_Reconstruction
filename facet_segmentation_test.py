import bpy
import bmesh
import random

def segment_facets():
    # 1. Selection
    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    if not shards:
        print("No shards found.")
        return
    
    # Select the first shard for the test
    target = shards[0]
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    
    # 2. Extract Inner Faces using the attribute we found earlier
    bm = bmesh.new()
    bm.from_mesh(target.data)
    
    inner_faces = []
    # Find attribute
    attr = target.data.attributes.get('Inner_faces')
    if not attr:
        print("Attribute 'Inner_faces' not found.")
        return
        
    for i, face in enumerate(bm.faces):
        if attr.data[i].value:
            inner_faces.append(face)
            
    if not inner_faces:
        print("No inner faces found on this shard.")
        return

    print(f"Total inner faces found: {len(inner_faces)}")

    # 3. Group Faces into Islands (Segmentation)
    # We group faces if they share an edge AND the angle between them is small.
    unvisited = set(inner_faces)
    islands = []
    
    angle_threshold = 0.5 # Radians (approx 30 degrees)
    
    while unvisited:
        start_face = unvisited.pop()
        current_island = [start_face]
        queue = [start_face]
        
        while queue:
            f = queue.pop(0)
            # Find neighbors sharing an edge
            for edge in f.edges:
                for nf in edge.link_faces:
                    if nf != f and nf in unvisited:
                        # Check Normal Angle
                        # Internal fracture surfaces might have sharp bends at corners
                        angle = f.normal.angle(nf.normal)
                        if angle < angle_threshold:
                            unvisited.remove(nf)
                            current_island.append(nf)
                            queue.append(nf)
                            
        islands.append(current_island)

    print(f"Identified {len(islands)} distinct facets (islands).")

    # 4. Colorization Proof
    # Create materials for each island
    target.data.materials.clear()
    
    for i, island in enumerate(islands):
        mat_name = f"Facet_Mat_{i}"
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
        
        # Random colorful color
        mat.diffuse_color = (random.random(), random.random(), random.random(), 1.0)
        target.data.materials.append(mat)
        
        # Assign faces to this material slot
        for face in island:
            face.material_index = i

    # Update Mesh
    bm.to_mesh(target.data)
    bm.free()
    
    # Force Viewport to show Material Colors
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D':
                space.shading.color_type = 'MATERIAL'
    
    return f"Successfully segmented {len(islands)} facets on {target.name} and colored them."

result = segment_facets()
print(result)
