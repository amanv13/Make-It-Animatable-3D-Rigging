import os
from glob import glob

import bpy
from tqdm import tqdm

from utils import HiddenPrints, get_all_armature_obj, get_all_mesh_obj, load_file, remove_all, select_objs, update


def rename_mixamo_bone(armature_obj):
    """Replace name like 'mixamorig10:xxx' to 'mixamorig:xxx, so that character can be correctly animated.'"""
    import re

    pattern = re.compile(r"mixamorig[0-9]+:")
    for bone in armature_obj.data.bones:
        bone.name = re.sub(pattern, "mixamorig:", bone.name)
    return armature_obj


if __name__ == "__main__":
    input_dir = "character_rabit"
    output_dir = "character_rabit_refined"
    os.makedirs(output_dir, exist_ok=True)
    character_list = sorted(glob(os.path.join(input_dir, "*.fbx")))

    for file in tqdm(character_list, dynamic_ncols=True):
        with HiddenPrints():
            remove_all()
            obj_list = load_file(file)
            assert len(get_all_armature_obj(obj_list)) == 1, "Armature number is not 1"
            bpy.ops.wm.save_as_mainfile(filepath="test.blend")

            select_objs(get_all_mesh_obj(obj_list), deselect_first=True)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            update()
            select_objs(obj_list, deselect_first=True)
            bpy.ops.export_scene.fbx(
                filepath=os.path.join(output_dir, os.path.basename(file)),
                check_existing=False,
                use_selection=True,
                use_triangles=True,  # !
                add_leaf_bones=False,
                bake_anim=False,
                # path_mode="COPY",
                # embed_textures=True,
            )
