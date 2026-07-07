# VoxDrive NLU

This module maps ASR text into conservative LMDrive-compatible commands.

Pipeline:

```text
ASR text
  -> wake-word gate
  -> rule parser for safety-critical commands
  -> BGE semantic matching fallback
  -> canonical LMDrive instruction + external control constraints
```

Default local model:

```text
ckpts/bge-small-zh-v1.5
```

Right-click runnable smoke test:

```bash
conda activate voxdrive
python voxdrive/voxdrive_nlu/demo_parse.py
```

Right-click runnable microphone pipeline:

```bash
python voxdrive/voxdrive_nlu/live_mic_nlu.py
```

The microphone pipeline defaults to English ASR (`--language en`) because LMDrive
canonical instructions are English. For Chinese ASR tests, pass `--language zh`
or `--language auto`.

The live microphone pipeline uses strict two-stage interaction:

```text
1. Say: command
2. Wait until the console prints: Recording command... speak now.
3. Say: go ahead / turn left / speed to 5 km/h / stop
```

If the ASR returns `command go ahead` in one chunk, VoxDrive treats it as wake
only and waits for the next utterance.

After wake-up, VoxDrive records the command as one complete audio segment rather
than parsing every fixed chunk. It stops recording when either:

```text
1. speech starts and then silence lasts for --command-end-silence-seconds
2. command speech reaches --command-max-seconds
3. no speech starts before --command-start-timeout-seconds
```

Useful tuning parameters:

```bash
python voxdrive/voxdrive_nlu/live_mic_nlu.py \
  --command-start-timeout-seconds 6 \
  --command-end-silence-seconds 1.2 \
  --command-max-seconds 10 \
  --speech-rms-threshold 0.04
```

Examples:

```text
command
  -> opens a short command window

go ahead
  -> START
  -> Please commence driving.

小沃，前方路口左转
  -> TURN_LEFT_NEXT
  -> Please execute a left turn at the forthcoming intersection.

command speed to 5 km/h
  -> SET_SPEED
  -> Proceed along this route.
  -> external speed_limit_kmh=5

急停
  -> EMERGENCY_STOP
  -> external throttle=0, brake=1
```

Wake-word behavior:

```text
IDLE:
  normal commands are ignored unless they contain command / VoxDrive / 小沃 / 命令 / 语音指令
  English ASR variants such as box drive / voice drive / common are also accepted

ACTIVE:
  saying only "command" opens a 5-second window; the next ASR sentence is parsed
  inline phrases such as "command go ahead" are treated as wake-only by default

EMERGENCY:
  explicit emergency phrases such as "急停" or "emergency stop" bypass the wake word
```

During microphone testing, ignored ASR results are printed by default so you can see
what SenseVoice actually recognized. Use `--no-print-ignored` to show accepted
commands only.
