# VoxDrive 语音接入

当前采用旁路控制接入：

1. `voxdrive_nlu/live_mic_nlu.py` 调用麦克风和 ASR。
2. NLU 识别出有效命令后，写入 `voxdrive/runtime/voice_command.json`。
3. `team_code/minddrive_b2d_agent.py` 每帧读取最新命令。
4. MindDrive 仍负责感知、轨迹预测和路线跟随；语音只在最终 `VehicleControl` 前做高优先级覆盖。

第一版已经执行的语音控制：

- `STOP` / `EMERGENCY_STOP`：保持全刹停。
- `START` / `CONTINUE_ROUTE`：解除语音刹停，让 MindDrive 接管路线跟随。
- `SET_SPEED`：设置速度上限，例如 `Accelerate to 5 km/h`。
- `SLOW_DOWN`：临时降低速度上限。

第一版暂不直接执行的控制：

- `TURN_LEFT_NEXT`
- `TURN_RIGHT_NEXT`
- `CHANGE_LEFT`
- `CHANGE_RIGHT`

这些命令会被记录，但不直接打方向盘。它们需要后续接 route/lane 行为层，否则可能和全局路线冲突。

## 运行方式

打开第一个终端，启动语音识别：

```bash
conda activate voxdrive
./voxdrive/scripts/run_live_mic_nlu.sh
```

打开第二个终端，启动 MindDrive 语音演示路线：

```bash
conda activate voxdrive
./voxdrive/scripts/run_minddrive_voice_route.sh
```

语音演示脚本默认设置：

```bash
VOXDRIVE_START_HOLD=1
VOXDRIVE_VOICE_COMMAND_PATH=./voxdrive/runtime/voice_command.json
```

因此车辆会先刹停等待。说 `command` 后，听到提示再说 `go ahead`，车辆会解除刹停并由 MindDrive 按路线行驶。

普通路线测试仍然用：

```bash
./voxdrive/scripts/run_minddrive_route.sh
```

普通脚本默认 `VOXDRIVE_START_HOLD=0`，不会因为没有语音命令而停住。

