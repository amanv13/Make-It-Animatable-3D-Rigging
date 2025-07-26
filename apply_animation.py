import os
from glob import glob

from tqdm import tqdm

if __name__ == "__main__":
    character_dir = "./character_vroid_refined"
    animation_dir = "./animation"
    output_dir = "./animated_vroid"
    os.makedirs(output_dir, exist_ok=True)

    character_list = sorted(glob(os.path.join(character_dir, "*.fbx")))
    assert character_list
    animation_list = sorted(glob(os.path.join(animation_dir, "*.fbx")))
    assert animation_list
    get_base_name = lambda s: os.path.splitext(os.path.basename(s))[0]
    for char_file in tqdm(character_list, dynamic_ncols=True, desc="Character"):
        for anim_file in tqdm(animation_list, dynamic_ncols=True, leave=False, desc="Animation"):
            output_filename = f"{get_base_name(char_file)}-{get_base_name(anim_file)}"
            if os.path.isfile(os.path.join(output_dir, f"{output_filename}.fbx")):
                continue
            # Call subprocess to avoid accumulation bugs that gradually slow down the process
            os.system(
                f"python apply_animation_blender.py --char_path {char_file} --anim_path {anim_file} --output_dir {output_dir}"
            )
