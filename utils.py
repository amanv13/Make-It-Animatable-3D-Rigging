import math
import os
import sys

import bpy
import numpy as np
from bpy.types import Action, Armature, Mesh, Object

# isort: split
import bmesh
import mathutils


class HiddenPrints:
    def __init__(self, enable=True, suppress_err=False):
        self.enable = enable
        self.suppress_err = suppress_err

    def __enter__(self):
        if not self.enable:
            return
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, "w")
        if self.suppress_err:
            self._original_stderr = sys.stderr
            sys.stderr = open(os.devnull, "w")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.enable:
            return
        sys.stdout.close()
        sys.stdout = self._original_stdout
        if self.suppress_err:
            sys.stderr.close()
            sys.stderr = self._original_stderr


USE_WORLD_COORDINATES = False


class Mode:
    def __init__(self, mode_name="EDIT", active_obj: Object = None):
        self.mode = mode_name
        self.active = active_obj
        self.pre_active = None
        self.pre_mode = "OBJECT"

    def __enter__(self):
        self.pre_active = bpy.context.view_layer.objects.active
        if self.pre_active is not None:
            self.pre_mode = bpy.context.object.mode
        bpy.context.view_layer.objects.active = self.active
        bpy.ops.object.mode_set(mode=self.mode)
        return self.active

    def __exit__(self, exc_type, exc_val, exc_tb):
        bpy.ops.object.mode_set(mode=self.pre_mode)
        bpy.context.view_layer.objects.active = self.pre_active


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def update():
    bpy.context.view_layer.update()
    bpy.context.scene.update_tag()
    for obj in bpy.context.scene.objects:
        # obj.hide_render = obj.hide_render
        obj.update_tag()


def remove_all(delete_actions=True):
    for obj in bpy.data.objects.values():
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.outliner.orphans_purge(do_recursive=True)
    if delete_actions:
        for action in bpy.data.actions:
            bpy.data.actions.remove(action, do_unlink=True)


def remove_empty():
    childless_empties = [e for e in bpy.data.objects if e.type.startswith("EMPTY") and not e.children]
    bpy.data.batch_remove(childless_empties)


def remove_collection(coll_name: str):
    if coll_name not in bpy.data.collections:
        return
    coll = bpy.data.collections[coll_name]
    for c in coll.children:
        remove_collection(c)
    bpy.data.collections.remove(coll, do_unlink=True)


def load_file(filepath: str, *args, **kwargs) -> "list[Object]":
    old_objs = set(bpy.context.scene.objects)
    if filepath.endswith(".glb"):
        bpy.ops.import_scene.gltf(filepath=filepath, *args, **kwargs)
    elif filepath.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=filepath, *args, **kwargs)
    elif filepath.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=filepath, *args, **kwargs)
    elif filepath.endswith(".ply"):
        bpy.ops.wm.ply_import(filepath=filepath, *args, **kwargs)
    else:
        raise RuntimeError(f"Invalid input file: {filepath}")
    imported_objs = set(bpy.context.scene.objects) - old_objs
    imported_objs = sorted(imported_objs, key=lambda x: x.name)
    print("Imported:", imported_objs)
    return imported_objs


def select_all():
    bpy.ops.object.select_all(action="SELECT")


def deselect():
    bpy.ops.object.select_all(action="DESELECT")


def select_objs(obj_list: "list[Object]" = None, deselect_first=False):
    if not obj_list:
        obj_list = bpy.context.scene.objects
    if deselect_first:
        deselect()
    for obj in obj_list:
        obj.select_set(True)


def select_mesh(obj_list: "list[Object]" = None, all=True, deselect_first=False):
    if not obj_list:
        obj_list = bpy.context.scene.objects
    if deselect_first:
        deselect()
    for obj in obj_list:
        if obj.type == "MESH":
            if all:
                obj.select_set(True)
            else:
                break


class Select:
    """
    Deselecting before and after selecting the specified objects.
    """

    def __init__(self, objs: "Object | list[Object]" = None):
        self.objs = (objs,) if isinstance(objs, Object) else objs
        self.objs: "tuple[Object]" = tuple(self.objs)

    def __enter__(self):
        select_objs(self.objs, deselect_first=True)
        return self.objs

    def __exit__(self, exc_type, exc_val, exc_tb):
        deselect()


def get_type_objs(obj_list: "list[Object]" = None, type="MESH", sort=True) -> "list[Object]":
    if not obj_list:
        obj_list = bpy.context.scene.objects
    type_obj_list = [obj for obj in obj_list if obj.type == type]
    if sort:
        type_obj_list = sorted(type_obj_list, key=lambda x: x.name)
    return type_obj_list


def get_all_mesh_obj(obj_list: "list[Object]" = None):
    return get_type_objs(obj_list, "MESH")


def get_all_armature_obj(obj_list: "list[Object]" = None):
    return get_type_objs(obj_list, "ARMATURE")


def get_armature_obj(obj_list: "list[Object]" = None) -> Object:
    if not obj_list:
        obj_list = bpy.context.scene.objects
    for obj in obj_list:
        if obj.type == "ARMATURE":
            return obj


def get_rest_bones(armature_obj: Object):
    if armature_obj is None:
        return None, None, None
    rest_bones = []
    rest_bones_tail = []
    bones_idx_dict: "dict[str, int]" = {}
    armature_data: Armature = armature_obj.data
    for i, bone in enumerate(armature_data.bones):
        pos = bone.head_local
        pos_tail = bone.tail_local
        if USE_WORLD_COORDINATES:
            pos = armature_obj.matrix_world @ pos
            pos_tail = armature_obj.matrix_world @ pos_tail
        rest_bones.append(pos)
        rest_bones_tail.append(pos_tail)
        bones_idx_dict[bone.name] = i
    rest_bones = np.stack(rest_bones, axis=0)
    rest_bones_tail = np.stack(rest_bones_tail, axis=0)
    return rest_bones, rest_bones_tail, bones_idx_dict


def transfer_weights(source_bone_name: str, target_bone_name: str, mesh_obj_list: "list[Object]"):
    if isinstance(mesh_obj_list, Object):
        mesh_obj_list = [mesh_obj_list]
    for obj in mesh_obj_list:
        source_group = obj.vertex_groups.get(source_bone_name)
        if source_group is None:
            return
        source_i = source_group.index
        target_group = obj.vertex_groups.get(target_bone_name)
        if target_group is None:
            target_group = obj.vertex_groups.new(name=target_bone_name)

        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == source_i:
                    target_group.add((v.index,), g.weight, "ADD")
        obj.vertex_groups.remove(source_group)


def remove_empty_vgroups(mesh_obj_list: "list[Object]"):
    if isinstance(mesh_obj_list, Object):
        mesh_obj_list = [mesh_obj_list]
    for obj in mesh_obj_list:
        vertex_groups = obj.vertex_groups
        groups = {r: None for r in range(len(vertex_groups))}

        for vert in obj.data.vertices:
            for vg in vert.groups:
                i = vg.group
                if i in groups:
                    del groups[i]

        lis = list(groups)
        lis.sort(reverse=True)
        for i in lis:
            vertex_groups.remove(vertex_groups[i])


def set_action(armature_obj: Object, action: Action):
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    armature_obj.animation_data.action = action
    return armature_obj


def mesh_quads2tris(obj_list: "list[Object]" = None):
    if not obj_list:
        obj_list = bpy.context.scene.objects
    for obj in obj_list:
        if obj.type == "MESH":
            with Mode("EDIT", obj):
                bpy.ops.mesh.quads_convert_to_tris(quad_method="BEAUTY", ngon_method="BEAUTY")


def get_enabled_addons() -> "list[str]":
    return [x.module for x in bpy.context.preferences.addons]


def enable_arp(armature_obj: Object, addon_path=os.path.join(os.path.dirname(__file__), "auto_rig_pro")):
    import sys

    assert os.path.isfile(os.path.join(addon_path, "__init__.py")), "Auto-Rig Pro not found"
    dirname, addon_name = os.path.split(addon_path)
    # if addon_name in get_enabled_addons():
    #     return
    sys.path.insert(0, dirname)
    with Mode("POSE", armature_obj):
        # import addon_utils
        # addon_utils.enable(addon_name)
        bpy.ops.preferences.addon_enable(module=addon_name)


def retarget(source_armature: Object, target_armature: Object, inplace=False):
    enable_arp(target_armature)
    scn = bpy.context.scene
    scn.source_rig = source_armature.name
    if inplace:
        scn.arp_retarget_in_place = True
    scn.target_rig = target_armature.name
    bpy.ops.arp.auto_scale()
    bpy.ops.arp.build_bones_list()
    hips = scn.bones_map_v2["mixamorig:Hips"]
    scn.bones_map_index = list(scn.bones_map_v2).index(hips)
    hips.set_as_root = True
    bpy.ops.arp.retarget()
    return target_armature


def load_mixamo_anim(char_file: str, anim_file: str, do_retarget=False, inplace=False, to_tris=False):
    char_objs = load_file(char_file) if isinstance(char_file, str) else char_file
    char_armature = get_armature_obj(char_objs)

    anim_objs = load_file(anim_file)
    anim_armature = get_armature_obj(anim_objs)
    print(anim_armature)
    print(anim_armature.animation_data)
    assert anim_armature.animation_data is not None and len(bpy.data.actions) > 0, f"Animation not found in {anim_file}"

    set_action(char_armature, anim_armature.animation_data.action)
    if do_retarget:
        retarget(anim_armature, char_armature, inplace=inplace)
        for action in bpy.data.actions:
            if action is not char_armature.animation_data.action:
                bpy.data.actions.remove(action, do_unlink=True)
    for obj in anim_objs:
        bpy.data.objects.remove(obj, do_unlink=True)

    if to_tris:
        mesh_quads2tris(char_objs)
    return char_objs
