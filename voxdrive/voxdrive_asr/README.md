# VoxDrive ASR Utilities

Install and run inside the `voxdrive` conda environment.

Download models:

```bash
conda activate voxdrive
python voxdrive/voxdrive_asr/download_models.py SenseVoiceSmall fsmn-vad
```

Run a local SenseVoice test:

```bash
python voxdrive/voxdrive_asr/test_funasr_asr.py \
  --audio ckpts/SenseVoiceSmall/example/zh.mp3 \
  --model-dir ckpts/SenseVoiceSmall \
  --vad-dir ckpts/fsmn-vad \
  --device cuda:0 \
  --language auto \
  --merge-vad
```

For future VoxDrive work, keep model directories under `ckpts/<model_name>` and pass local paths into FunASR instead of relying on user cache directories.

List microphone devices:

```bash
python voxdrive/voxdrive_asr/live_mic_asr.py --list-devices
```

Run chunked microphone transcription with the built-in defaults:

```bash
python voxdrive/voxdrive_asr/live_mic_asr.py
```

The defaults are `plughw:1,0`, `ckpts/SenseVoiceSmall`, `ckpts/fsmn-vad`, `cuda:0`, and 2-second chunks.

Override defaults when needed:

```bash
python voxdrive/voxdrive_asr/live_mic_asr.py \
  --alsa-device plughw:1,0 \
  --model-dir ckpts/SenseVoiceSmall \
  --vad-dir ckpts/fsmn-vad \
  --infer-device cuda:0 \
  --chunk-seconds 3
```

Use `plughw:1,0` for the USB camera microphone shown by `arecord -l`; use `default` or another `plughw:<card>,<device>` if your active microphone differs.

For a short smoke test, add `--max-chunks 5`.
