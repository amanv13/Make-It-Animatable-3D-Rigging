# Make-It-Animatable 3D Rigging Pipeline
<a href="./LICENSE">
        <img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-blue.svg"></a>

## Introduction:
This Blender addon streamlines the process of working with 3DGS (3D Gaussian Splatting) scans in your 3D projects. Here's what it offers:

1.	Automatic Conversion: Seamlessly transforms.ply scan files into Blender-compatible objects.
2.	Eevee Compatibility: Converted objects are fully renderable with Blender's Eevee engine.
3.	Full Object Control: Manipulate your imported scans just like any other Blender object: 
    - Move, scale, and rotate with precision
    - Easily duplicate to populate your scenes
4.	Advanced Lighting Integration: 
    - Light-Reactive Objects: Imported scans fully interact with scene lighting for realistic rendering
    - Option for shadeless display to preserve the raw scan appearance
    - Seamlessly blend scans with other 3D elements in your scene
5.	Color Enhancement: Fine-tune the visual appeal of your scans with built-in color editing tools.
By bridging the gap between 3DGS technology and Blender's powerful ecosystem, this addon empowers artists and designers to seamlessly incorporate realistic, light-responsive scans into their 3D workflows.

This project demonstrates the local setup and execution of the [Make-It-Animatable](https://huggingface.co/jasongzy/Make-It-Animatable) pipeline for automatic 3D character rigging.

## 🔧 Tools & Frameworks
- Python (via Conda environment)
- PyTorch
- PyTorch3D
- Git LFS
- Blender (for `.obj` mesh preview and debugging)

  ## 💡 Workflow Summary
- Installed all required dependencies using `requirements.txt`.
- Cloned LFS assets via HuggingFace.
- Rigged custom `.obj` mesh locally using `app.py`.
- Manually managed submodule issues for clean GitHub upload.

## 🤝 Credits
Based on the original project by [Jason Gzy](https://huggingface.co/jasongzy/Make-It-Animatable).


## Installation:
❗❗Please note❗❗ The addon was made for the most current version of Blender at the time of writing - Blender 4.2 version. The addon will NOT work with previous versions of Blender. If you zip the installation package yourself, please make sure the zip file is named as: gs_render_by_kiri_engine.zip


