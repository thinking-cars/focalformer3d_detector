# Implementation Details

## FocalFormer3D Integration

The [`focalformer3d_detector`](../focalformer3d_detector) package wraps the original NVlabs [FocalFormer3D](https://github.com/NVlabs/FocalFormer3D) implementation (included as submodule) in a ROS 2 node that subscribes to `sensor_msgs/PointCloud2` and publishes `perception_msgs/ObjectList`.

### Structure

- [`focalformer3d_model.py`](../focalformer3d_detector/focalformer3d_detector/focalformer3d_model.py) — framework-agnostic model wrapper. Imports the heavy dependencies (torch, mmcv, mmdet3d) lazily, registers the FocalFormer3D mmdet3d plugin, builds the detector from the original config, loads the checkpoint, and exposes `detect(points) -> DetectionResult` for numpy point clouds.
- [`focalformer3d_detector.py`](../focalformer3d_detector/focalformer3d_detector/focalformer3d_detector.py) — ROS 2 node. Converts `PointCloud2` to a `(N, 4)` numpy array (x, y, z, intensity), runs the model, and converts detections to `perception_msgs/Object` (HEXAMOTION state model).

### Model Loading

The model is built analogously to `FocalFormer3D/tools/test.py`:

1. The FocalFormer3D repository root is derived from the `config_file` path and added to `sys.path`; importing `projects.mmdet3d_plugin` registers all custom modules (`FocalFormer3D` detector, `FocalEncoder`, `FocalDecoder`, `TransFusionBBoxCoder`, ...).
2. `mmcv.Config.fromfile` + `mmdet3d.models.build_model` (with `train_cfg=None`) construct the network, `mmcv.runner.load_checkpoint` loads the weights.
3. Inference calls `model.simple_test(points=[tensor], img_metas=[{"box_type_3d": LiDARInstance3DBoxes}])` — the LiDAR-only config (`input_img=False`) needs no image metadata beyond the box type.

### Preprocessing

The model expects 5 features per point: `(x, y, z, intensity, dt)`, where `dt` is the time lag of aggregated sweeps. The node reads `x, y, z, intensity` from the incoming cloud (NaNs skipped, intensity zero-filled if the field is missing, scaled by `intensity_scale`); the wrapper zero-pads the remaining `dt` column (single-sweep input).

### Output Conversion

The model outputs `LiDARInstance3DBoxes` in the **pre-1.0 mmdetection3d box convention**: tensor rows `(x, y, z_bottom, w, l, h, yaw_mmdet, vx, vy)`. The wrapper converts to conventional sensor-frame values (cf. `output_to_nusc_box` in mmdet3d 0.17.x):

- position: `gravity_center` (geometric box center) — matches the default `GEOMETRIC_CENTER` reference point of `perception_msgs`
- heading: `yaw = normalize(-yaw_mmdet - π/2)`
- dimensions: `length = l`, `width = w`, `height = h`
- velocity: `(vx, vy)` are sensor-frame velocities; the node projects them into the object frame (`vel_lon`, `vel_lat`) as required by the HEXAMOTION state model

Class scores are used both as `existence_probability` and as classification probability; nuScenes classes are mapped to `ObjectClassification` types (see package README).

### Runtime Requirements

The original implementation targets Python 3.8 / PyTorch 1.9.1 / mmcv-full 1.3.18 / mmdet 2.14.0 / mmdet3d 0.17.1, which is not installable on modern base images. The integration has therefore been ported to and verified with **Python 3.12 / torch 2.5 / CUDA 12.6** using mmcv-full 1.7.2 (source build, C++17), mmdet 2.28.2, mmsegmentation 0.30.0, and mmdet3d 1.0.0rc6 (source build) — installed by [docker/install-model-dependencies.sh](../docker/install-model-dependencies.sh). mmdet3d 1.0.0rc6 is the last release retaining the legacy 0.17-style API the FocalFormer3D plugin was written against; its post-refactor box classes only pass raw tensors through the plugin's own decoding, so the checkpoint's 0.17-era conventions (handled in the model wrapper, see above) are unaffected. This was verified empirically: checkpoint loads with 0 missing/unexpected/mismatched keys, and synthetic box clusters are recovered at the correct positions, dimensions, and headings (~150 ms per frame on an RTX 3090).

Required patches to the `FocalFormer3D/` submodule (in the working tree): `mmdet3d.ops.iou3d.iou3d_utils` imports (`nms_gpu` etc.) were replaced by their `mmcv.ops` successors (`nms_bev` etc.), which also renamed the `pre_maxsize` argument to `pre_max_size`. The plugin additionally JIT-compiles a custom `localattention` CUDA extension on first model load (requires `ninja` on `PATH`; the built `.so` is cached in the plugin tree).

The node fails fast with a clear error if the dependencies or a CUDA device are missing. All ROS-side logic (message parsing, object conversion) is independent of the model stack.

**Note on setuptools**: images shipping setuptools ≥ 80 break `colcon build` for `ament_python` packages (the install step silently produces an empty package) as well as the mm-package source builds; the install script pins setuptools 75.6.0 in the user site.
