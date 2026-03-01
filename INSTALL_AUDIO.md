<<<<<<< Updated upstream
# shipOS 音声サブシステム インストールガイド
> Raspberry Pi 4B / オフライン優先で動作する音声会話・通知・独り言

---

## 1. システム依存パッケージ

```bash
sudo apt update && sudo apt install -y \
  build-essential cmake git \
  python3-pip python3-venv \
  evtest \
  alsa-utils pulseaudio pipewire wireplumber \
  libsndfile1-dev
```

---

## 2. whisper.cpp（オフラインSTT）

```bash
cd /home/pi
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make -j4

# tinyモデル（軽量・Pi4推奨）
bash models/download-ggml-model.sh tiny

# 動作テスト
./main -m models/ggml-tiny.bin -f samples/jfk.wav -l ja --no-timestamps
```

> baseモデルを使う場合: `bash models/download-ggml-model.sh base`
> config.yaml の `stt.whisper_cpp.model` を変更

---

## 3. Piper TTS（オフラインTTS）

```bash
cd /home/pi
mkdir piper && cd piper

# Piperバイナリ（ARM64）
wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz
tar xzf piper_linux_aarch64.tar.gz

# 日本語音声モデル
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/ja/ja_JP/takumi/medium/ja_JP-takumi-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/ja/ja_JP/takumi/medium/ja_JP-takumi-medium.onnx.json

# 動作テスト
echo "テスト音声" | ./piper --model ja_JP-takumi-medium.onnx --output_file test.wav
aplay test.wav
```

---

## 4. Python依存

```bash
cd /home/pi/autonomous_ai
pip install evdev pyyaml psutil
```

---

## 5. 入力デバイス確認

```bash
# マクロパッドのデバイス番号を確認
sudo evtest
# → /dev/input/event12 等を確認

# キーコード確認
sudo evtest /dev/input/event12
# F13=183, F14=184, F15=185, F16=186, F17=187
# VolumeUp=115, VolumeDown=114

# 安定パス確認（推奨）
ls -la /dev/input/by-id/
```

---

## 6. 権限設定

```bash
# piユーザーをinput/audioグループに追加
sudo usermod -aG input,audio pi

# 再起動して反映
sudo reboot
```

---

## 7. オーディオ確認

```bash
# 出力デバイス確認
aplay -l

# 入力デバイス確認
arecord -l

# スピーカーテスト
speaker-test -t wav -c 2

# 録音→再生テスト
arecord -D default -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav
aplay /tmp/test.wav
```

---

## 8. 設定カスタマイズ

`src/audio/config.yaml` を環境に合わせて編集:

```yaml
input:
  device_path: "/dev/input/event12"  # evtestで確認した番号

stt:
  engine: "whisper_cpp"
  whisper_cpp:
    binary: "/home/pi/whisper.cpp/main"
    model: "/home/pi/whisper.cpp/models/ggml-tiny.bin"

tts:
  engine: "piper"
  piper:
    binary: "/home/pi/piper/piper"
    model: "/home/pi/piper/ja_JP-takumi-medium.onnx"
```

---

## 9. systemd設定

```bash
# サービスファイルコピー
sudo cp /home/pi/autonomous_ai/systemd/shipos-audio.service /etc/systemd/system/

# 有効化
sudo systemctl daemon-reload
sudo systemctl enable shipos-audio.service
sudo systemctl start shipos-audio.service

# ステータス確認
sudo systemctl status shipos-audio.service

# ログ確認
journalctl -u shipos-audio -f
```

---

## 10. 動作確認チェックリスト

| テスト | 操作 | 期待結果 |
|--------|------|----------|
| F13 会話 | 押して話す→離す | 音声認識→応答再生 |
| F14 ミュート | 押す | 「独り言ミュートしたよ」 |
| F15 状態 | 押す | CPU温度等を読み上げ |
| F16 航海日誌 | 押す | 日誌記録＋読み上げ |
| F17 緊急停止 | 押す | 「緊急停止するね」→AI停止 |
| ノブ | 回す | 音量変化 |
| 独り言 | 7-25分待つ | 小音量で独り言 |

---

## 11. トラブルシュート

**デバイス番号が変わる:**
→ `/dev/input/by-id/` のシンボリックリンクを使用

**権限エラー (Permission denied):**
→ `sudo usermod -aG input pi && sudo reboot`

**PipeWire/ALSA切り替え:**
→ `wpctl status` で確認、`wpctl set-volume` で音量制御

**無音:**
→ `aplay -l` で出力先確認、`wpctl set-default` でシンク設定

**whisper.cppが遅い:**
→ tinyモデルに変更、スレッド数を調整 (`threads: 2`)

**Piperエラー:**
→ モデルファイルの存在確認、`chmod +x /home/pi/piper/piper`

---

## 12. CPU負荷対策

- whisper.cppはtinyモデル推奨（baseより2倍速い）
- Piperは軽量（100ms以内で合成）
- 独り言間隔を広げる（config.yamlの `monologue.min_interval_min`）
- 録音は16kHz mono（最小帯域）
=======
# shipOS 音声サブシステム インストールガイド
> Raspberry Pi 4B / オフライン優先で動作する音声会話・通知・独り言

---

## 1. システム依存パッケージ

```bash
sudo apt update && sudo apt install -y \
  build-essential cmake git \
  python3-pip python3-venv \
  evtest \
  alsa-utils pulseaudio pipewire wireplumber \
  libsndfile1-dev
```

---

## 2. whisper.cpp（オフラインSTT）

```bash
cd /home/pi
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp

# cmakeビルド
cmake -B build
cmake --build build -j4

# tinyモデル（軽量・Pi4推奨）
bash models/download-ggml-model.sh tiny

# 動作テスト
./build/bin/whisper-cli -m models/ggml-tiny.bin -f samples/jfk.wav -l ja --no-timestamps
```

> baseモデルを使う場合: `bash models/download-ggml-model.sh base`
> config.yaml の `stt.whisper_cpp.model` を変更

---

## 3. OpenAI TTS（音声合成）

> Piperには公式の日本語音声モデルが存在しないため、OpenAI TTS APIを使用

```bash
# openaiパッケージインストール
pip install openai

# .envにAPIキーを設定
echo 'OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx' >> /home/pi/autonomous_ai/.env

# 動作テスト
python3 -c "
import openai, os
client = openai.OpenAI()
response = client.audio.speech.create(
    model='tts-1', voice='nova', input='テスト音声です。shipOS起動完了',
    response_format='wav'
)
response.stream_to_file('/tmp/test_tts.wav')
print('OK: /tmp/test_tts.wav')
"
aplay /tmp/test_tts.wav
```

---

## 4. Python依存

```bash
cd /home/pi/autonomous_ai
pip install evdev pyyaml psutil openai
```

---

## 5. 入力デバイス確認

```bash
# マクロパッドのデバイス番号を確認
sudo evtest
# → /dev/input/event12 等を確認

# キーコード確認
sudo evtest /dev/input/event12
# F13=183, F14=184, F15=185, F16=186, F17=187
# VolumeUp=115, VolumeDown=114

# 安定パス確認（推奨）
ls -la /dev/input/by-id/
```

---

## 6. 権限設定

```bash
# piユーザーをinput/audioグループに追加
sudo usermod -aG input,audio pi

# 再起動して反映
sudo reboot
```

---

## 7. オーディオ確認

```bash
# 出力デバイス確認
aplay -l

# 入力デバイス確認
arecord -l

# スピーカーテスト
speaker-test -t wav -c 2

# 録音→再生テスト
arecord -D default -f S16_LE -r 16000 -c 1 -d 5 /tmp/test.wav
aplay /tmp/test.wav
```

---

## 8. 設定カスタマイズ

`src/audio/config.yaml` を環境に合わせて編集:

```yaml
input:
  device_path: "/dev/input/event12"  # evtestで確認した番号

stt:
  engine: "whisper_cpp"
  whisper_cpp:
    binary: "/home/pi/whisper.cpp/build/bin/whisper-cli"
    model: "/home/pi/whisper.cpp/models/ggml-tiny.bin"

tts:
  engine: "openai_tts"
  openai_tts:
    model: "tts-1"      # tts-1 or tts-1-hd
    voice: "nova"       # alloy, echo, fable, onyx, nova, shimmer
```

---

## 9. systemd設定

```bash
# サービスファイルコピー
sudo cp /home/pi/autonomous_ai/systemd/shipos-audio.service /etc/systemd/system/

# 有効化
sudo systemctl daemon-reload
sudo systemctl enable shipos-audio.service
sudo systemctl start shipos-audio.service

# ステータス確認
sudo systemctl status shipos-audio.service

# ログ確認
journalctl -u shipos-audio -f
```

---

## 10. 動作確認チェックリスト

| テスト | 操作 | 期待結果 |
|--------|------|----------|
| F13 会話 | 押して話す→離す | 音声認識→応答再生 |
| F14 ミュート | 押す | 「独り言ミュートしたよ」 |
| F15 状態 | 押す | CPU温度等を読み上げ |
| F16 航海日誌 | 押す | 日誌記録＋読み上げ |
| F17 緊急停止 | 押す | 「緊急停止するね」→AI停止 |
| ノブ | 回す | 音量変化 |
| 独り言 | 7-25分待つ | 小音量で独り言 |

---

## 11. トラブルシュート

**デバイス番号が変わる:**
→ `/dev/input/by-id/` のシンボリックリンクを使用

**権限エラー (Permission denied):**
→ `sudo usermod -aG input pi && sudo reboot`

**PipeWire/ALSA切り替え:**
→ `wpctl status` で確認、`wpctl set-volume` で音量制御

**無音:**
→ `aplay -l` で出力先確認、`wpctl set-default` でシンク設定

**whisper.cppが遅い:**
→ tinyモデルに変更、スレッド数を調整 (`threads: 2`)

**Piperエラー:**
→ モデルファイルの存在確認、`chmod +x /home/pi/piper/piper`

---

## 12. CPU負荷対策

- whisper.cppはtinyモデル推奨（baseより2倍速い）
- Piperは軽量（100ms以内で合成）
- 独り言間隔を広げる（config.yamlの `monologue.min_interval_min`）
- 録音は16kHz mono（最小帯域）
>>>>>>> Stashed changes
