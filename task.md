# Create and Fragment Earthenware in Blender

- [x] Check Blender MCP connection and status <!-- id: 0 -->
- [x] Setup Git Repository (Version Control) <!-- id: 40 -->
- [x] Determine method (Search vs Generate vs Code) <!-- id: 1 -->
- [x] Execute creation of earthenware (Re-import) <!-- id: 2 -->
- [x] Apply fracture to the model (Script + Manual Apply) <!-- id: 5 -->
- [ ] separate fragments and verify (Manual Apply required) <!-- id: 6 -->
- [x] Install RBDLab Addon (User Manual Operation) <!-- id: 10 -->
- [x] Fracture and Simulate with RBDLab (Partial Automation) <!-- id: 11 -->
- [x] Add Floor and Gravity (Physics Setup) <!-- id: 12 -->

## Phase 3: Feasibility Verification (Technical Proof of Concept)
- [x] Check 1: Verify Fracture Label Extraction (Inner vs Outer) <!-- id: 30 -->
- [x] Check 2.5: Verify Facet Segmentation (Count & Color Islands) <!-- id: 35 -->
- [x] Check 2.7: Adjacency-Based Facet Splitting (V3) <!-- id: 36 -->
- [x] Check 2.8: Majority-Vote & Smoothing Segmentation (V6) <!-- id: 37 -->
- [x] Check 2: Adjacency Extraction (Connect pair of shards with lines) <!-- id: 5 -->
- [x] Check 3: Verify RBDLab Automation via Python <!-- id: 32 -->
- [x] Check 4: Verify Point Cloud & CSV Export <!-- id: 33 -->

## Phase 4: AI Training Data Generation (Sim2Real)
- [x] Create AI Training Plan (Augmentation & Labels) <!-- id: 20 -->
- [x] Step 1: Script for Procedural Pot Generation (Variety) <!-- id: 21 -->
- [ ] Step 2: Script for Wear & Tear (Erosion/Deletion) <!-- id: 22 -->
- [x] Step 3: Script for Point Cloud & Adjacency Export (Labeling) <!-- id: 23 -->
- [x] Step 4: Verify Data Quality (Visual Check) <!-- id: 24 -->
- [x] Tool: Create `mass_production.py` (Panel "土器(Pottery)") <!-- id: 50 -->
- [/] Execute Mass Production (Target: 500 pots) <!-- id: 51 -->
    - [x] Fix: Resolve "Shard 24" glitch (Open Bottom V5)
    - [/] Refine: Improve Pottery Generation Logic (V6)
        - [x] Restore Bottom (Flat & Safe Z-height)
        - [x] Add Shape Variety (Yayoi Style: Parametric Randomization)
    - [ ] 1. Continuous Loop: Apply -> Export & Next (Semi-Auto)
    - [ ] 2. Verify Output Count








- [ ] separate fragments and verify <!-- id: 6 -->
