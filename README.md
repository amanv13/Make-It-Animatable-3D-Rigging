---
tags:
- 3d
viewer: false
---

# Make-It-Animatable: An Efficient Framework for Authoring Animation-Ready 3D Characters

- [Paper](https://arxiv.org/abs/2411.18197)
- [Project Page](https://jasongzy.github.io/Make-It-Animatable/)

## Data

- `character`: 95 characters (T-pose with bones and texture) downloaded from [Mixamo](https://www.mixamo.com/#/?page=1&type=Character)

- `character_fbx_upgraded`: 51 (among 95) characters with FBX version upgraded by [FBX Converter](https://aps.autodesk.com/developer/overview/fbx-converter-archives) (so that they can be imported into [Blender](https://www.blender.org/))

- **`character_refined`**: all 95 characters (triangle mesh without texture, animatable by any one from `animation`) processed with `character_refine.py`
  - vertices: 2374 ~ 35128 (average: 15482; details in `character_verts.json`)
  - bones: 42 ~ 112 (mostly standard 65 *mixamorig* bones; details in `character_bones.txt`)

- **`animation`**: 2453 animations (only bones) downloaded from [Mixamo](https://www.mixamo.com/#/?page=1&type=Motion)
  - frames: 2 ~ 2801 (average: 212; details in `animation_frames.json`)

## Reproduction

1. Download characters and animations from [Mixamo](https://www.mixamo.com/).

2. Convert old-version FBX (`try_import_blender.py` > `character_old_fbx.txt`) with [FBX Converter](https://aps.autodesk.com/developer/overview/fbx-converter-archives).

3. Rename corrupted bone names in unposed characters (`character_unposed.txt`).

4. Convert all characters into **triangle mesh without texture** with [Blender](https://docs.blender.org/api/current/info_advanced_blender_as_bpy.html).
