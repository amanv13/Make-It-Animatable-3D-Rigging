import math
import os
from dataclasses import dataclass
from functools import cached_property
from glob import glob
from typing import Iterator

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from tqdm import tqdm

from utils import (
    Armature,
    HiddenPrints,
    Mode,
    bpy,
    get_all_mesh_obj,
    get_armature_obj,
    load_file,
    mathutils,
    remove_all,
    remove_collection,
    remove_empty_vgroups,
    reset,
    select_objs,
    transfer_weights,
    update,
)

MIXAMO_PREFIX = "mixamorig:"
VROID_JOINTS_MAP = {
    "J_Bip_C_Hips": f"{MIXAMO_PREFIX}Hips",
    "J_Bip_C_Spine": f"{MIXAMO_PREFIX}Spine",
    "J_Bip_C_Chest": f"{MIXAMO_PREFIX}Spine1",
    "J_Bip_C_UpperChest": f"{MIXAMO_PREFIX}Spine2",
    "J_Bip_C_Neck": f"{MIXAMO_PREFIX}Neck",
    "J_Bip_C_Head": f"{MIXAMO_PREFIX}Head",
    "J_Bip_L_Shoulder": f"{MIXAMO_PREFIX}LeftShoulder",
    "J_Bip_L_UpperArm": f"{MIXAMO_PREFIX}LeftArm",
    "J_Bip_L_LowerArm": f"{MIXAMO_PREFIX}LeftForeArm",
    "J_Bip_L_Hand": f"{MIXAMO_PREFIX}LeftHand",
    "J_Bip_L_Index1": f"{MIXAMO_PREFIX}LeftHandIndex1",
    "J_Bip_L_Index2": f"{MIXAMO_PREFIX}LeftHandIndex2",
    "J_Bip_L_Index3": f"{MIXAMO_PREFIX}LeftHandIndex3",
    "J_Bip_L_Little1": f"{MIXAMO_PREFIX}LeftHandPinky1",
    "J_Bip_L_Little2": f"{MIXAMO_PREFIX}LeftHandPinky2",
    "J_Bip_L_Little3": f"{MIXAMO_PREFIX}LeftHandPinky3",
    "J_Bip_L_Middle1": f"{MIXAMO_PREFIX}LeftHandMiddle1",
    "J_Bip_L_Middle2": f"{MIXAMO_PREFIX}LeftHandMiddle2",
    "J_Bip_L_Middle3": f"{MIXAMO_PREFIX}LeftHandMiddle3",
    "J_Bip_L_Ring1": f"{MIXAMO_PREFIX}LeftHandRing1",
    "J_Bip_L_Ring2": f"{MIXAMO_PREFIX}LeftHandRing2",
    "J_Bip_L_Ring3": f"{MIXAMO_PREFIX}LeftHandRing3",
    "J_Bip_L_Thumb1": f"{MIXAMO_PREFIX}LeftHandThumb1",
    "J_Bip_L_Thumb2": f"{MIXAMO_PREFIX}LeftHandThumb2",
    "J_Bip_L_Thumb3": f"{MIXAMO_PREFIX}LeftHandThumb3",
    "J_Bip_R_Shoulder": f"{MIXAMO_PREFIX}RightShoulder",
    "J_Bip_R_UpperArm": f"{MIXAMO_PREFIX}RightArm",
    "J_Bip_R_LowerArm": f"{MIXAMO_PREFIX}RightForeArm",
    "J_Bip_R_Hand": f"{MIXAMO_PREFIX}RightHand",
    "J_Bip_R_Index1": f"{MIXAMO_PREFIX}RightHandIndex1",
    "J_Bip_R_Index2": f"{MIXAMO_PREFIX}RightHandIndex2",
    "J_Bip_R_Index3": f"{MIXAMO_PREFIX}RightHandIndex3",
    "J_Bip_R_Little1": f"{MIXAMO_PREFIX}RightHandPinky1",
    "J_Bip_R_Little2": f"{MIXAMO_PREFIX}RightHandPinky2",
    "J_Bip_R_Little3": f"{MIXAMO_PREFIX}RightHandPinky3",
    "J_Bip_R_Middle1": f"{MIXAMO_PREFIX}RightHandMiddle1",
    "J_Bip_R_Middle2": f"{MIXAMO_PREFIX}RightHandMiddle2",
    "J_Bip_R_Middle3": f"{MIXAMO_PREFIX}RightHandMiddle3",
    "J_Bip_R_Ring1": f"{MIXAMO_PREFIX}RightHandRing1",
    "J_Bip_R_Ring2": f"{MIXAMO_PREFIX}RightHandRing2",
    "J_Bip_R_Ring3": f"{MIXAMO_PREFIX}RightHandRing3",
    "J_Bip_R_Thumb1": f"{MIXAMO_PREFIX}RightHandThumb1",
    "J_Bip_R_Thumb2": f"{MIXAMO_PREFIX}RightHandThumb2",
    "J_Bip_R_Thumb3": f"{MIXAMO_PREFIX}RightHandThumb3",
    "J_Bip_L_UpperLeg": f"{MIXAMO_PREFIX}LeftUpLeg",
    "J_Bip_L_LowerLeg": f"{MIXAMO_PREFIX}LeftLeg",
    "J_Bip_L_Foot": f"{MIXAMO_PREFIX}LeftFoot",
    "J_Bip_L_ToeBase": f"{MIXAMO_PREFIX}LeftToeBase",
    "J_Bip_R_UpperLeg": f"{MIXAMO_PREFIX}RightUpLeg",
    "J_Bip_R_LowerLeg": f"{MIXAMO_PREFIX}RightLeg",
    "J_Bip_R_Foot": f"{MIXAMO_PREFIX}RightFoot",
    "J_Bip_R_ToeBase": f"{MIXAMO_PREFIX}RightToeBase",
    #
    # "J_Opt_L_RabbitEar1_01": f"{MIXAMO_PREFIX}LRabbitEar1",
    "J_Opt_L_RabbitEar2_01": f"{MIXAMO_PREFIX}LRabbitEar2",
    # "J_Opt_R_RabbitEar1_01": f"{MIXAMO_PREFIX}RRabbitEar1",
    "J_Opt_R_RabbitEar2_01": f"{MIXAMO_PREFIX}RRabbitEar2",
    "J_Opt_C_FoxTail1_01": f"{MIXAMO_PREFIX}FoxTail1",
    "J_Opt_C_FoxTail2_01": f"{MIXAMO_PREFIX}FoxTail2",
    "J_Opt_C_FoxTail3_01": f"{MIXAMO_PREFIX}FoxTail3",
    "J_Opt_C_FoxTail4_01": f"{MIXAMO_PREFIX}FoxTail4",
    "J_Opt_C_FoxTail5_01": f"{MIXAMO_PREFIX}FoxTail5",
}
VROID_JOINTS = set(VROID_JOINTS_MAP.values())


def enable_vrm(addon_path="VRM_Addon_for_Blender-Extension-2_20_88.zip"):
    """https://github.com/saturday06/VRM-Addon-for-Blender"""
    assert os.path.isfile(addon_path), f"Addon file not found: {addon_path}"
    import shutil

    # bpy.ops.preferences.addon_install(filepath=os.path.abspath(addon_path))
    repo = "user_default"
    shutil.rmtree(bpy.utils.user_resource("EXTENSIONS", path=repo))
    bpy.ops.extensions.package_install_files(filepath=os.path.abspath(addon_path), repo=repo)
    bpy.ops.preferences.addon_enable(module=f"bl_ext.{repo}.vrm")


def load_vrm(filepath: str):
    old_objs = set(bpy.context.scene.objects)
    bpy.ops.import_scene.vrm(
        filepath=filepath,
        use_addon_preferences=True,
        extract_textures_into_folder=False,
        make_new_texture_folder=True,
        set_shading_type_to_material_on_import=False,
        set_view_transform_to_standard_on_import=True,
        set_armature_display_to_wire=False,
        set_armature_display_to_show_in_front=False,
        set_armature_bone_shape_to_default=True,
    )
    remove_collection("glTF_not_exported")
    remove_collection("Colliders")
    imported_objs = set(bpy.context.scene.objects) - old_objs
    imported_objs = sorted(imported_objs, key=lambda x: x.name)
    print("Imported:", imported_objs)
    return imported_objs


@dataclass(frozen=True)
class Joint:
    name: str
    index: int
    parent: Self | None
    children: list[Self]

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"

    def __iter__(self) -> Iterator[Self]:
        yield self
        for child in self.children:
            yield from child

    @cached_property
    def children_recursive(self) -> list[Self]:
        # return [child for child in self if child is not self]
        children_list = []
        if not self.children:
            return children_list
        for child in self.children:
            children_list.append(child)
            children_list.extend(child.children_recursive)
        return children_list

    def __len__(self):
        return len(self.children_recursive) + 1

    def __contains__(self, item: Self | str):
        if isinstance(item, str):
            return item == self.name or item in (child.name for child in self.children_recursive)
        elif isinstance(item, Joint):
            return item is Self or item in self.children_recursive
        else:
            raise TypeError(f"Item must be {self.__class__.__name__} or str, not {type(item)}")

    @cached_property
    def children_recursive_dict(self) -> dict[str, Self]:
        return {child.name: child for child in self.children_recursive}

    def __getitem__(self, index: int | str) -> Self:
        if index in (0, self.name):
            return self
        if isinstance(index, int):
            index -= 1
            return self.children_recursive[index]
        elif isinstance(index, str):
            return self.children_recursive_dict[index]
        else:
            raise TypeError(f"Index must be int or str, not {type(index)}")

    @cached_property
    def parent_recursive(self) -> list[Self]:
        parent_list = []
        if self.parent is None:
            return parent_list
        parent_list.append(self.parent)
        parent_list.extend(self.parent.parent_recursive)
        return parent_list

    def get_first_valid_parent(self, valid_names: list[str]) -> Self | None:
        return next((parent for parent in self.parent_recursive if parent.name in valid_names), None)


def build_skeleton(armature_obj, bones_idx_dict: dict[str, int] = None):
    def get_children(bone, parent=None):
        joint = Joint(
            bone.name, index=bones_idx_dict[bone.name] if bones_idx_dict else None, parent=parent, children=[]
        )
        children = [b for b in bone.children if not bones_idx_dict or b.name in bones_idx_dict]
        if not children:
            return joint
        for child in bone.children:
            joint.children.append(get_children(child, parent=joint))
        return joint

    hips_bone = armature_obj.data.bones[f"{MIXAMO_PREFIX}Hips"]
    hips = get_children(hips_bone)
    return hips


if __name__ == "__main__":
    input_dir = "./character_vroid"
    output_dir = "./character_vroid_refined"
    keep_texture = False
    os.makedirs(output_dir, exist_ok=True)

    with HiddenPrints():
        reset()
        enable_vrm()

    for vrm_path in tqdm(sorted(glob(os.path.join(input_dir, "*.vrm"))), dynamic_ncols=True):
        with HiddenPrints(suppress_err=True):
            remove_all()
            objs = load_vrm(vrm_path)
            armature_obj = get_armature_obj(objs)
            armature_data: Armature = armature_obj.data
            mesh_objs = get_all_mesh_obj(objs)

            # Correct global scaling and rotation
            armature_obj.scale = (100, 100, 100)
            armature_obj.rotation_mode = "XYZ"
            armature_obj.rotation_euler[0] = -math.pi / 2
            bpy.context.view_layer.objects.active = armature_obj
            armature_obj.select_set(state=True)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            armature_obj.scale = (0.01, 0.01, 0.01)
            armature_obj.rotation_euler[0] = math.pi / 2
            update()

            for bone in armature_data.bones:
                if bone.name in VROID_JOINTS_MAP:
                    bone.name = VROID_JOINTS_MAP[bone.name]
            with Mode("EDIT", armature_obj):
                armature_data.edit_bones.remove(armature_data.edit_bones["Root"])

            kinematic_tree = build_skeleton(armature_obj)
            for bone_name in VROID_JOINTS:
                assert bone_name in kinematic_tree, f"{bone_name} not found in {vrm_path}"
            for bone in armature_data.bones:
                if bone.name not in VROID_JOINTS:
                    valid_parent = kinematic_tree[bone.name].get_first_valid_parent(VROID_JOINTS)
                    if valid_parent is not None:
                        transfer_weights(bone.name, valid_parent.name, mesh_objs)
            # remove_empty_vgroups(mesh_objs)
            update()

            with Mode("EDIT", armature_obj):
                for bone in armature_data.edit_bones:
                    if bone.name not in VROID_JOINTS:
                        armature_data.edit_bones.remove(bone)
                # Attach parent.tail to child.head (instead of inverse by setting bone.use_connect=True)
                for parent, child in (
                    (f"{MIXAMO_PREFIX}Hips", f"{MIXAMO_PREFIX}Spine"),
                    (f"{MIXAMO_PREFIX}Spine", f"{MIXAMO_PREFIX}Spine1"),
                    (f"{MIXAMO_PREFIX}Spine1", f"{MIXAMO_PREFIX}Spine2"),
                    (f"{MIXAMO_PREFIX}LeftFoot", f"{MIXAMO_PREFIX}LeftToeBase"),
                    (f"{MIXAMO_PREFIX}RightFoot", f"{MIXAMO_PREFIX}RightToeBase"),
                ):
                    bone_parent = armature_data.edit_bones[parent]
                    bone_child = armature_data.edit_bones[child]
                    bone_roll = bone_parent.matrix.to_3x3().copy() @ mathutils.Vector((0.0, 0.0, 1.0))
                    bone_parent.tail = bone_child.head
                    bone_parent.align_roll(bone_roll)

            # Correct roll
            template = load_file(os.path.join(output_dir, "../bones.fbx"))
            template_armature = get_armature_obj(template)
            roll_dict = {}
            with Mode("EDIT", template_armature):
                for bone in template_armature.data.edit_bones:
                    roll_dict[bone.name] = bone.roll
            for obj in template:
                bpy.data.objects.remove(obj, do_unlink=True)
            with Mode("EDIT", armature_obj):
                for bone in armature_data.edit_bones:
                    if bone.name in roll_dict:
                        bone.roll = roll_dict[bone.name]

            update()
            select_objs(objs, deselect_first=True)
            # Warning: exporting to fbx will change tail locations of some bones
            # Use bpy.ops.wm.save_as_mainfile to reproduce this bug
            bpy.ops.export_scene.fbx(
                filepath=os.path.join(output_dir, os.path.basename(vrm_path).replace(".vrm", ".fbx")),
                check_existing=False,
                use_selection=True,
                use_triangles=True,
                add_leaf_bones=False,
                bake_anim=False,
                path_mode="COPY",
                embed_textures=keep_texture,
            )
            bones_path = os.path.join(output_dir, "../bones_vroid.fbx")
            if not os.path.isfile(bones_path):
                select_objs([get_armature_obj(objs)], deselect_first=True)
                bpy.ops.export_scene.fbx(
                    filepath=bones_path,
                    check_existing=False,
                    use_selection=True,
                    add_leaf_bones=False,
                    bake_anim=False,
                )
