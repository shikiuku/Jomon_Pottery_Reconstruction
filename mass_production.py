import bpy
import os
import sys
import importlib

# Ensure path is available for imports
sys.path.append(r"c:\Users\k4849\Documents\VibeCording\Jomon_Pottery_Reconstruction")
import generate_random_pots
import export_shards_data
import verify_rbdlab_automation # We'll borrow fracture setup logic if needed, or implement here

# Force reload
importlib.reload(generate_random_pots)
importlib.reload(export_shards_data)

class JomonFactoryProperties(bpy.types.PropertyGroup):
    output_path: bpy.props.StringProperty(
        name="Output Path",
        default=r"c:\Users\k4849\Documents\VibeCording\Jomon_Pottery_Reconstruction\dataset_manual_batch_001",
        subtype='DIR_PATH'
    )
    current_id: bpy.props.IntProperty(name="Current ID", default=10, min=1)
    
    promo_grid_rows: bpy.props.IntProperty(
        name="Grid Rows",
        description="Number of rows for the promo grid",
        default=10,
        min=1,
        max=50
    )
    promo_grid_cols: bpy.props.IntProperty(
        name="Grid Cols",
        description="Number of columns for the promo grid",
        default=10,
        min=1,
        max=50
    )

class JOMON_OT_GeneratePot(bpy.types.Operator):
    """Generates a new pot and prepares it for fracturing."""
    bl_idname = "jomon.generate_pot"
    bl_label = "1. Generate & Fracture Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("--- RUNNING GENERATE POT V3 (Fix Cleanup) ---")
        props = context.scene.jomon_props
        
        # 1. Determine Next ID from folder scan
        # Scan explicitly to be safe
        existing_pots = []
        if os.path.exists(props.output_path):
            for d in os.listdir(props.output_path):
                if d.startswith("Pot_") and os.path.isdir(os.path.join(props.output_path, d)):
                    try:
                        num = int(d.split("_")[1])
                        existing_pots.append(num)
                    except: pass
        
        next_id = 1
        if existing_pots:
            next_id = max(existing_pots) + 1
        
        props.current_id = next_id
        
        # 2. Cleanup Scene (delete old RND_Pot_*, PROOF_*, etc.)
    bl_label = "1. Spawn & Fracture"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.jomon_props
        
        # 1. Cleanup Scene First (Aggressive)
        bpy.ops.jomon.cleanup_only()
        
        # 2. Generate Pot
        pot_name = f"Pot_{props.current_id:03d}"
        location = (0, 0, 0) # Center
        
        try:
            # Create Floor if missing (Hidden)
            generate_random_pots.create_floor(size=20, location=(0,0,-0.2))
            
            # Create Pot
            # NOTE: generates 'Tempo_Pot' then renames
            pot_obj = generate_random_pots.create_random_pot(name="Temp_Pot", location=(0,0,0)) 
            pot_obj.name = pot_name
            
            # Ensure it is active
            bpy.context.view_layer.objects.active = pot_obj
            pot_obj.select_set(True)
            
        except Exception as e:
            self.report({'ERROR'}, f"Generation Failed: {e}")
            return {'CANCELLED'}
        
        # 3. Setup Rigid Body World if missing
        if not bpy.context.scene.rigidbody_world:
            bpy.ops.rigidbody.world_add()
            
        # 4. RBDLab Autos Setup & Fracture
        try:
            # Set scatter count (randomize slightly to avoid deterministic glitches)
            import random
            count = random.randint(45, 65)
            bpy.context.scene.rbdlab.scatter_count = count
            
            # Add Scatter
            # bpy.ops.rbdlab.scatter_add()
            
            # Enable Cell Fracture Mode
            # bpy.context.scene.rbdlab.current_using_cell_fracture = True
            
            # Execute Fracture (This creates the cells but DOES NOT Apply Physics yet)
            # bpy.ops.rbdlab.cellfracture()
            
            self.report({'INFO'}, f"Generated {pot_name}. (Fracture Disabled for Debug)")
            
        except Exception as e:
            self.report({'WARNING'}, f"RBDLab Auto-Fracture Failed: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

class JOMON_OT_HideOriginal(bpy.types.Operator):
    """Manually hides the original pot if it overlaps."""
    bl_idname = "jomon.hide_original"
    bl_label = "Hide Original (Visual Check)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Scan for ANY object that looks like a Pot but isn't a shard
        count = 0
        for obj in bpy.data.objects:
            if "Pot_" in obj.name:
                 # Check if it's a shard (has 'cell' or 'fracture' or is the Low poly wrapper)
                 # Logic: If it DOES NOT have 'cell' in name (case insensitive), it's likely an original (or the low poly original)
                 # Note: RBDLab creates 'Pot_xxx_Low' often. We want to hide that too.
                 if "cell" not in obj.name.lower() and "fracture" not in obj.name.lower():
                     obj.hide_viewport = True
                     obj.hide_render = True
                     count += 1
        
        if count > 0:
            self.report({'INFO'}, f"Hidden {count} original objects.")
        else:
            self.report({'WARNING'}, "No original objects found to hide.")
            
        return {'FINISHED'}

class JOMON_OT_ExportNext(bpy.types.Operator):
    """Exports the currently fractured shards and cleans up."""
    bl_idname = "jomon.export_next"
    bl_label = "2. Export & Next Pot >>"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.jomon_props
        pot_id_str = f"Pot_{props.current_id:03d}"
        target_dir = os.path.join(props.output_path, pot_id_str)
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # check if we have shards
        shards = [o for o in bpy.data.objects if pot_id_str in o.name and ("cell" in o.name.lower() or "Cell" in o.name)]
        
        if len(shards) < 2:
            self.report({'WARNING'}, "No shards found! Did you click 'Apply Fractures'?")
            return {'CANCELLED'}
        
        # Force Hide Original before export (just in case)
        bpy.ops.jomon.hide_original()
        
        try:
            self.export_single_pot(shards, target_dir, pot_id_str)
            self.report({'INFO'}, f"Exported {pot_id_str} Success!")
            
            # --- WANKO SOBA MODE: Cleanup & Next ---
            # 1. Delete everything
            bpy.ops.jomon.cleanup_only()
            
            # 2. Increment ID
            props.current_id += 1
            
            # 3. Spawn Next
            bpy.ops.jomon.generate_pot()
            
        except Exception as e:
            self.report({'ERROR'}, f"Export Failed: {e}")
            return {'CANCELLED'}

    def export_single_pot(self, shards, folder, pot_name):
        import json
        import bmesh
        from mathutils.bvhtree import BVHTree
        from mathutils import Vector
        import random
        
        # 1. Adjacency
        bpy.context.scene.frame_set(1)
        bpy.context.view_layer.update()
        
        facet_data = []
        mat_to_id = {}
        id_counter = 1
        
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
        
        adjacency_list = []
        pairs_set = set()
        
        for i, f1 in enumerate(facet_data):
            best = None
            min_d = 1000.0
            
            for j, f2 in enumerate(facet_data):
                if i == j: continue
                if f1['nb_name'] == f2['obj_name'] and f2['nb_name'] == f1['obj_name']:
                    d = (f1['pos'] - f2['pos']).length
                    if d < 2.0 and d < min_d:
                        min_d = d
                        best = j
            if best is not None:
                f2 = facet_data[best]
                pair = sorted([f1['id'], f2['id']])
                tp = tuple(pair)
                if tp not in pairs_set:
                    pairs_set.add(tp)
                    adjacency_list.append(pair)
                    
        with open(os.path.join(folder, "adjacency.json"), 'w') as f:
            json.dump(adjacency_list, f, indent=4)
            
        # Run Segmentation logic (using external script logic inline or imported)
        # Using imported for stability as defined in 'export_shards_data.py' logic
        try:
            import facet_segmentation_v6_majority
            importlib.reload(facet_segmentation_v6_majority)
            facet_segmentation_v6_majority.apply_segmentation_to_objects(shards)
        except Exception as e:
            print(f"Segmentation Warning: {e}")

        for obj in shards:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bm.transform(obj.matrix_world)
            bvh = BVHTree.FromBMesh(bm)
            bm.faces.ensure_lookup_table()
            total_area = sum(f.calc_area() for f in bm.faces)
            points = []
            
            for _ in range(2048):
                 r = random.uniform(0, total_area)
                 acc = 0
                 target = bm.faces[0]
                 for f in bm.faces:
                     acc += f.calc_area()
                     if acc >= r: target = f; break
                 
                 p = target.calc_center_bounds()
                 _, n, fidx, _ = bvh.find_nearest(p)
                 mat_idx = bm.faces[fidx].material_index
                 mat = obj.data.materials[mat_idx]
                 
                 lbl = 0
                 if mat and "RECON_V6_" in mat.name:
                     lbl = mat_to_id.get((obj.name, mat.name), 0)
                     
                 points.append({'pos': [p.x, p.y, p.z], 'norm': [n.x, n.y, n.z], 'label': lbl})
            
            with open(os.path.join(folder, f"{obj.name}.json"), 'w') as f:
                json.dump(points, f)
            bm.free()

class JOMON_OT_GeneratePromoGrid(bpy.types.Operator):
    """Generates a grid of random pots for promotion."""
    bl_idname = "jomon.generate_promo_grid"
    bl_label = "Generate Grid"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            # Clean first
            bpy.ops.jomon.cleanup_only()
            
            props = context.scene.jomon_props
            r = props.promo_grid_rows
            c = props.promo_grid_cols
            
            # Generate grid with user-defined size
            generate_random_pots.generate_verification_grid(rows=r, cols=c, spacing=1.0)
            
            self.report({'INFO'}, f"Generated {r}x{c} Promo Grid!")
        except Exception as e:
             self.report({'ERROR'}, f"Grid Gen Failed: {e}")
             return {'CANCELLED'}
        return {'FINISHED'}

class JOMON_OT_CleanupOnly(bpy.types.Operator):
    """Emergency Cleanup: Deletes all pots and shards."""
    bl_idname = "jomon.cleanup_only"
    bl_label = "Emergency Cleanup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Explicitly remove handler if it exists (Leftover cleanup)
        try:
             if bpy.app.handlers.depsgraph_update_post:
                 bpy.app.handlers.depsgraph_update_post.clear()
        except: pass

        to_delete = []
        for obj in bpy.data.objects:
             # Broad match for project objects
            if "Pot_" in obj.name or "RND_" in obj.name or "cell" in obj.name or "Temp_" in obj.name or "Cube" in obj.name:
                to_delete.append(obj)
            if "_Low" in obj.name:
                to_delete.append(obj)
        
        for obj in to_delete:
            try:
                bpy.data.objects.remove(obj, do_unlink=True)
            except: pass
            
        self.report({'INFO'}, "Scene Cleaned.")
        return {'FINISHED'}

class JOMON_PT_FactoryPanel_V9(bpy.types.Panel):
    bl_label = "土器生産ツール V9 (Grid Config)"
    bl_idname = "JOMON_PT_factory_v9"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "土器(Pottery)"

    def draw(self, context):
        layout = self.layout
        props = context.scene.jomon_props
        
        layout.prop(props, "output_path")
        layout.prop(props, "current_id")
        
        layout.separator()
        layout.label(text="Loop Operation:")
        
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator("jomon.generate_pot", text="1. Spawn Only (Debug)", icon='PLAY')
        col.label(text="↓ Click Apply in RBDLab (Wait for Shards) ↓")
        col.operator("jomon.export_next", text="2. Export & Next Pot >>", icon='FORWARD')
        
        layout.separator()
        layout.label(text="Verification:")
        
        row = layout.row(align=True)
        row.prop(props, "promo_grid_rows", text="Rows")
        row.prop(props, "promo_grid_cols", text="Cols")
        
        layout.operator("jomon.generate_promo_grid", text="Generate Verification Grid", icon='GRID')
        layout.operator("jomon.cleanup_only", text="Clear Scene", icon='TRASH')

classes = [JomonFactoryProperties, JOMON_OT_GeneratePot, JOMON_OT_HideOriginal, JOMON_OT_ExportNext, JOMON_OT_GeneratePromoGrid, JOMON_OT_CleanupOnly, JOMON_PT_FactoryPanel_V9]

def register():
    # Aggressive Cleanup of Old Panels
    for cls in bpy.types.Panel.__subclasses__():
        if hasattr(cls, 'bl_idname') and cls.bl_idname.startswith("JOMON_PT_factory"):
            try:
                bpy.utils.unregister_class(cls)
                print(f"Removed old panel: {cls.bl_idname}")
            except: pass

    for cls in classes:
        try:
           bpy.utils.unregister_class(cls)
        except: pass
        bpy.utils.register_class(cls)
    bpy.types.Scene.jomon_props = bpy.props.PointerProperty(type=JomonFactoryProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.jomon_props
    
    # Ensure handlers are cleared
    try:
        bpy.app.handlers.depsgraph_update_post.clear()
    except: pass

if __name__ == "__main__":
    register()
    print("Jomon Factory V8 Loaded.")
