# ScoutBase — Match Analysis Pipeline

## Full Pipeline Execution Order

### Phase 1: Detection (GPU)
1. YOLO v11 detects all persons per frame
2. ByteTrack assigns persistent IDs across frames
3. Output: track_id → frame positions, bounding boxes

### Phase 2: Segmentation (GPU, optional)
4. SAM3 segments players by team (text-prompted: "blue jerseys", "red jerseys")
5. Ball detection and possession tracking
6. Output: team assignments per track_id

### Phase 3: Body Analysis (CPU)
7. MediaPipe Pose extracts body landmarks per player per sampled frame
8. Calculate joint angles, body lean, symmetry scores
9. Output: pose metrics per track_id

### Phase 4: Metrics (CPU)
10. Calculate per-player: distance, speed, sprints, heat zones
11. Calculate team-level: pressing intensity, formation shape
12. Output: full metrics JSON

### Phase 5: Video Production (CPU)
13. FFmpeg extracts per-player clips at key moments
14. FFmpeg generates highlight reel from top moments
15. FFmpeg generates thumbnail from peak action frame
16. Output: clip files, highlight.mp4, thumbnail.jpg

### Phase 6: Intelligence (API)
17. Scout Agent generates individual player assessments
18. Analyst Agent generates match performance report
19. Medical Agent flags injury risk patterns
20. Editor Agent generates highlight reel specifications
21. Output: scout_report.md, match_report.md, medical_flags.json, highlight_spec.json

### Phase 7: Delivery
22. All results saved to database (Supabase)
23. Video clips uploaded to storage (Supabase Storage)
24. Dashboard updated with new data
25. Notifications sent to subscribed scouts/clubs

## Error Handling
- Each phase is independent — failure in one doesn't block others
- SAM3 (Phase 2) is optional — system works without it
- MediaPipe (Phase 3) gracefully handles failed pose detections
- GPU phases can be offloaded to RunPod when local GPU unavailable

## Configuration
- All agent behaviors defined in markdown files in this directory
- Edit agent files to customize evaluation criteria per client
- League-specific configs in /agents/leagues/
