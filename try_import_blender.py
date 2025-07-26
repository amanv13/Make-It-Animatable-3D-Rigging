import os
import sys
from glob import glob

import bpy
from tqdm import tqdm

from utils import HiddenPrints

if __name__ == "__main__":
    input_dir = "."
    character_list = sorted(glob(os.path.join(input_dir, "character", "*.fbx")))
    # animation_list = sorted(glob(os.path.join(input_dir, "animation", "*.fbx")))
    for filepath in tqdm(character_list, dynamic_ncols=True):
        try:
            with HiddenPrints():
                bpy.ops.import_scene.fbx(filepath=filepath)
        except Exception as e:
            tqdm.write(filepath)
            with open("character_old_fbx.txt", "a") as f:
                f.write(f"{filepath}\n")

    # https://aps.autodesk.com/developer/overview/fbx-converter-archives
    # Manually convert and replace FBX in the txt
