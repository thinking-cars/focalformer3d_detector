# focalformer3d_detector

<p align="center">
  <a href="https://www.ros.org"><img src="https://img.shields.io/badge/ROS 2-jazzy-22314e"/></a>
  <a href="https://github.com/thinking-cars/focalformer3d_detector/releases/latest"><img src="https://img.shields.io/github/v/release/thinking-cars/focalformer3d_detector"/></a>
  <a href="https://github.com/thinking-cars/focalformer3d_detector/blob/main/LICENSE"><img src="https://img.shields.io/github/license/thinking-cars/focalformer3d_detector"/></a>
  <br>
  <a href="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/docker-ros.yml"><img src="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/docker-ros.yml/badge.svg"/></a>
  <a href="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/compose-oci.yml"><img src="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/compose-oci.yml/badge.svg"/></a>
  <a href="https://thinking-cars.github.io/focalformer3d_detector"><img src="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/docs.yml/badge.svg"/></a>
  <a href="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/consistency.yml"><img src="https://github.com/thinking-cars/focalformer3d_detector/actions/workflows/consistency.yml/badge.svg"/></a>
</p>

This repository integrates the [FocalFormer3D](https://github.com/NVlabs/FocalFormer3D) lidar detection model into [OpenADS](https://github.com/openads-project).

> [!IMPORTANT]
> This repository is a prototypical integration of `FocalFormer3D` into [OpenADS](https://github.com/openads-project) for testing and benchmarking purposes. Thus, only necessary changes were made for integration without adopting the original code to the OpenADS consistency guidelines.

The following teaser shows **detected objects** on validation data from the nuScenes Dataset provided by [autonomy_datasets](https://github.com/thinking-cars/autonomy_datasets).

![Teaser](./assets/teaser.gif)

<p align="center">
  <strong>🚀 <a href="#-quick-start">Quick Start</a></strong> • <strong>💻 <a href="#-development">Development</a></strong> • <strong>📝 <a href="#-documentation">Documentation</a></strong>
</p>


## 🚀 Quick Start

1. Start a container of the pre-built runtime image.
    ```bash
    docker run --rm -it ghcr.io/thinking-cars/focalformer3d_detector:latest bash
    ```
1. Inside the container, launch the pre-built nodes.
    ```bash
    ros2 launch focalformer3d_detector focalformer3d_detector_launch.py
    ```

## 💻 Development

### Set up Development Environment

1. Clone the repository.
    ```bash
    git clone https://github.com/thinking-cars/focalformer3d_detector.git
    ```
1. Initialize the [`.openads-dev-environment`](https://github.com/openads-project/openads-dev-environment) submodule containing development environment configuration.
    ```bash
    cd focalformer3d_detector
    git submodule update --init --recursive
    ```
1. Open the repository in [Visual Studio Code](https://code.visualstudio.com).
    ```bash
    code .
    ```
1. Install the recommended VS Code extensions.
    > *Ctrl+Shift+P / Extensions: Show Recommended Extensions / Install Workspace Recommended Extensions (Cloud Download Icon)*
1. Reopen the repository in a [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers).
    > *Ctrl+Shift+P / Dev Containers: Rebuild and Reopen in Container*

### Build

> *Ctrl+Shift+B*

```bash
colcon build
```

### Run Tests

> *Ctrl+Shift+P / Tasks: Run Test Task*

```bash
colcon build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=1
colcon test
colcon test-result --verbose
```


## 📝 Documentation

Package and node interfaces are documented in the respective package READMEs listed below. Implementation details are found in the [Source Code Documentation](https://thinking-cars.github.io/focalformer3d_detector).

| Package | Description |
| --- | --- |
| [focalformer3d_detector](focalformer3d_detector/README.md) | ROS 2 package integrating the official FocalFormer3D implementation by NVlabs |

## ⚖️ Licensing

This repository integrates code from the [NVlabs/FocalFormer3D](https://github.com/NVlabs/FocalFormer3D) repository published under [Nvidia Source Code License-NC](https://github.com/NVlabs/FocalFormer3D/blob/master/LICENSE). Our modifications are licensed under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).

## 🙏 Acknowledgements

This project is maintained by [Thinking Cars](https://www.thinking-cars.de). We acknowledge the work of the [original authors at NVlabs](https://github.com/NVlabs).
