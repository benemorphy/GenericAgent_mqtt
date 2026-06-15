# 环境准备清单: Supervision + FPGA 桥接开发

> 基于本机 (Windows 10, i7-8700K?, 16GB, RTX 4060 Ti) 的实际环境探测
> 2026-06-10 | 对应 supervision-fpga-bridge-plan.md 各阶段

---

## 一、当前环境快照 (已探测)

| 项目 | 状态 | 明细 |
|------|------|------|
| 操作系统 | ✅ | Windows 10 Pro, 64-bit |
| CPU | ✅ | Intel Coffee Lake, 6C12T |
| 内存 | ✅ | 16GB DDR4 2666 (Kingston) |
| GPU | ✅ | NVIDIA RTX 4060 Ti, CUDA 12.6, Driver 560.70 |
| 系统盘 (C:) | ⚠️ | 118GB total, 12GB free (空间紧张) |
| 数据盘 (D:) | ✅ | 499GB total, 70GB free (主力工作盘) |
| Python | ✅ | 3.11.12 (uv 管理) |
| PyTorch | ✅ | 2.11.0 (但有循环导入问题, 需修复) |
| ONNX Runtime | ✅ | 1.26.0 |
| OpenCV | ✅ | 4.13.0.92 |
| NumPy | ✅ | 2.4.6 |
| supervision | ❌ | 未安装 |
| ultralytics | ❌ | 未安装 |
| Vivado (Xilinx) | ❌ | 未安装 |
| Lattice Diamond | ❌ | 未安装 |
| Vitis | ❌ | 未安装 |
| OpenOCD | ❌ | 未安装 |
| make / cmake | ❌ | 未安装 |
| Git | ✅ | 已安装 |

---

## 二、分阶段环境准备

### Phase 0: 纯软件基线 (Python)

**目标**: 跑通 Supervision + YOLO 管线, 建立性能基线

#### Step 0.1 — 修复 PyTorch 循环导入

当前 `torch` 在虚拟环境中报 circular import:

```
ImportError: cannot import name 'amp' from partially initialized module 'torch'
```

**可能原因**: uv 管理的 venv 中 torch 安装不完整, 或与 numpy 2.x 不兼容。

```bash
# 方案 A: 重装 torch (推荐)
uv pip uninstall torch
uv pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121

# 方案 B: 如果重装后仍不行, 降级 numpy (numpy 2.x 已知与旧版 torch 有兼容问题)
uv pip install "numpy<2.0"
```

#### Step 0.2 — 安装 supervision + ultralytics

```bash
# 安装 supervision (最新稳定版)
uv pip install supervision

# 安装 ultralytics (提供 YOLO 模型)
uv pip install ultralytics

# 验证安装
python -c "
import supervision as sv
print('supervision:', sv.__version__)
from ultralytics import YOLO
print('ultralytics: OK')
"
```

#### Step 0.3 — 下载 YOLO 模型

```bash
# 下载 YOLOv11n (最轻量, 适合 FPGA 参考)
python -c "
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
model.export(format='onnx', imgsz=640)  # 导出 ONNX 用于基准测试
"

# 可选: 下载 YOLOv11s (中等)
model = YOLO('yolo11s.pt')
```

**预期占用**: 
- supervision + ultralytics: ~200MB (含依赖)
- YOLO 模型: yolo11n.pt ~5MB, yolo11n.onnx ~10MB

#### Step 0.4 — 验证基准管线

```python
# demo_phase0.py
import supervision as sv
import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO("yolo11n.onnx")
frame = np.zeros((640, 640, 3), dtype=np.uint8)

results = model(frame)[0]
detections = sv.Detections.from_ultralytics(results)
print(f"Detections: {len(detections)}")

# 验证 ByteTrack
tracker = sv.ByteTrack()
tracked = tracker.update_with_detections(detections)
print(f"Tracked: {len(tracked)}")

# 验证 Annotators
annotated = sv.BoxAnnotator().annotate(frame, tracked)
print(f"Annotated shape: {annotated.shape}")
```

---

### Phase 1: FPGA 预处理加速

**目标**: FPGA 做立体匹配 + 柱面展平, Host 跑 Supervision Python

#### Step 1.1 — 安装 FPGA 厂商工具链

根据计划中的选型, 二选一:

**选项 A: Lattice CrossLink-NX (Phase 1 推荐)**

```bash
# Lattice Diamond (含 Reveal Logic Analyzer)
# 下载: https://www.latticesemi.com/Products/DesignSoftwareAndIP/FPGAandLDS/LatticeDiamond.aspx
# Windows 安装包 ~2GB, 需要 10GB 磁盘空间
# 安装路径: C:\lscc\diamond\3.13\

# Lattice Radiant (CrossLink-NX 需要 Radiant, 不是 Diamond)
# CrossLink-NX 系列需要在 Lattice Radiant 下开发
# 下载: https://www.latticesemi.com/LatticeRadiant
# 安装包 ~3GB, 需要 15GB 磁盘空间

# 环境变量 (安装后自动设置)
# LSC_HOME -> C:\lscc\diamond\3.13
# LSC_DIAMOND -> C:\lscc\diamond\3.13\bin\nt64
```

**选项 B: Xilinx Kria KV260 (Phase 2 过渡)**

```bash
# Vivado ML Standard (免费版, 支持 KV260)
# 下载: https://www.xilinx.com/support/download.html
# 安装包 ~40GB, 需要 80GB 磁盘空间! (C盘空间不足, 必须装到 D:)
# 
# 安装建议:
#   1. 下载 Vivado Unified Installer (~40GB)
#   2. 安装到 D:\Xilinx\Vivado\2025.1
#   3. 只勾选 "Kria" 系列器件 (不必安装全部, 节省空间)
#   4. 安装后环境变量: XILINX_VIVADO -> D:\Xilinx\Vivado\2025.1
```

**磁盘空间评估:**

| 工具 | 安装包 | 安装后 | 建议安装盘 |
|------|--------|--------|-----------|
| Lattice Radiant | ~3GB | ~15GB | D: (有70GB余量, 够) |
| Vivado ML | ~40GB | ~80GB | D: (70GB余量, **不够! 需清理**) |
| 两者都装 | ~43GB | ~95GB | D: 需要清理至少 30GB |

**结论**: C盘只剩12GB, 不够装任何 FPGA 工具链。D盘70GB, 够装 Lattice Radiant (15GB), 但装 Vivado (80GB) 需要清理 D 盘。

#### Step 1.2 — USB 驱动

FPGA 开发板通过 USB 连接时需要驱动:

```bash
# Lattice CrossLink-NX Eval Board
# 板载 FTDI FT2232H -> 需要 FTDI D2XX 驱动
# 下载: https://ftdichip.com/drivers/d2xx-drivers/
# Windows 自动识别, 或从 Lattice Radiant 安装包自带

# Xilinx Kria KV260
# 板载 FTDI + Digilent -> 需要 Digilent Adept Runtime
# 下载: https://digilent.com/reference/software/adept/start
# 安装后会自动注册 JTAG 和 UART 设备

# 验证连接:
# 插上开发板后, 设备管理器应出现:
#   - "Digilent USB Device" (JTAG)
#   - "USB Serial Port (COMx)" (UART)
#   - "USB 3.0 SuperSpeed" (数据通道)
```

#### Step 1.3 — Python USB 通信库

```bash
# 用于 Host 与 FPGA 的 USB 3.0 DMA 通信

# 方式 A: libusb + pyusb (跨平台, 推荐)
uv pip install pyusb

# 方式 B: FTDI 专用 (仅 FTDI 芯片)
uv pip install ftd2xx  # 封装 D2XX DLL

# 方式 C: Cypress FX3 (CrossLink-NX Eval 的 USB 控制器)
# 需要 Cypress CyAPI 库 (Windows 专用)
# 下载 FX3 SDK: https://www.cypress.com/products/ez-usb-fx3
# Python 封装: 基于 ctypes 调用 cyusb.dll
```

#### Step 1.4 — 双目摄像头验证

```bash
# 验证 OpenCV 能否打开双目摄像头 (采购前, 先用普通 USB 摄像头验证管线)
python -c "
import cv2
cap = cv2.VideoCapture(0)  # 或 RealSense
ret, frame = cap.read()
print(f'Camera OK: {frame.shape if ret else \"FAIL\"}')
cap.release()
"

# 如果有 Intel RealSense, 需要安装 SDK
uv pip install pyrealsense2
```

---

### Phase 2: FPGA 推理 + 共享内存桥

#### Step 2.1 — 额外 Python 包

```bash
# 共享内存操作
uv pip install posix_ipc   # Linux 专用
# Windows 共享内存: 使用 win32file.CreateFileMapping (内建, 无需额外包)
# 或使用 mmap 模块 (Python 内建)

# Profiling 工具
uv pip install py-spy      # 性能 profiler
uv pip install memory_profiler  # 内存分析

# 数据可视化 (验证 FPGA 输出)
uv pip install matplotlib
```

#### Step 2.2 — Vitis HLS (高级综合, 可选)

如果要在 Xilinx 上用 C/C++ 编写 FPGA 逻辑而非 HDL:

```bash
# Vitis HLS 包含在 Vivado 安装中
# 路径: D:\Xilinx\Vivado\2025.1\bin\vitis_hls.bat
```

#### Step 2.3 — ILA 调试内核

调试阶段需要在 FPGA bitstream 中插入 ILA (Integrated Logic Analyzer):

```
Phase 2 的调试 bitstream 需要额外:
- Lattice: Reveal Logic Analyzer (~2-5% LUT 额外开销)
- Xilinx: Vivado ILA (~1-3% LUT 额外开销)

注意: 调试 bitstream 可能装不下 YOLO 全模型
方案: 准备两套 bitstream
  - debug.bit  (含 ILA, 降频运行)
  - release.bit (不含 ILA, 全速运行)
```

---

### Phase 3-4: ByteTrack + 全管线

#### Step 3.1 — RISC-V 工具链 (Phase 4)

```bash
# 如果使用 RISC-V 软核运行轻量 Supervision Runtime
# 安装 RISC-V GNU 工具链
# 下载: https://github.com/riscv-collab/riscv-gnu-toolchain/releases

# 或者使用 Lattice Mico32 (Lattice 自有 ISA, 非 RISC-V)
# Mico32 工具链在 Lattice Radiant 安装包内自带
```

#### Step 3.2 — 功耗测量工具

```bash
# 独立运行的功耗测量
# 硬件: Otii Arc Pro / Monsoon Power Monitor (~$500-2000)
# 软件: 开发板自带 PMBus/I2C 电压传感器读数
```

---

## 三、安装顺序与时间预估

```
Week 1 (Phase 0):
  Day 1: 修复 torch, 安装 supervision + ultralytics    [1h]
  Day 2: 跑通 demos, 建立性能基线                       [2h]
  Day 3: 瓶颈分析, 确定 FPGA 优先级                      [2h]
  合计: ~5h

Week 2 (FPGA 工具链):
  Day 1: 下载 Lattice Radiant (~3GB, 取决于网速)       [1-3h]
  Day 2: 安装 + 许可证申请 + Hello World bitstream       [3h]
  Day 3: USB 驱动 + 验证 PC <-> FPGA 通信               [3h]
  合计: ~9h (不含下载等待)

Week 3-4 (Phase 1 调试):
  Day 1: FPGA 双目图像采集 (MIPI CSI -> DDR -> DMA)     [8h]
  Day 2: 立体匹配 IP 调试                                [8h]
  Day 3: Python 桥接层 + USB 验证                        [4h]
  合计: ~20h

Week 5-8 (Phase 2):
  YOLO INT8 量化 + FPGA 部署 + 共享内存桥                [40-60h]
```

---

## 四、风险依赖

| 依赖 | 当前状态 | 缓解措施 |
|------|---------|---------|
| C盘空间不足 (仅12GB) | ❌ | 所有 FPGA 工具装到 D: |
| D盘70GB, 装 Vivado 不够 | ⚠️ | 先用 Lattice (15GB), 清理 D 盘后再装 Vivado |
| PyTorch 循环导入 | ❌ | 重装 torch 或降级 numpy |
| 无 FPGA 开发板硬件 | ⚠️ | Phase 0 纯软件不依赖硬件; 采购建议: Lattice CrossLink-NX Eval ($299) |
| 无双目摄像头 | ⚠️ | Phase 0 用 USB 摄像头/测试图片代替; 采购: RealSense D435i |
| Windows 共享内存 | ⚠️ | Windows mmap 有文件映射限制; Phase 2 需要确认 POSIX 兼容性 |
| 许可证 | ⚠️ | Lattice Radiant: 免费版有器件限制; Vivado ML: 免费版功能完整 |

---

## 五、快速启动命令 (复制粘贴版)

```bash
# ===== Phase 0: 纯软件 =====

# 1. 修复 torch
uv pip uninstall torch
uv pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
uv pip install "numpy<2.0"

# 2. 安装 core 包
uv pip install supervision ultralytics

# 3. 验证
python -c "
import supervision as sv; print(f'supervision {sv.__version__}')
from ultralytics import YOLO; print('ultralytics OK')
import torch; print(f'CUDA: {torch.cuda.is_available()}')
import cv2; print(f'OpenCV: {cv2.__version__}')
"

# 4. 下载模型
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='onnx')"

# ===== Phase 1 前置: FPGA 工具链 =====

# 下载 Lattice Radiant
# 1. 打开 https://www.latticesemi.com/LatticeRadiant
# 2. 注册账号 -> 下载 Windows 版 (~3GB)
# 3. 安装到 D:\lscc\radiant\3.2
# 4. 申请免费许可证 (节点锁定, 绑定本机 MAC)

# ===== Phase 1 前置: USB 驱动 =====

# FTDI 驱动 (CrossLink-NX Eval Board 需要)
# 下载: https://ftdichip.com/drivers/d2xx-drivers/
# 安装: 运行 CDM v2.12.36 WHQL Certified.exe

# ===== Phase 1: 调试环境 =====

# 1. 串口终端 (UART 日志)
# 推荐: TeraTerm (Windows 下最稳定)
# 下载: https://tera-term.en.lo4d.com/download
# 或者使用 VSCode Serial Monitor 插件

# 2. Wireshark (USB 3.0 抓包, 诊断 DMA 丢帧问题)
# 下载: https://www.wireshark.org/download.html
# 需要安装 USBPcap 驱动 (安装 Wireshark 时可选)
uv pip install pyshark  # Python 调用 Wireshark 分析

# 3. FPGA 工具链自带的调试工具
# Lattice Radiant -> Reveal Logic Analyzer (已包含在 Radiant 安装中)
# Vivado -> Hardware Manager + ILA (已包含在 Vivado 安装中)

---

## 六、调试环境核查清单

| 工具 | 用途 | 安装检查 | 备注 |
|------|------|---------|------|
| 串口终端 (TeraTerm / Putty) | FPGA UART 日志 | ❌ 需安装 | 115200, 8N1 |
| Wireshark + USBPcap | USB 3.0 包级别诊断 | ❌ 需安装 | 调试 DMA 丢帧时使用 |
| Lattice Reveal | 片上逻辑分析 (CrossLink-NX) | 随 Radiant 安装 | 类似示波器, 抓内部信号 |
| Vivado ILA | 片上逻辑分析 (Kria KV260) | 随 Vivado 安装 | 同上 |
| Python pyshark | 自动化 USB 抓包分析 | ❌ 需安装 | `uv pip install pyshark` |

### 调试验证命令

开发板到手后, 验证 USB 连接是否正常:

```bash
# 检查 JTAG 设备 (Windows)
# 设备管理器应出现:
#   - Lattice: "FTDI FT2232H" 或 "D2XX" 设备
#   - Xilinx: "Digilent USB Device"

# 检查 UART 虚拟串口
# 设备管理器 -> 端口 (COM 和 LPT):
#   - "USB Serial Port (COM3)" 或类似

# 检查 USB 3.0 SuperSpeed 枚举
# 设备管理器 -> 通用串行总线控制器:
#   - "USB 3.0 根集线器" 且端口速率显示 5Gbps

# Python 验证串口通信
python -c "
import serial
import serial.tools.list_ports
ports = [p.device for p in serial.tools.list_ports.comports()]
print('Available COM ports:', ports)
# 预期: 至少出现一个 FPGA UART 端口
"
uv pip install pyserial
```

### 调试 bitstream 准备

调试版本需要在 bitstream 中插入 ILA/Reveal IP:

```bash
# Lattice 开发流程
# 1. 在 Radiant 中例化 Reveal 控制器
# 2. 选择需要观察的信号 (不超过 64 个探针)
# 3. 设置触发条件 (例如: frame_done == 1)
# 4. 综合 -> 布局布线 -> 生成 debug.bit
# 5. 烧录: 通过 Radiant Programmer 或命令行
#    radiant_programmer -a jtag -m flash -f debug.bit

# Xilinx 开发流程
# 1. 在 Vivado 中例化 ILA IP
# 2. 设置探针宽度和采样深度 (深度越大占 BRAM 越多)
# 3. 综合 -> 实现 -> 生成 debug.bit
# 4. 烧录: Vivado Hardware Manager -> Program device
```

**注意**: 调试 bitstream 通常需要降频运行 (因为 ILA 插入会影响时序收敛)。
推荐在 Phase 1 初期就准备好两套 tcl 脚本:

```bash
# build_debug.tcl  - 含 ILA, 目标时钟 50MHz (降频)
# build_release.tcl - 不含 ILA, 目标时钟 100MHz (全速)
```
