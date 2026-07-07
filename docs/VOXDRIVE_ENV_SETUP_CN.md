# VoxDrive 环境配置说明

本文档记录当前 VoxDrive 项目的推荐环境配置，覆盖 ASR/NLU、MindDrive、mmcv 编译、CARLA 0.9.15 联动和常见报错处理。

当前项目路径：

```bash
/home/mofltye/Pycharm_Project/PROJECT_CODE/VoxDrive
```

当前 CARLA 路径：

```bash
/home/mofltye/Carla/CARLA_0_9_15
```

## 1. 基本结论

建议先保持：

```text
Python: 3.8
CUDA: 11.8
PyTorch: cu118 版本
CARLA: 0.9.15
```

原因：

- MindDrive 原始环境文档要求 Python 3.8，CARLA 0.9.15 的 Python egg 也是 `py3.7`，在 Python 3.8 环境下通常可用。
- 现在不建议升级到 Python 3.9。升级 Python 会额外影响 CARLA、mmcv、旧版依赖和部分编译扩展，收益不明显。
- torch 可以比原始文档高一些，但必须和 CUDA 11.8 匹配。当前已使用 `torch 2.4.1+cu118`。
- mmcv 这类 CUDA/C++ 扩展必须用 CUDA 11.8 支持的编译器。当前系统默认 `gcc/g++ 12.3` 不兼容，需要指定 `gcc-11/g++-11`。

## 2. Conda 环境

如果需要重建环境：

```bash
conda create -n voxdrive python=3.8 -y
conda activate voxdrive
```

确认版本：

```bash
python --version
python -m pip --version
```

当前可用环境中 Python 是 `3.8.20`，可以继续用。

## 3. 安装 PyTorch

torch 由你自己安装。推荐使用 CUDA 11.8 对应版本，例如：

```bash
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

安装后检查：

```bash
python - <<'PY'
import torch
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())
PY
```

期望：

```text
torch 版本带 +cu118
torch.version.cuda = 11.8
torch.cuda.is_available() = True
```

如果在受限工具环境里看到 `cuda available False`，不一定代表本机终端不可用。以你自己终端里执行结果为准。

## 4. 安装基础编译工具

```bash
python -m pip install ninja packaging
```

确认 gcc：

```bash
gcc --version
g++ --version
which gcc-11
which g++-11
```

当前机器上可用：

```text
/usr/bin/gcc-11
/usr/bin/g++-11
```

## 5. 编译安装当前项目的 mmcv

不要直接使用：

```bash
python -m pip install -v -e .
```

直接安装会用系统默认 `gcc/g++ 12`，CUDA 11.8 编译会失败，典型错误：

```text
unsupported GNU version! gcc versions later than 11 are not supported!
```

使用下面的命令：

```bash
CC=/usr/bin/gcc-11 CXX=/usr/bin/g++-11 MAX_JOBS=8 TORCH_CUDA_ARCH_LIST=8.9 \
python -m pip install -v -e . --no-deps --no-build-isolation
```

说明：

- `CC/CXX`：指定 gcc-11/g++-11，避免 CUDA 11.8 和 gcc 12 冲突。
- `MAX_JOBS=8`：并行编译线程数。如果内存不够，可以改成 `MAX_JOBS=2` 或 `MAX_JOBS=4`。
- `TORCH_CUDA_ARCH_LIST=8.9`：适配 RTX 40 系/Ada 架构。如果不是 40 系显卡，需要改成对应架构。
- `--no-deps`：不让 pip 自动重装一堆依赖，避免把你已经装好的 torch 或其他包搞乱。
- `--no-build-isolation`：使用当前 conda 环境里的 torch/ninja/packaging 编译。

常见显卡架构参考：

```text
RTX 40 系: 8.9
RTX 30 系 / A10: 8.6
A100: 8.0
RTX 20 系 / T4: 7.5
```

## 6. 验证 mmcv

先配置 CARLA/leaderboard/scenario_runner 路径，再验证。因为这份 MindDrive 代码的 `mmcv` import 会连带导入 CARLA 相关模块。

```bash
export CARLA_ROOT=/home/mofltye/Carla/CARLA_0_9_15
export PYTHONPATH=$PWD:$PWD/rl_projects:$PWD/rl_projects/scenario_runner:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg:$CARLA_ROOT/PythonAPI/carla:$PYTHONPATH
```

验证：

```bash
python - <<'PY'
import carla
print("carla import OK")

import leaderboard
print("leaderboard import OK")

import srunner
print("srunner import OK")

import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "available", torch.cuda.is_available())

import mmcv
print("mmcv", getattr(mmcv, "__version__", "local"))

import mmcv._ext
print("mmcv._ext OK")
PY
```

成功时至少应看到：

```text
carla import OK
leaderboard import OK
srunner import OK
mmcv._ext OK
```

## 7. CARLA 联动配置

本项目不要改全局 CARLA 安装，避免影响其他项目。每次运行 VoxDrive/MindDrive 前，在当前终端设置环境变量即可。

```bash
export CARLA_ROOT=/home/mofltye/Carla/CARLA_0_9_15
export PYTHONPATH=$PWD:$PWD/rl_projects:$PWD/rl_projects/scenario_runner:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg:$CARLA_ROOT/PythonAPI/carla:$PYTHONPATH
```

如果运行时提示找不到 CARLA 动态库，再补充：

```bash
export LD_LIBRARY_PATH=$CARLA_ROOT/CarlaUE4/Binaries/Linux:$LD_LIBRARY_PATH
```

启动 CARLA：

```bash
/home/mofltye/Carla/CARLA_0_9_15/CarlaUE4.sh -RenderOffScreen -quality-level=Low -carla-rpc-port=2000
```

MindDrive 的 `leaderboard_evaluator.py` 当前会自动启动 CARLA，不需要提前手动启动。推荐直接用一键脚本：

```bash
./voxdrive/scripts/run_minddrive_route.sh
```

默认运行 `data/routes/rollout_routes.xml` 中的 route `1773`，默认无头启动 CARLA。

有头模式启动：

```bash
CARLA_RENDER_MODE=windowed ./voxdrive/scripts/run_minddrive_route.sh
```

常用覆盖参数：

```bash
ROUTES_SUBSET=1792 ./voxdrive/scripts/run_minddrive_route.sh
CARLA_QUALITY_LEVEL=Epic CARLA_RENDER_MODE=windowed ./voxdrive/scripts/run_minddrive_route.sh
PORT=2000 TM_PORT=8000 GPU_RANK=0 ./voxdrive/scripts/run_minddrive_route.sh
```

## 8. 模型目录约定

所有模型统一放到：

```bash
./ckpts/<模型名>
```

当前约定：

```text
ckpts/
  SenseVoiceSmall/
  fsmn-vad/
  bge-small-zh-v1.5/
  minddrive/
```

MindDrive 0.5B 实验需要的文件建议放成：

```text
ckpts/minddrive/
  minddrive_rltrain.pth
  llava-qwen2-0.5b/
    config.json
    generation_config.json
    model.safetensors
    tokenizer.json
    tokenizer_config.json
    special_tokens_map.json
    added_tokens.json
    merges.txt
    vocab.json
```

下载 MindDrive 0.5B 权重可以使用：

```bash
huggingface-cli download poleyzdk/Minddrive \
  --local-dir ./ckpts/minddrive \
  --include \
  "minddrive_rltrain.pth" \
  "llava-qwen2-0.5b/*.json" \
  "llava-qwen2-0.5b/*.safetensors" \
  "llava-qwen2-0.5b/merges.txt" \
  "llava-qwen2-0.5b/vocab.json"
```

## 9. ASR/NLU 测试

VoxDrive 新代码放在：

```text
voxdrive/
  voxdrive_asr/
  voxdrive_nlu/
```

麦克风 ASR 测试：

```bash
python voxdrive/voxdrive_asr/live_mic_asr.py
```

麦克风 ASR + NLU 命令测试：

```bash
python voxdrive/voxdrive_nlu/live_mic_nlu.py
```

当前设计是先说唤醒词：

```text
command
```

然后脚本进入短时间命令录音状态，再说驾驶指令，例如：

```text
go ahead
stop
turn left
accelerate to 5 km/h
```

## 10. 常见问题

### 10.1 pip 提示 Python 版本不匹配

例如：

```text
Link requires a different Python (3.8.20 not in: '>=3.10'): pip-26.x
```

这通常不是根因，只是 pip 在跳过不兼容的新版 pip 包。真正失败原因要继续往下看 `error:` 或编译日志。

### 10.2 mmcv 编译失败，提示 gcc 版本太高

错误：

```text
unsupported GNU version! gcc versions later than 11 are not supported!
```

解决：

```bash
CC=/usr/bin/gcc-11 CXX=/usr/bin/g++-11 MAX_JOBS=8 TORCH_CUDA_ARCH_LIST=8.9 \
python -m pip install -v -e . --no-deps --no-build-isolation
```

### 10.3 `No module named carla`

说明当前终端没有加 CARLA PythonAPI 路径。

解决：

```bash
export CARLA_ROOT=/home/mofltye/Carla/CARLA_0_9_15
export PYTHONPATH=$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg:$CARLA_ROOT/PythonAPI/carla:$PYTHONPATH
```

### 10.4 `No module named leaderboard`

说明没有加项目里的 `rl_projects` 路径。

解决：

```bash
export PYTHONPATH=$PWD:$PWD/rl_projects:$PYTHONPATH
```

### 10.5 `No module named srunner`

说明没有加 ScenarioRunner 路径。

解决：

```bash
export PYTHONPATH=$PWD/rl_projects/scenario_runner:$PYTHONPATH
```

### 10.6 Hugging Face 或 Matplotlib cache 不可写

如果看到：

```text
There was a problem when trying to write in your cache folder
```

或者看到 Matplotlib config/cache 目录不可写，可以临时指定缓存目录：

```bash
export HF_HOME=/tmp/voxdrive-hf
export MPLCONFIGDIR=/tmp/voxdrive-mpl
```

这两个不是必须环境变量，只是临时规避用户目录不可写的警告。项目模型仍然建议下载到 `./ckpts/<模型名>`，不要依赖用户级缓存。

## 11. 推荐的一次性终端初始化命令

进入项目根目录后：

```bash
conda activate voxdrive

export CARLA_ROOT=/home/mofltye/Carla/CARLA_0_9_15
export PYTHONPATH=$PWD:$PWD/rl_projects:$PWD/rl_projects/scenario_runner:$CARLA_ROOT/PythonAPI/carla/dist/carla-0.9.15-py3.7-linux-x86_64.egg:$CARLA_ROOT/PythonAPI/carla:$PYTHONPATH
```

然后验证：

```bash
python - <<'PY'
import carla, leaderboard, srunner
import torch, mmcv, mmcv._ext
print("torch:", torch.__version__, torch.version.cuda, torch.cuda.is_available())
print("env OK")
PY
```
