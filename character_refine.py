import os
from glob import glob

import bpy
from tqdm import tqdm

from utils import (
    HiddenPrints,
    get_all_armature_obj,
    get_rest_bones,
    load_file,
    mesh_quads2tris,
    remove_all,
    select_objs,
)


def rename_mixamo_bone(armature_obj):
    """Replace name like 'mixamorig10:xxx' to 'mixamorig:xxx, so that character can be correctly animated.'"""
    import re

    pattern = re.compile(r"mixamorig[0-9]+:")
    for bone in armature_obj.data.bones:
        bone.name = re.sub(pattern, "mixamorig:", bone.name)
    return armature_obj


if __name__ == "__main__":
    input_dir = "."
    keep_texture = False
    output_dir = os.path.join(input_dir, "character_refined")
    if keep_texture:
        output_dir += "_textured"
    os.makedirs(output_dir, exist_ok=True)
    character_list = sorted(glob(os.path.join(input_dir, "character", "*.fbx")))
    character_list_upgraded = sorted(glob(os.path.join(input_dir, "character_fbx_upgraded", "*.fbx")))
    character_list_upgraded = {os.path.basename(x): x for x in character_list_upgraded}
    for i, path in enumerate(character_list):
        path_upgraded = character_list_upgraded.get(os.path.basename(path))
        if path_upgraded is not None:
            character_list[i] = path_upgraded
    animation_list = sorted(glob(os.path.join(input_dir, "animation", "*.fbx")))
    unposed_list_file = "character_unposed.txt"
    if os.path.isfile(unposed_list_file):
        with open(unposed_list_file, "r") as f:
            unposed_list = f.readlines()
        unposed_list = [x.strip() for x in unposed_list if x.strip() != ""]
    else:
        unposed_list = None
    logfile = "character_bones.txt"

    bones_name_list = []
    for file in tqdm(character_list, dynamic_ncols=True):
        try:
            with HiddenPrints():
                remove_all()
                obj_list = load_file(file)
                armature_obj = get_all_armature_obj(obj_list)
                assert len(armature_obj) == 1, "Armature number is not 1"
                armature_obj = armature_obj[0]
                if unposed_list is None or file in unposed_list:
                    rename_mixamo_bone(armature_obj)
                rest_bones, bones_idx_dict = get_rest_bones(armature_obj)

                # mesh_quads2tris(get_all_mesh_obj(obj_list))
                select_objs(obj_list, deselect_first=True)
                bpy.ops.export_scene.fbx(
                    filepath=os.path.join(output_dir, os.path.basename(file)),
                    check_existing=False,
                    use_selection=True,
                    use_triangles=True,  # !
                    add_leaf_bones=False,
                    bake_anim=False,
                    path_mode="COPY",
                    embed_textures=keep_texture,
                )
            bones_name_list += list(bones_idx_dict.keys())
            with open(logfile, "a") as f:
                f.write(f"{file}: {len(bones_idx_dict)}\n")
        except Exception as e:
            # raise
            tqdm.write(f"{file}: {e}")
            with open(logfile, "a") as f:
                f.write(f"{file}: {e}\n")

    # Calculate the coverage of each bone among all characters
    print(sorted(set(bones_name_list)))
    # with HiddenPrints():
    #     remove_all()
    #     rest_bones, bones_idx_dict = get_rest_bones(get_all_armature_obj(load_file(animation_list[0]))[0])
    with open(logfile, "a") as f:
        # for v in bones_idx_dict.keys():
        for v in sorted(set(bones_name_list)):
            f.write(f"{v}: {bones_name_list.count(v)}/{len(character_list)}\n")
