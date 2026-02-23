# OLED・ファン制御 - インストールガイド

---

## 1. 概要

このガイドでは、Raspberry Pi 4B用Mini Towerクーラーに付属するOLEDディスプレイとPWMファンを制御し、システム状態とAI状態をリアルタイム表示するシステムのインストール手順を説明します。

**前提条件:**
- Raspberry Pi 4B
- Raspberry Pi OS (Bullseye or later)
- Mini Towerクーラー（OLED・ファン付き）
- インターネット接続

---

## 2. ハードウェアのセットアップ

1.  **Mini Towerクーラーの組み立て**
    - クーラーの取扱説明書に従って、Raspberry Pi 4Bに正しく取り付けてください。
    - OLEDとファンのケーブルがGPIOピンに正しく接続されていることを確認してください。

2.  **GPIO接続の確認**
    - **OLED**: I2Cピン（SDA: GPIO 2, SCL: GPIO 3）
    - **ファン**: PWMピン（GPIO 18）

---

## 3. OSの初期設定

### 3.1 I2CとPWMの有効化

1.  **ターミナルを開き、`raspi-config` を実行します。**
    ```bash
    sudo raspi-config
    ```

2.  **I2Cを有効化します。**
    - `3 Interface Options` → `I5 I2C` → `<Yes>` を選択して有効化します。

3.  **PWMを有効化します。**
    - `/boot/config.txt` を編集します。
    ```bash
    sudo nano /boot/config.txt
    ```
    - ファイルの末尾に以下の行を追記します。
    ```
    # PWMファン制御を有効化
    dtoverlay=pwm,pin=18,func=2
    ```
    - `Ctrl+X` → `Y` → `Enter` で保存して終了します。

4.  **再起動します。**
    ```bash
    sudo reboot
    ```

### 3.2 ユーザーの権限設定

1.  **現在のユーザーを `gpio` と `i2c` グループに追加します。**
    ```bash
    sudo usermod -a -G gpio,i2c $USER
    ```

2.  **設定を反映させるため、一度ログアウトして再度ログインします。**

---

## 4. 必要なライブラリのインストール

### 4.1 システムパッケージのインストール

```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip i2c-tools
```

### 4.2 Pythonパッケージのインストール

1.  **プロジェクトディレクトリに移動します。**
    ```bash
    cd /home/pi/autonomous_ai/hardware
    ```

2.  **`requirements.txt` を使ってインストールします。**
    ```bash
    pip3 install -r requirements.txt
    ```

---

## 5. AI状態ファイルの準備

1.  **AI状態ファイルを作成し、パーミッションを設定します。**
    ```bash
    sudo touch /var/run/ai_state.json
    sudo chmod 666 /var/run/ai_state.json
    ```

---

## 6. systemdサービスの登録

1.  **サービスファイルをコピーします。**
    ```bash
    sudo cp /home/pi/autonomous_ai/systemd/oled-fan-controller.service /etc/systemd/system/
    ```

2.  **systemdをリロードします。**
    ```bash
    sudo systemctl daemon-reload
    ```

3.  **サービスを有効化します（起動時に自動実行）。**
    ```bash
    sudo systemctl enable oled-fan-controller.service
    ```

4.  **サービスを開始します。**
    ```bash
    sudo systemctl start oled-fan-controller.service
    ```

---

## 7. 動作確認

### 7.1 サービスのステータス確認

```bash
sudo systemctl status oled-fan-controller.service
```

- `Active: active (running)` と表示されていれば成功です。

### 7.2 OLEDディスプレイの確認

- OLEDディスプレイにシステム情報（CPU温度、メモリ使用率など）が表示されていることを確認します。

### 7.3 ファンの動作確認

- CPU温度に応じてファンの回転数が変化することを確認します。
- 以下のコマンドでCPUに負荷をかけると、ファンの回転数が上がるはずです。
    ```bash
    stress --cpu 1 --timeout 60
    ```

### 7.4 ログの確認

```bash
journalctl -u oled-fan-controller.service -f
```

- エラーが出ていないか確認します。

---

## 8. 操作マニュアル

### 8.1 サービスの管理

| コマンド | 説明 |
| :--- | :--- |
| `sudo systemctl start oled-fan-controller` | サービスを開始 |
| `sudo systemctl stop oled-fan-controller` | サービスを停止 |
| `sudo systemctl restart oled-fan-controller` | サービスを再起動 |
| `sudo systemctl status oled-fan-controller` | サービスの状態を確認 |

### 8.2 AI状態の表示

- OLEDディスプレイの4行目に現在のAIの状態が表示されます。
- 状態の種類:
    - `Idle`: アイドル状態
    - `Planning`: タスク計画中
    - `Acting`: コマンド実行中
    - `Moving Files`: ファイル移動中
    - `Error`: エラー発生
    - `Wait Approval`: 課金承認待ち

---

## 9. トラブルシューティング

### 9.1 OLEDが表示されない

1.  **I2C接続を確認します。**
    ```bash
    i2cdetect -y 1
    ```
    - `3c` が表示されていれば、OLEDは認識されています。

2.  **ケーブルの接続を確認します。**
    - SDA, SCL, VCC, GNDが正しく接続されているか確認してください。

3.  **ライブラリが正しくインストールされているか確認します。**

### 9.2 ファンが回転しない

1.  **GPIO接続を確認します。**
    - GPIO 18に正しく接続されているか確認してください。

2.  **PWMが有効になっているか確認します。**
    - `/boot/config.txt` の設定を確認してください。

3.  **ログを確認します。**
    - `journalctl -u oled-fan-controller.service` でエラーメッセージを確認してください。

---

**以上で、OLED・ファン制御システムのインストールは完了です。**
