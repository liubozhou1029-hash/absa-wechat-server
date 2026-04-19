import platform
import sys
import subprocess

print("=" * 50)
print("操作系统信息")
print("=" * 50)
print(f"系统：{platform.system()} {platform.release()}")
print(f"详细版本：{platform.version()}")

print("\n" + "=" * 50)
print("Python 信息")
print("=" * 50)
print(f"Python 版本：{sys.version}")

print("\n" + "=" * 50)
print("CPU 信息")
print("=" * 50)
try:
    import cpuinfo
    info = cpuinfo.get_cpu_info()
    print(f"CPU：{info.get('brand_raw', '未知')}")
except ImportError:
    print("（请先 pip install py-cpuinfo）")
    import os
    if platform.system() == "Windows":
        result = subprocess.run(
            ["wmic", "cpu", "get", "name"],
            capture_output=True, text=True
        )
        print(f"CPU：{result.stdout.strip()}")

print("\n" + "=" * 50)
print("内存信息")
print("=" * 50)
try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"总内存：{mem.total / (1024**3):.1f} GB")
except ImportError:
    print("（请先 pip install psutil）")

print("\n" + "=" * 50)
print("GPU / CUDA 信息")
print("=" * 50)
try:
    import torch
    print(f"PyTorch 版本：{torch.__version__}")
    print(f"CUDA 可用：{torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA 版本：{torch.version.cuda}")
        print(f"GPU 数量：{torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            prop = torch.cuda.get_device_properties(i)
            print(f"GPU {i}：{prop.name}，显存 {prop.total_memory / (1024**3):.1f} GB")
    else:
        print("未检测到 GPU，使用 CPU 运行")
except ImportError:
    print("PyTorch 未安装")

print("\n" + "=" * 50)
print("关键依赖版本")
print("=" * 50)
packages = [
    "pyabsa",
    "transformers",
    "bertopic",
    "flask",
    "sentence-transformers",
    "scikit-learn",
    "pandas",
    "numpy",
    "openai",
]
for pkg in packages:
    try:
        import importlib.metadata as meta
        version = meta.version(pkg)
        print(f"{pkg}：{version}")
    except Exception:
        print(f"{pkg}：未安装或未找到")