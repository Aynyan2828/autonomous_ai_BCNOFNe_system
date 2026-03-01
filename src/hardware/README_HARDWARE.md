# OLED・ファン制御システム

---

## 概要

Raspberry Pi 4B用Mini Towerクーラーに付属するOLEDディスプレイとPWMファンを制御し、システム状態とAI状態をリアルタイム表示するシステムです。

---

## 主な機能

### 📺 OLED表示

4行のリアルタイム表示:
1.  **1行目**: CPU温度 + CPU使用率
2.  **2行目**: メモリ使用率 + SSD使用率
3.  **3行目**: ファン状態（RPMまたはステータス）
4.  **4行目**: AI状態（Idle / Planning / Acting / Moving Files / Error / Wait Approval）

### 🌡 温度連動ファン制御

| CPU温度 | ファン速度 | PWMデューティ |
| :--- | :--- | :--- |
| 〜50°C | 停止/低速 | 0%〜30% |
| 50〜60°C | 中速 | 50% |
| 60〜70°C | 高速 | 75% |
| 70°C〜 | 最大 + 警告 | 100% |

### 🚨 高温警告

CPU温度が70°C以上になると、Discord/LINEに緊急通知を送信します。

---

## ファイル構成

```
hardware/
├── README_HARDWARE.md              # このファイル
├── HARDWARE_DESIGN.md              # 設計書
├── INSTALL_GUIDE_HARDWARE.md       # インストールガイド
├── requirements.txt                # Pythonパッケージ一覧
├── fan_controller.py               # PWMファン制御モジュール
├── oled_display.py                 # OLED表示モジュール
└── oled_fan_controller.py          # 統合制御モジュール
```

---

## クイックスタート

### 1. インストール

詳細は **INSTALL_GUIDE_HARDWARE.md** を参照してください。

```bash
# I2CとPWMを有効化
sudo raspi-config

# ライブラリをインストール
cd /home/pi/autonomous_ai/hardware
pip3 install -r requirements.txt

# systemdサービスを登録
sudo cp ../systemd/oled-fan-controller.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oled-fan-controller.service
sudo systemctl start oled-fan-controller.service
```

### 2. 動作確認

```bash
# サービスの状態を確認
sudo systemctl status oled-fan-controller.service

# ログを確認
journalctl -u oled-fan-controller.service -f
```

---

## 技術仕様

### ハードウェア

| 項目 | 仕様 |
| :--- | :--- |
| **OLED** | SSD1306 128x64ピクセル (I2C, 0x3C) |
| **ファン** | PWM制御 (GPIO 18, 25kHz) |

### ソフトウェア

| 項目 | 仕様 |
| :--- | :--- |
| **OLED更新頻度** | 2秒ごと |
| **ファン制御頻度** | 5秒ごと |
| **AI状態チェック** | 1秒ごと |
| **CPU使用率目標** | 1%以下 |

---

## トラブルシューティング

### OLEDが表示されない

```bash
# I2C接続を確認
i2cdetect -y 1
```

- `3c` が表示されていれば、OLEDは認識されています。

### ファンが回転しない

- GPIO 18の接続を確認してください。
- `/boot/config.txt` に `dtoverlay=pwm,pin=18,func=2` が追加されているか確認してください。

### ログの確認

```bash
journalctl -u oled-fan-controller.service -n 50
```

---

**詳細は各ドキュメントを参照してください。**
