import bpy
import bmesh
from mathutils import Vector

def update_adjacency_lines(scene):
    line_col = bpy.data.collections.get("Adjacency_Lines")
    if not line_col: return

    # 1. Gather Facet Centroids at current frame
    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    
    # Store world centroids: facet_name_map[mat_name] = Vector
    facet_pos = {}
    
    for obj in shards:
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name: continue
            
            # Use a cached local centroid if possible to avoid recalculating bmesh every frame
            # For now, we calculate it (simple enough for 30 shards)
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid = obj.matrix_world @ local_centroid
            facet_pos[(obj.name, mat.name)] = world_centroid

    # 2. Update line objects
    # We use a naming convention for line objects: "Line_ShardA_MatA_ShardB_MatB"
    for line_obj in line_col.objects:
        if not line_obj.name.startswith("Line_"): continue
        
        # Data is stored in the name or we can use custom properties
        parts = line_obj.get("pair_info")
        if not parts: continue
        
        # pair_info format: [objA_name, matA_name, objB_name, matB_name]
        p1 = facet_pos.get((parts[0], parts[1]))
        p2 = facet_pos.get((parts[2], parts[3]))
        
        if p1 and p2:
            # Update vertex positions
            line_obj.data.vertices[0].co = p1
            line_obj.data.vertices[1].co = p2

def setup_dynamic_visualization():
    # 1. Match pairs at Frame 1
    current_frame = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    shards = [obj for obj in bpy.data.objects if "Lathe_Pot_cell" in obj.name and obj.type == 'MESH']
    facet_data = []
    
    for obj in shards:
        for i, mat in enumerate(obj.data.materials):
            if not mat or "RECON_V6_" not in mat.name: continue
            # Extract neighbor name
            core_name = mat.name[9:] 
            nb_name = "_".join(core_name.split('_')[:-1])
            
            faces = [f for f in obj.data.polygons if f.material_index == i]
            if not faces: continue
            
            local_centroid = sum((f.center for f in faces), Vector()) / len(faces)
            world_centroid_f1 = obj.matrix_world @ local_centroid
            
            facet_data.append({
                'obj_name': obj.name,
                'nb_name': nb_name,
                'mat_name': mat.name,
                'f1_pos': world_centroid_f1
            })

    # 2. Create/Prepare the Line Collection
    line_col = bpy.data.collections.get("Adjacency_Lines")
    if line_col:
        for o in line_col.objects: bpy.data.objects.remove(o, do_unlink=True)
    else:
        line_col = bpy.data.collections.new("Adjacency_Lines")
        bpy.context.scene.collection.children.link(line_col)

    # 3. Pair and Create Static Line Objects (to be updated dynamically)
    matched_count = 0
    for i, f1 in enumerate(facet_data):
        for j, f2 in enumerate(facet_data):
            if i >= j: continue
            if f1['nb_name'] == f2['obj_name'] and f2['nb_name'] == f1['obj_name']:
                if (f1['f1_pos'] - f2['f1_pos']).length < 0.005:
                    # Create a simple 2-vertex mesh
                    mesh = bpy.data.meshes.new(f"L_{matched_count}")
                    line_obj = bpy.data.objects.new(f"Line_{matched_count}", mesh)
                    line_col.objects.link(line_obj)
                    
                    # Store data for the handler to use
                    line_obj["pair_info"] = [f1['obj_name'], f1['mat_name'], f2['obj_name'], f2['mat_name']]
                    
                    # Initialize with 2 vertices
                    bm = bmesh.new()
                    bm.verts.new((0,0,0))
                    bm.verts.new((0,0,0))
                    bm.edges.new(bm.verts)
                    bm.to_mesh(mesh)
                    bm.free()
                    matched_count += 1

    # Return to current frame
    bpy.context.scene.frame_set(current_frame)
    
    # 4. Register the Handler
    # Remove existing to avoid duplicates
    bpy.app.handlers.frame_change_post.clear()
    bpy.app.handlers.frame_change_post.append(update_adjacency_lines)
    
    # Run once immediately
    update_adjacency_lines(bpy.context.scene)
    
    return f"Dynamic Visualization Ready: {matched_count} lines registered."

print(setup_dynamic_visualization())
