"""Use optional workspace-local CUDA wheels without changing system settings."""
from pathlib import Path
import os, ctypes

_handles=[]
def configure():
    if os.name != 'nt':
        return
    root=Path(__file__).resolve().parents[2]
    deps=root/'work/simulation_deps/nvidia'
    if not deps.exists():
        return
    cache=root/'work/gpu_cache';cache.mkdir(parents=True,exist_ok=True)
    os.environ['TMP']=str(cache);os.environ['TEMP']=str(cache)
    os.environ['CUPY_CACHE_DIR']=str(cache/'cupy')
    os.environ['CUDA_PATH']=str(deps/'cuda_runtime')
    for folder in deps.glob('*/bin'):
        _handles.append(os.add_dll_directory(str(folder)))
    for dll in (deps/'cuda_nvrtc/bin').glob('nvrtc64_*.dll'):
        if '.alt.' not in dll.name:
            _handles.append(ctypes.WinDLL(str(dll)))
