import argparse
import os

from utils import HiddenPrints, bpy, load_mixamo_anim, remove_all, reset, select_objs, update

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--char_path", type=str, required=True)
    parser.add_argument("--anim_path", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()

    get_base_name = lambda s: os.path.splitext(os.path.basename(s))[0]
    output_filename = f"{get_base_name(args.char_path)}-{get_base_name(args.anim_path)}"
    with HiddenPrints():
        # remove_all()
        reset()
        objs = load_mixamo_anim(args.char_path, args.anim_path, do_retarget=True, inplace=False)
        update()
        # bpy.ops.wm.save_as_mainfile(filepath=os.path.join(args.output_dir, f"{output_filename}.blend"))
        select_objs(objs, deselect_first=True)
        bpy.ops.export_scene.fbx(
            filepath=os.path.join(args.output_dir, f"{output_filename}.fbx"),
            check_existing=False,
            use_selection=True,
            use_triangles=True,
            add_leaf_bones=False,
            bake_anim=True,
            # path_mode="COPY",
            # embed_textures=True,
        )
