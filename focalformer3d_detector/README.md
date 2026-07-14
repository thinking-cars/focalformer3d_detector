# `focalformer3d_detector`

ROS 2 package integrating the official FocalFormer3D implementation by NVlabs

- [focalformer3d\_detector](#focalformer3d_detector)
  - [Model Dependencies](#model-dependencies)
  - [`focalformer3d_detector`](#focalformer3d_detector-1)
    - [Subscribed Topics](#subscribed-topics)
    - [Published Topics](#published-topics)
    - [Parameters](#parameters)
    - [Notes](#notes)

## Launch Files

### [`focalformer3d_detector_launch.py`](launch/focalformer3d_detector_launch.py)

| Argument | Default | Description |
| --- | --- | --- |
| `input_topic` | `"~/input"` | input point cloud |
| `output_topic` | `"~/output"` | output object list |
| `name` | `"focalformer3d_detector"` | node name |
| `namespace` | `""` | node namespace |
| `params` | `os.path.join(get_package_share_directory("focalformer3d_detector"), "config", "params.yml")` | path to parameter file |
| `log_level` | `"info"` | ROS logging level (debug, info, warn, error, fatal) |
| `use_sim_time` | `"false"` | use simulation clock |
