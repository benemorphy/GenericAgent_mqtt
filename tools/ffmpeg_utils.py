"""
FFmpeg 工具集 — 封装常用音视频操作

本机 ffmpeg 版本: 2026-04-01-git (www.gyan.dev)
编译特性: 100个启用 (CUDA/NVENC/NVDEC/D3D11VA/Vulkan/OpenCL/AMF)
GPU: NVIDIA (Driver 555.99, CUDA 12.5)

用法:
    from tools.ffmpeg_utils import screen_capture, probe_media, convert_format
"""

import subprocess, json, os, logging
from pathlib import Path

log = logging.getLogger("ffmpeg_utils")

FFMPEG = r"D:\Program Files\ffmpeg-2026-04-01-git-eedf8f0165-full_build\bin\ffmpeg.EXE"
FFPROBE = r"D:\Program Files\ffmpeg-2026-04-01-git-eedf8f0165-full_build\bin\ffprobe.EXE"


def _run(cmd, timeout=60):
    """执行 ffmpeg 命令"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            log.warning(f"ffmpeg 返回 {r.returncode}: {r.stderr[:200]}")
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        log.error(f"ffmpeg 超时 ({timeout}s)")
        return -1, "", "timeout"
    except FileNotFoundError:
        log.error(f"ffmpeg 未找到: {FFMPEG}")
        return -1, "", "not_found"


def probe_media(path):
    """探测媒体文件信息"""
    cmd = [FFPROBE, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    rc, out, err = _run(cmd, timeout=10)
    if rc == 0 and out:
        return json.loads(out)
    return None


def screen_capture(output="screenshot.png", region=None, display=None):
    """屏幕截图 (Windows DirectX)"""
    cmd = [FFMPEG, "-f", "gdigrab", "-framerate", "1"]
    if region:
        cmd += ["-offset_x", str(region[0]), "-offset_y", str(region[1]),
                "-video_size", f"{region[2]}x{region[3]}"]
    if display:
        cmd += ["-i", f"desktop"]
    else:
        cmd += ["-i", "desktop"]
    cmd += ["-vframes", "1", "-y", output]
    rc, _, err = _run(cmd, timeout=15)
    return rc == 0, output, err


def convert_format(input_path, output_path, extra_args=None):
    """格式转换"""
    cmd = [FFMPEG, "-i", str(input_path), "-y"]
    if extra_args:
        cmd += extra_args
    cmd.append(str(output_path))
    rc, _, err = _run(cmd)
    return rc == 0, output_path, err


def extract_audio(input_path, output_path="audio.mp3", codec="libmp3lame"):
    """提取音频"""
    cmd = [FFMPEG, "-i", str(input_path), "-vn", "-acodec", codec, "-y", str(output_path)]
    rc, _, err = _run(cmd)
    return rc == 0, output_path, err


def compress_video(input_path, output_path, crf=23, preset="medium"):
    """视频压缩 (H.264)"""
    cmd = [FFMPEG, "-i", str(input_path), "-c:v", "libx264", "-preset", preset,
           "-crf", str(crf), "-c:a", "aac", "-y", str(output_path)]
    rc, _, err = _run(cmd)
    return rc == 0, output_path, err


def hardware_encode(input_path, output_path, encoder="h264_nvenc"):
    """硬件编码 (需 GPU)"""
    cmd = [FFMPEG, "-i", str(input_path), "-c:v", encoder, "-preset", "p4",
           "-cq", "23", "-c:a", "aac", "-y", str(output_path)]
    rc, _, err = _run(cmd)
    return rc == 0, output_path, err


def gpu_info():
    """查询可用的 GPU 编码器"""
    rc, out, _ = _run([FFMPEG, "-encoders"], timeout=10)
    if rc != 0:
        return []
    hw = []
    for line in out.split('\n'):
        if any(x in line for x in ['nvenc', 'nvenc', 'qsv', 'amf', 'cuda', 'dxva']):
            parts = line.strip().split()
            if parts:
                hw.append(parts[0])
    return hw


if __name__ == "__main__":
    print("=== FFmpeg 工具集测试 ===")
    print(f"ffmpeg: {FFMPEG}")
    print(f"ffprobe: {FFPROBE}")
    print(f"可用硬件编码器: {gpu_info()}")
    print("✅ ffmpeg_utils 就绪")
