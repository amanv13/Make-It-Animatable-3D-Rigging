import os

import numpy as np
import torch
import torch.nn.functional as F
import trimesh
from pytorch3d.transforms import Transform3d
from torch.utils.data import DataLoader
from tqdm import tqdm

import util.blender_utils as blender_utils
from app import bw_post_process, vis_joints, vis_weights
from model import PCAE
from util.blender_utils import bpy as bpy
from util.dataset_mixamo import MIXAMO_PREFIX, PoseData, collate, seed_worker
from util.utils import (
    HiddenPrints,
    apply_transform,
    fix_random,
    get_normalize_transform,
    pose_local_to_global,
    pose_rot_to_global,
    to_pose_local,
    to_pose_matrix,
)

USE_ADDITIONAL_BONES = False
if USE_ADDITIONAL_BONES:
    from util.dataset_mixamo_additional import BONES_IDX_DICT, JOINTS_NUM, KINEMATIC_TREE, MixamoDataset
else:
    from util.dataset_mixamo import BONES_IDX_DICT, JOINTS_NUM, KINEMATIC_TREE, MixamoDataset

if __name__ == "__main__":
    fix_random()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data_dir = "./data"
    vis_bone = f"{MIXAMO_PREFIX}LeftArm"
    print(vis_bone)
    vis_bone_index = BONES_IDX_DICT[vis_bone]
    vis_batch = 1

    N = 32768
    hands_resample_ratio = 0.5
    geo_resample_ratio = 0.0
    hierarchical_ratio = hands_resample_ratio + geo_resample_ratio
    model = PCAE(
        N=N, input_normal=False, input_attention=False, deterministic=True, hierarchical_ratio=hierarchical_ratio
    )
    model.load("output/best/bw.pth").to(device).eval()

    model_joints = PCAE(
        N=N,
        deterministic=True,
        hierarchical_ratio=hierarchical_ratio,
        output_dim=JOINTS_NUM,
        kinematic_tree=KINEMATIC_TREE,
        predict_bw=False,
        predict_joints=True,
        predict_joints_tail=True,
    )
    model_joints.load("output/best/joints.pth").to(device).eval()

    model_pose = PCAE(
        N=N,
        deterministic=True,
        hierarchical_ratio=hierarchical_ratio,
        output_dim=JOINTS_NUM,
        kinematic_tree=KINEMATIC_TREE,
        predict_bw=False,
        predict_pose_trans=True,
        pose_mode="dual_quat",
        pose_input_joints=True,
        pose_attn=True,
    )
    model_pose.load("output/best/pose.pth").to(device).eval()

    dataset = MixamoDataset(
        "data/Mixamo",
        # extra_character_dir="data/Mixamo/character_rabit_refined",
        same_animation_first=False,
        sample_frames=[0, 10, 20, 30],
        sample_points=N,
        sample_vertices=-1,
        hands_resample_ratio=hands_resample_ratio,
        geo_resample_ratio=geo_resample_ratio,
        include_rest=True,
        get_normals=True,
        split="test",
    )
    dataloader = DataLoader(
        dataset,
        batch_size=1,
        collate_fn=collate,
        shuffle=False,
        num_workers=0,
        pin_memory=True,
        worker_init_fn=seed_worker,
    )

    for data in tqdm(dataloader, dynamic_ncols=True):
        data: PoseData
        meta = data.meta
        pts = data.pts
        verts = data.verts

        rotate = Transform3d(matrix=data.hips_transform.transpose(-1, -2))
        pts = rotate.transform_points(pts)
        norm = get_normalize_transform(pts, keep_ratio=True, recenter=False)
        global_transform = rotate.compose(norm)
        global_transform_rest = Transform3d(matrix=data.hips_transform_rest.transpose(-1, -2)).compose(norm)
        pts = norm.transform_points(pts)
        verts = global_transform.transform_points(verts)
        joints_gt = global_transform.transform_points(data.joints)
        # trimesh.Trimesh(vertices=pts[-1]).export(os.path.join(data_dir, "pts.ply"))
        # trimesh.Trimesh(vertices=verts[-1]).export(os.path.join(data_dir, "verts.ply"))
        if model.input_normal:
            pts_normal = F.normalize(global_transform.transform_normals(data.pts_normal), dim=-1)
            pts = torch.cat([pts, pts_normal], dim=-1)
            verts_normal = F.normalize(global_transform.transform_normals(data.verts_normal), dim=-1)
            verts = torch.cat([verts, verts_normal], dim=-1)

        pts = pts.to(device, non_blocking=True)
        verts = verts.to(device, non_blocking=True)

        with torch.no_grad():
            # model.to_mesh(pts)[-1].export(os.path.join(data_dir, "test.ply"))
            bw = model.forward(pts, verts).bw
            pts, verts = pts[..., :3], verts[..., :3]
            joints = model_joints.forward(pts).joints
            joints_ = joints.clone() if model_pose.pose_input_joints else None
            pose = model_pose.forward(pts, joints=joints_).pose_trans

        bw = bw.cpu()
        pts = pts.cpu()
        verts = verts.cpu()
        joints = joints.cpu()
        pose = pose.cpu()

        meta = meta[vis_batch]
        bw_gt = torch.nan_to_num(data.weights, nan=0.0)
        bw = bw_post_process(bw, bones_idx_dict=BONES_IDX_DICT)

        output_dir = os.path.join(data_dir, f"pred_{meta.index:02}")
        os.makedirs(output_dir, exist_ok=True)

        vis_joints(verts[vis_batch], joints[vis_batch][:, :3], meta.faces, bones_idx_dict=BONES_IDX_DICT).export(
            os.path.join(output_dir, f"{meta.frames:03}_joints.obj")
        )
        vis_joints(verts[vis_batch], joints_gt[vis_batch], meta.faces, bones_idx_dict=BONES_IDX_DICT).export(
            os.path.join(output_dir, f"{meta.frames:03}_joints_gt.obj")
        )
        vis_weights(verts[vis_batch], bw[vis_batch], meta.faces, vis_bone_index).export(
            os.path.join(output_dir, f"{meta.frames:03}_bw.obj")
        )
        vis_weights(verts[vis_batch], bw_gt[vis_batch], meta.faces, vis_bone_index).export(
            os.path.join(output_dir, f"{meta.frames:03}_bw_gt.obj")
        )
        vis_weights(
            apply_transform(meta.rest.verts, torch.einsum("kij,nk->nij", data.joints_transform[vis_batch], bw[0])),
            bw[vis_batch],
            meta.faces,
            vis_bone_index,
        ).export(os.path.join(output_dir, f"{meta.frames:03}_lbs.obj"))

        # # LBS manually
        # if "local" not in model_pose.pose_mode:
        #     # pose = data.joints_transform_inv
        #     # pose = torch.einsum("bij,bnjk->bnik", global_transform_rest[vis_batch].get_matrix().transpose(-1, -2), pose)
        #     # pose = torch.einsum("bnij,bjk->bnik", pose, global_transform[vis_batch].inverse().get_matrix().transpose(-1, -2))
        #     # pose = decompose_transform(pose)[..., :-3]
        #     # transl, rotation = pose.split([3, 4], dim=-1)
        #     # pose = quat_trans_to_dualquat(quat=rotation, transl=transl, transl_first=True)
        #     pose = dualquat_to_quat_trans(pose, concat=True, transl_first=True)
        #     pose = torch.cat([pose, torch.ones_like(pose[..., :3])], dim=-1)
        #     pose = compose_transform(pose)
        #     rest_joints = apply_transform(joints[..., :3], pose)[vis_batch]
        #     vis_joint(
        #         global_transform_rest[vis_batch].transform_points(torch.from_numpy(meta.rest.verts)),
        #         rest_joints,
        #         meta.faces,
        #         vis_bone_index=None,
        #     ).export(os.path.join(output_dir, f"{meta.frames:03}_restjoints.obj"))
        #     vis_weights(
        #         apply_transform(verts, torch.einsum("bkij,bnk->bnij", pose, bw))[vis_batch],
        #         bw[vis_batch],
        #         meta.faces,
        #         vis_bone_index,
        #     ).export(os.path.join(output_dir, f"{meta.frames:03}_restverts.obj"))

        assert dataset.include_rest
        with HiddenPrints():
            blender_utils.reset()
            blender_utils.load_mixamo_anim(meta.char_path, meta.anim_path)
            bpy.ops.export_scene.fbx(
                filepath=os.path.join(output_dir, "gt.fbx"),
                check_existing=False,
                use_selection=False,
                add_leaf_bones=False,
            )
            # rest_joints, rest_joints_tail = meta.rest.joints, meta.rest.joints_tail
            rest_joints, rest_joints_tail = joints[0, :, :3], joints[0, :, 3:]
            rest_joints = global_transform[0].inverse().transform_points(rest_joints).numpy()
            if rest_joints_tail.shape[-1] == 3:
                rest_joints_tail = global_transform[0].inverse().transform_points(rest_joints_tail).numpy()
            else:
                rest_joints_tail = None
            blender_utils.set_rest_bones(
                blender_utils.get_armature_obj(), rest_joints, rest_joints_tail, BONES_IDX_DICT
            )
            blender_utils.set_weights(blender_utils.get_all_mesh_obj(), bw[0].numpy(), BONES_IDX_DICT)
            bpy.ops.export_scene.fbx(
                filepath=os.path.join(output_dir, "lbs.fbx"),
                check_existing=False,
                use_selection=False,
                add_leaf_bones=False,
                # path_mode="COPY",
                # embed_textures=True,
            )  # export/import will automatically remove all-zero-weighted vertex groups

            # Transform to rest pose
            joints_vis, joints_tail_vis = joints[vis_batch, :, :3], joints[vis_batch, :, 3:]
            joints_vis = global_transform[vis_batch].inverse().transform_points(joints_vis).numpy()
            if joints_tail_vis.shape[-1] == 3:
                joints_tail_vis = global_transform[vis_batch].inverse().transform_points(joints_tail_vis).numpy()
            else:
                joints_tail_vis = None
            blender_utils.reset()
            blender_utils.load_mixamo_anim(meta.char_path, meta.anim_path)
            bpy.context.scene.frame_set(meta.frames)
            blender_utils.update()
            blender_utils.set_rest_bones(
                blender_utils.get_armature_obj(), joints_vis, joints_tail_vis, BONES_IDX_DICT, reset_as_rest=True
            )
            blender_utils.set_weights(blender_utils.get_all_mesh_obj(), bw[0].numpy(), BONES_IDX_DICT)
            if "local" in model_pose.pose_mode:
                pose = to_pose_local(pose, input_mode=model_pose.pose_mode, return_quat=False)
                # pose, _ = pose_local_to_global(
                #     pose, joints[..., :3], torch.tensor(KINEMATIC_TREE.parent_indices), relative_to_source=True
                # )
                raise NotImplementedError
            elif model_pose.pose_mode in ("quat", "ortho6d"):
                pose, _ = pose_rot_to_global(pose, joints[..., :3], torch.tensor(KINEMATIC_TREE.parent_indices))
            else:
                pose = to_pose_matrix(pose, input_mode=model_pose.pose_mode, source=joints[..., :3])
            pose = torch.einsum("bij,bnjk->bnik", global_transform_rest.inverse().get_matrix().transpose(-1, -2), pose)
            pose = torch.einsum("bnij,bjk->bnik", pose, global_transform.get_matrix().transpose(-1, -2))
            pose[..., 0, :, :] = torch.eye(4)
            # pose = data.joints_transform_inv
            pose_inv = pose[vis_batch].numpy()
            blender_utils.set_bone_pose(
                blender_utils.get_armature_obj(), pose_inv, BONES_IDX_DICT, local="local" in model_pose.pose_mode
            )
            bpy.ops.export_scene.fbx(
                filepath=os.path.join(output_dir, f"{meta.frames:03}_rest.fbx"),
                check_existing=False,
                use_selection=False,
                add_leaf_bones=False,
                bake_anim=False,
            )

        tqdm.write(output_dir)
