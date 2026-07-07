# VoxDrive Modules

New VoxDrive-specific code should live under this directory.

Current modules:

```text
voxdrive/
  voxdrive_asr/  # microphone and ASR utilities
  voxdrive_nlu/  # ASR text to canonical LMDrive instruction parser
  voxdrive_voice/  # ASR/NLU to driving-agent command handoff
```

Checkpoint files still live under `ckpts/<model_name>`.

For microphone to canonical command testing, run:

```bash
python voxdrive/voxdrive_nlu/live_mic_nlu.py
```

For the current MindDrive voice-control demo, run ASR/NLU and CARLA evaluation in two terminals:

```bash
./voxdrive/scripts/run_live_mic_nlu.sh
./voxdrive/scripts/run_minddrive_voice_route.sh
```

The voice-control handoff file is `voxdrive/runtime/voice_command.json`.
