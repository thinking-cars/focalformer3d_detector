# FocalFormer3D

<p align="center">
  <a href="https://www.ros.org"><img src="https://img.shields.io/badge/ROS 2-jazzy-22314e"/></a>
  <a href="https://github.com/thinking-cars/FocalFormer3D/releases/latest"><img src="https://img.shields.io/github/v/release/thinking-cars/FocalFormer3D"/></a>
  <a href="https://github.com/thinking-cars/FocalFormer3D/blob/main/LICENSE"><img src="https://img.shields.io/github/license/thinking-cars/FocalFormer3D"/></a>
  <br>
  <a href="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/docker-ros.yml"><img src="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/docker-ros.yml/badge.svg"/></a>
  <a href="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/compose-oci.yml"><img src="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/compose-oci.yml/badge.svg"/></a>
  <a href="https://thinking-cars.github.io/FocalFormer3D"><img src="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/docs.yml/badge.svg"/></a>
  <a href="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/consistency.yml"><img src="https://github.com/thinking-cars/FocalFormer3D/actions/workflows/consistency.yml/badge.svg"/></a>
</p>

**Demo repository for an OpenADS module**

This repository serves as a demo for an OpenADS module, showcasing the structure and documentation style for OpenADS packages. It includes a simple ROS 2 node that subscribes to a topic, processes the data, and publishes the result. This is a short description of the repository and its purpose.

> ### ⚙️ Recommended GitHub Settings
> 
> [**GitHub Organization Settings**](https://github.com/organizations/openads-project/settings):
>   - Settings → Codespaces → General → Codespaces access → ○ Enable for all members
>   - Settings → Actions → General → Approval for running fork pull request workflows from contributors → ○ Require approval for all external contributors
>   - Settings → Actions → General → Workflow permissions → ○ Read and write permissions
>   - Settings → Packages → Package creation → ☑ Public
> 
> [**GitHub Repository Settings**](https://github.com/openads-project/openads_demo_module/settings):
>   - About (Sidebar):
>     - Description: `<short_title_description_from_readme>`
>     - Website: ☑ Use your GitHub Pages website
>     - Topics: e.g. `openadservice`, `openadsuite`, `openadstack`, `openadsim`, ...
>   - Settings → General → Pull Requests → ☑ Allow auto-merge (only possible to set once public)
>   - Settings → General → Pull Requests → ☑ Automatically delete head branches
>   - Settings → Branches → Add classic branch protection rule (only takes effect once public)
>     - Branch name pattern: `main`
>     - ☑ Require a pull request before merging
>     - ☑ Require status checks to pass before merging (only possible to set once public)
>       - Status checks that are required: `docker-ros`, `compose-oci`, `consistency`
>     - ☑ Require conversation resolution before merging (only possible to set once public)
>   - Settings → Pages → Branch: `gh-pages` (only possible to set once public)
>   - If the repository was created in a private namespace and the organization settings above cannot be applied:
>     - Settings → Actions → General → Workflow permissions → ○ Read and write permissions
>   - If the repository's visibility is changed from *private* to *public*, make sure to also [change the visibility of the associated packages](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).

<p align="center">
  <strong>🚀 <a href="#-quick-start">Quick Start</a></strong> • <strong>💻 <a href="#-development">Development</a></strong> • <strong>📝 <a href="#-documentation">Documentation</a></strong>
</p>


> [!IMPORTANT]
> This repository is part of [***OpenADS***](https://github.com/openads-project), the *Open Automated Driving Systems* project. *OpenADS* and its modules have been initiated and are currently being maintained by the [**Institute for Automotive Engineering (ika) at RWTH Aachen University**](https://www.ika.rwth-aachen.de/de/).


## 🚀 Quick Start

1. Start a container of the pre-built runtime image.
    ```bash
    docker run --rm -it ghcr.io/openads-project/openads_demo_module:latest bash
    ```
1. Inside the container, launch the pre-built nodes.
    ```bash
    ros2 launch openads_demo_module openads_demo_module_launch.py
    ```

## 💻 Development

### Set up Development Environment

1. Clone the repository.
    ```bash
    git clone https://github.com/thinking-cars/FocalFormer3D.git
    ```
1. Initialize the [`.openads-dev-environment`](https://github.com/openads-project/openads-dev-environment) submodule containing development environment configuration.
    ```bash
    cd FocalFormer3D
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

Package and node interfaces are documented in the respective package READMEs listed below. Implementation details are found in the [Source Code Documentation](https://thinking-cars.github.io/FocalFormer3D).

| Package | Description |
| --- | --- |

## ⚖️ Licensing

This repository integrates code from the [NVlabs/FocalFormer3D](https://github.com/NVlabs/FocalFormer3D) repository published under [Nvidia Source Code License-NC](https://github.com/NVlabs/FocalFormer3D/blob/master/LICENSE). Our modifications are licensed under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0.txt).

## 🙏 Acknowledgements

This project is maintained by [Thinking Cars](https://www.thinking-cars.de). We acknowledge the work of the [original authors at NVlabs](https://github.com/NVlabs).
