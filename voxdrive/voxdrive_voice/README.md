# VoxDrive 语音接入

当前采用旁路控制接入：

1. `voxdrive_nlu/live_mic_nlu.py` 调用麦克风和 ASR。
2. NLU 识别出有效命令后，写入 `voxdrive/runtime/voice_command.json`。
3. `team_code/minddrive_b2d_agent.py` 每帧读取最新命令。
4. MindDrive 仍负责感知、轨迹预测和路线跟随；语音只在最终 `VehicleControl` 前做高优先级覆盖。

已经执行的语音控制：

- `STOP` / `EMERGENCY_STOP`：保持全刹停。
- `START` / `CONTINUE_ROUTE`：解除语音刹停，让 MindDrive 接管路线跟随。
- `SET_SPEED`：设置目标速度，例如“加速到每小时 20 公里”。
- `ACCELERATE`：在当前目标上增加 10 km/h，例如“加速”“快一点”。
- `SLOW_DOWN`：临时将目标速度降低 10 km/h。
- `TURN_LEFT_NEXT` / `TURN_RIGHT_NEXT`：将 MindDrive 的高层导航指令切换为下个路口左/右转。
- `TURN_LEFT_AFTER_DISTANCE` / `TURN_RIGHT_AFTER_DISTANCE`：行驶指定距离后切换转弯指令。
- `CHANGE_LEFT` / `CHANGE_RIGHT`：切换为左/右变道指令；检测到车辆已向目标车道横移且航向恢复，或达到最大变道距离后，自动进入 `LANEFOLLOW` 回正阶段，最后将方向盘置中并交还原路线。

转弯和变道仍由 MindDrive 的感知与轨迹网络生成轨迹，而不是固定时长锁死方向盘。说“继续行驶”或“保持直行”可以取消尚未完成的语音机动；说“停车”会立即取消机动并全刹。

可通过环境变量调整行为：

```bash
VOXDRIVE_MAX_SPEED_KMH=50
VOXDRIVE_ACCEL_DELTA_KMH=10
VOXDRIVE_LANE_CHANGE_DISTANCE_M=18
VOXDRIVE_LANE_SETTLE_DISTANCE_M=8
VOXDRIVE_LANE_MIN_LATERAL_M=2.5
VOXDRIVE_TURN_DISTANCE_M=45
VOXDRIVE_TURN_SETTLE_DISTANCE_M=10
```

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

语音演示脚本强制设置：

```bash
VOXDRIVE_START_HOLD=1
VOXDRIVE_VOICE_COMMAND_PATH=./voxdrive/runtime/voice_command.json
```

因此车辆会先刹停等待。启动前以及模型加载期间留下的旧命令不会解除刹停。说 `command` 后，听到提示再说 `go ahead`，车辆会解除刹停并由 MindDrive 按路线行驶。

普通路线测试仍然用：

```bash
./voxdrive/scripts/run_minddrive_route.sh
```

普通脚本默认 `VOXDRIVE_START_HOLD=0`，不会因为没有语音命令而停住。
