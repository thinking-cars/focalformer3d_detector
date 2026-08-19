#!/bin/bash
# Installs the FocalFormer3D model dependencies (mmcv/mmdet/mmseg/mmdet3d) into the user site,
# ported to run on modern Python (3.12) / PyTorch (2.x) / CUDA (12.x) base images.
#
# Verified combination (Python 3.12.3, torch 2.5.0+cu124, CUDA 12.6, RTX 3090):
#   mmcv-full 1.7.2 (built from source, C++17), mmdet 2.28.2, mmsegmentation 0.30.0,
#   mmdet3d 1.0.0rc6 (built from source with small patches), numpy 1.26.4, scipy 1.13.1
#
# Notes:
#  - mmcv-full and mmdet3d are built from source; ~20-40 min for mmcv depending on CPU.
#  - TORCH_CUDA_ARCH_LIST must match the target GPU (8.6 = RTX 30xx / A10; 8.9 = RTX 40xx / L4).
#  - setuptools is pinned < 80: newer versions remove the legacy setup.py commands that
#    both colcon (ament_python) and the mm-package builds still rely on.
#  - ~/.local/bin must be on PATH at runtime: the FocalFormer3D plugin JIT-compiles a
#    custom CUDA op (localattention) with ninja on first import.

set -e

TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.6}"
SRC_DIR="${SRC_DIR:-$HOME/src}"
MAX_JOBS="${MAX_JOBS:-$(nproc)}"

mkdir -p "$SRC_DIR"

# setuptools < 80 required by colcon's ament_python and legacy mm-package builds
pip install --user "setuptools==75.6.0"

# pure-python model stack + support packages
# (modern numba needs an up-to-date coverage; old system versions break its import)
pip install --user "mmdet==2.28.2" "mmsegmentation==0.30.0" \
  numba trimesh plyfile scikit-image pyquaternion "yapf==0.40.1" ninja psutil
pip install --user -U coverage

# mmcv-full 1.7.2 from source with CUDA ops (patched from C++14 to C++17 for torch >= 2.1)
if ! python3 -c "import mmcv" 2> /dev/null; then
  [ -d "$SRC_DIR/mmcv-1.7.2" ] || git clone --depth 1 --branch v1.7.2 https://github.com/open-mmlab/mmcv.git "$SRC_DIR/mmcv-1.7.2"
  cd "$SRC_DIR/mmcv-1.7.2"
  sed -i 's/std=c++14/std=c++17/g' setup.py
  MMCV_WITH_OPS=1 FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST="$TORCH_CUDA_ARCH_LIST" MAX_JOBS="$MAX_JOBS" \
    pip install --no-build-isolation --user .
fi

# mmdet3d 1.0.0rc6 from source (last release with the pre-2.0 API used by FocalFormer3D)
if ! python3 -c "import mmdet3d" 2> /dev/null; then
  [ -d "$SRC_DIR/mmdet3d-1.0.0rc6" ] || git clone --depth 1 --branch v1.0.0rc6 https://github.com/open-mmlab/mmdetection3d.git "$SRC_DIR/mmdet3d-1.0.0rc6"
  cd "$SRC_DIR/mmdet3d-1.0.0rc6"
  # allow mmcv 1.7.2 (upstream caps at 1.7.0)
  sed -i "s/mmcv_maximum_version = '1.7.0'/mmcv_maximum_version = '1.7.2'/" mmdet3d/__init__.py
  # guard dataset/eval imports whose SDKs (lyft_dataset_sdk) are not installable on modern Python
  python3 - <<'EOF'
import pathlib

p = pathlib.Path("mmdet3d/datasets/__init__.py")
s = p.read_text()
if "except ImportError" not in s:
    s = s.replace(
        "from .lyft_dataset import LyftDataset\n",
        "try:\n    from .lyft_dataset import LyftDataset\nexcept ImportError:  # lyft_dataset_sdk unavailable\n    LyftDataset = None\n",
    )
    p.write_text(s)

p = pathlib.Path("mmdet3d/core/evaluation/__init__.py")
s = p.read_text()
if "except ImportError" not in s:
    s = s.replace(
        "from .lyft_eval import lyft_eval\n",
        "try:\n    from .lyft_eval import lyft_eval\nexcept ImportError:  # lyft_dataset_sdk unavailable\n    lyft_eval = None\n",
    )
    p.write_text(s)
EOF
  # install without deps: upstream pins numba==0.53.0 / lyft sdk, which do not support modern Python
  pip install --no-deps --user .
fi

# nuscenes-devkit (needed by mmdet3d dataset modules at import time);
# pin numpy/scipy to versions compatible with the mm-stack
pip install --user nuscenes-devkit "numpy==1.26.4" "scipy==1.13.1"

python3 -c "
import mmcv, mmdet, mmseg, mmdet3d, numpy, scipy
from mmcv.ops import get_compiling_cuda_version
from mmdet3d.models import build_model
print('model dependency stack OK:')
print('  mmcv', mmcv.__version__, '(CUDA ' + get_compiling_cuda_version() + ')')
print('  mmdet', mmdet.__version__, '| mmseg', mmseg.__version__, '| mmdet3d', mmdet3d.__version__)
print('  numpy', numpy.__version__, '| scipy', scipy.__version__)
"
