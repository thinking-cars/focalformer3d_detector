# Copyright Thinking Cars GmbH
# SPDX-License-Identifier: Apache-2.0

import os
from glob import glob

from setuptools import setup

package_name = "focalformer3d_detector"


def data_files_from_tree(source_dir, install_root, prune=("__pycache__", ".git")):
    """Recursively map every file under ``source_dir`` into ``install_root``, keeping structure.

    The FocalFormer3D repository and the checkpoints directory live one level up from this
    package (next to it in the repository root). They are copied into the package share
    directory so they end up in the ROS install space, which is the only thing kept in the
    ``run`` Docker image (see docker/docker-ros/docker/Dockerfile). The model needs the full
    FocalFormer3D repository layout at ``<config>/../../..`` to import its mmdet3d plugin.
    """
    entries = []
    base_parent = os.path.dirname(source_dir.rstrip("/"))
    for path, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in prune]
        rel = os.path.relpath(path, base_parent)
        sources = [os.path.join(path, f) for f in files if not f.endswith(".pyc") and f not in prune]
        if sources:
            entries.append((os.path.join(install_root, rel), sources))
    return entries


share_dir = os.path.join("share", package_name)

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        (os.path.join("share", package_name), ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*launch.[pxy][yma]*")),
        (os.path.join("share", package_name, "config"), glob("config/*")),
    ]
    # ship the FocalFormer3D repo and model checkpoint into the install space so they are
    # available in the install-only run image (referenced by config/params.yml)
    + data_files_from_tree("../FocalFormer3D", share_dir)
    + data_files_from_tree("../checkpoints", share_dir),
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Raphael van Kempen",
    maintainer_email="vankempen@thinking-cars.de",
    description="ROS 2 package integrating the official FocalFormer3D implementation by NVlabs",
    license="Apache-2.0",
    entry_points={
        "console_scripts": ["focalformer3d_detector = focalformer3d_detector.focalformer3d_detector:main"],
    },
)
