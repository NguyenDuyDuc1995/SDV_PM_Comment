import subprocess
import re

__all__ = ['get_gpu_usage']


def get_gpu_usage(gpu_id=None):
    p = subprocess.check_output('nvidia-smi')
    rams_using = [int(_[:-5]) for _ in re.findall(r'\b\d+MiB+ /', str(p))]
    rams_total = [int(_[1:-3].lstrip()) for _ in re.findall(r'/ +\b\d+MiB', str(p))]
    if gpu_id is not None:
        return rams_using[gpu_id], rams_total[gpu_id]
    return {
        gpu_id: (rams_using[gpu_id], rams_total[gpu_id])
        for gpu_id in range(len(rams_using))
    }
