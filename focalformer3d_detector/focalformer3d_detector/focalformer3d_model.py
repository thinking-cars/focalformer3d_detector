# Copyright Thinking Cars GmbH
# SPDX-License-Identifier: LicenseRef-NvidiaSourceCodeLicense-NC

"""Wrapper around the original NVlabs FocalFormer3D implementation (mmdetection3d 0.17.x based).

This module isolates all model-related code and heavy dependencies (torch, mmcv, mmdet3d, ...)
from the ROS node. The dependencies are only imported when a `FocalFormer3DModel` is
instantiated, s.t. the ROS node module stays importable without them.
"""

import importlib
import math
import os
import sys
from dataclasses import dataclass, field


@dataclass
class Detection:
    """A single 3D object detection in the coordinate frame of the input point cloud."""

    position: tuple[float, float, float]  # geometric box center (x, y, z) [m]
    dimensions: tuple[float, float, float]  # (length, width, height) [m]
    yaw: float  # heading around +z, measured from +x [rad], in (-pi, pi]
    velocity: tuple[float, float] = (0.0, 0.0)  # (vx, vy) [m/s]
    score: float = 0.0  # detection confidence [0, 1]
    label: int = -1  # class index of the model
    class_name: str = "unknown"  # class name of the model, e.g. "car"


@dataclass
class DetectionResult:
    """Result of a single inference run."""

    detections: list[Detection] = field(default_factory=list)


class FocalFormer3DModel:
    """Loads the original FocalFormer3D model and runs single-frame LiDAR inference."""

    def __init__(self, config_file: str, checkpoint_file: str, device: str = "cuda:0"):
        """Builds the FocalFormer3D model from the original config and loads the checkpoint weights.

        Args:
            config_file (str): path to an mmdet3d config of the FocalFormer3D repository,
                e.g. `<repo>/projects/configs/focalformer3d/FocalFormer3D_L.py`
            checkpoint_file (str): path to a matching checkpoint (.pth)
            device (str, optional): CUDA device to run inference on, e.g. "cuda:0"
        """

        if not os.path.isfile(config_file):
            raise FileNotFoundError(f"Model config file not found: '{config_file}'")
        if not os.path.isfile(checkpoint_file):
            raise FileNotFoundError(f"Model checkpoint file not found: '{checkpoint_file}'")

        # import heavy dependencies lazily to keep this module importable without them
        try:
            import torch
            from mmcv import Config
            from mmcv.runner import load_checkpoint
            from mmdet3d.core.bbox import LiDARInstance3DBoxes
            from mmdet3d.models import build_model
        except ImportError as e:
            raise ImportError(
                "Failed to import the FocalFormer3D model dependencies (torch, mmcv, mmdet, mmdet3d). "
                "See the focalformer3d_detector README for installation instructions."
            ) from e

        if not device.startswith("cuda"):
            raise ValueError(
                "FocalFormer3D requires a CUDA device for inference " "(sparse convolutions and voxelization are CUDA-only)"
            )
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available, but is required to run FocalFormer3D")

        self._torch = torch
        self._box_type = LiDARInstance3DBoxes
        self.device = torch.device(device)

        # make the FocalFormer3D repository and its mmdet3d plugin importable;
        # the config file lives at <repo>/projects/configs/focalformer3d/<config>.py
        repo_root = os.path.abspath(os.path.join(os.path.dirname(config_file), "..", "..", ".."))
        if not os.path.isdir(os.path.join(repo_root, "projects", "mmdet3d_plugin")):
            raise FileNotFoundError(
                f"Could not locate the FocalFormer3D plugin at '{repo_root}/projects/mmdet3d_plugin'; "
                "make sure 'config_file' points into the original repository structure "
                "(<repo>/projects/configs/focalformer3d/<config>.py)"
            )
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        # the plugin JIT-compiles custom CUDA ops (bev_pool, localattention) on import,
        # which needs the pip-installed ninja from the user site on PATH
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin) and user_bin not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = user_bin + os.pathsep + os.environ.get("PATH", "")
        # registers all custom FocalFormer3D modules (detector, neck, head, bbox coder, ...)
        importlib.import_module("projects.mmdet3d_plugin")

        # build model and load checkpoint (analogous to FocalFormer3D/tools/test.py)
        cfg = Config.fromfile(config_file)
        cfg.model.train_cfg = None
        model = build_model(cfg.model, test_cfg=cfg.get("test_cfg"))
        checkpoint = load_checkpoint(model, checkpoint_file, map_location="cpu")
        self.class_names = list(checkpoint.get("meta", {}).get("CLASSES", cfg.class_names))
        model.to(self.device)
        model.eval()
        self.model = model

        # number of point features expected by the voxel encoder (x, y, z, intensity, dt)
        self.num_point_features = cfg.model.pts_voxel_encoder.get("num_features", 5)

    def detect(self, points, score_threshold: float = 0.1) -> DetectionResult:
        """Runs inference on a single LiDAR point cloud.

        Args:
            points (np.ndarray): point cloud of shape (N, >=3) with columns (x, y, z[, intensity]);
                missing feature columns are zero-padded (e.g. the time-lag feature of multi-sweep
                configs is 0 for a single sweep)
            score_threshold (float, optional): minimum detection confidence

        Returns:
            DetectionResult: detected objects in the coordinate frame of the input point cloud
        """

        torch = self._torch

        pts = torch.as_tensor(points, dtype=torch.float32)
        if pts.ndim != 2 or pts.shape[1] < 3:
            raise ValueError(f"Expected point cloud of shape (N, >=3), got {tuple(pts.shape)}")

        # pad/cut point features to the size expected by the model
        if pts.shape[1] < self.num_point_features:
            padding = torch.zeros((pts.shape[0], self.num_point_features - pts.shape[1]), dtype=torch.float32)
            pts = torch.cat([pts, padding], dim=1)
        elif pts.shape[1] > self.num_point_features:
            pts = pts[:, : self.num_point_features]
        pts = pts.to(self.device)

        # minimal image meta information required by the LiDAR-only pipeline
        img_metas = [{"box_type_3d": self._box_type}]

        with torch.no_grad():
            results = self.model.simple_test(points=[pts], img_metas=img_metas)
        pts_bbox = results[0]["pts_bbox"]

        boxes_3d = pts_bbox["boxes_3d"]  # LiDARInstance3DBoxes, tensor (M, 9)
        scores = pts_bbox["scores_3d"].cpu().numpy()
        labels = pts_bbox["labels_3d"].cpu().numpy()
        centers = boxes_3d.gravity_center.cpu().numpy()  # (M, 3), geometric box center
        dims = boxes_3d.dims.cpu().numpy()  # (M, 3), (w, l, h) in mmdet3d < 1.0 convention
        yaws = boxes_3d.yaw.cpu().numpy()  # (M,), mmdet3d < 1.0 box yaw convention
        if boxes_3d.tensor.shape[1] >= 9:
            velocities = boxes_3d.tensor[:, 7:9].cpu().numpy()  # (M, 2), (vx, vy) in sensor frame
        else:
            velocities = [(0.0, 0.0)] * len(scores)

        result = DetectionResult()
        for center, dim, yaw, vel, score, label in zip(centers, dims, yaws, velocities, scores, labels):
            if score < score_threshold:
                continue
            # convert mmdet3d < 1.0 box yaw convention to heading in the sensor frame
            # (cf. mmdet3d 0.17.x `output_to_nusc_box`: yaw = -yaw_mmdet - pi / 2)
            heading = normalize_angle(-float(yaw) - math.pi / 2.0)
            result.detections.append(
                Detection(
                    position=(float(center[0]), float(center[1]), float(center[2])),
                    dimensions=(float(dim[1]), float(dim[0]), float(dim[2])),  # (l, w, h)
                    yaw=heading,
                    velocity=(float(vel[0]), float(vel[1])),
                    score=float(score),
                    label=int(label),
                    class_name=self.class_names[int(label)] if 0 <= int(label) < len(self.class_names) else "unknown",
                )
            )

        return result


def normalize_angle(angle: float) -> float:
    """Normalizes an angle to (-pi, pi].

    Args:
        angle (float): angle [rad]

    Returns:
        float: normalized angle [rad]
    """

    angle = math.fmod(angle + math.pi, 2.0 * math.pi)
    if angle <= 0.0:
        angle += 2.0 * math.pi
    return angle - math.pi
