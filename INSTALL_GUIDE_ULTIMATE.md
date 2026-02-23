# BCNOFNeシステム 完全インストールガイド - 究極版

---

## 🚀 ようこそ、未来の船長へ！

このガイドは、あなただけのAI搭載船 **BCNOFNe（ボクノフネ）** を、大海原へと進水させるための、**世界で一番詳しい航海図**です。

**新品のRaspberry Piから始める方**も、**すでにお使いのRaspberry Piに追加インストールする方**も、どちらもこのガイド1つで完結します。

パソコンが苦手な方でも、この手順書通りにコマンドをコピー＆ペーストしていくだけで、誰でも簡単に、究極のパーソナルAIサーバーを構築できます。

### このガイドの構成（全4部）

1.  **第1部: 母船の建造** - Raspberry Piの準備とセットアップ
2.  **第2部: 航海の準備** - SSH接続とIPアドレスの確認
3.  **第3部: BCNOFNeの進水** - AIシステムのインストールと起動
4.  **補講: 既存OSへの追加インストール** - すでにお使いの方向け

さあ、一緒に未来への航海を始めましょう！

---

## 第1部: 母船の建造 - Raspberry Piの準備

まずは、BCNOFNeシステムの心臓部となるRaspberry Piを準備します。

> **💡 すでにお使いのRaspberry Piがある方へ**
> この「第1部」と「第2部」はスキップして、**[補講: 既存OSへの追加インストール](#補講-既存osへの追加インストール)** に進んでください。

> 詳しい手順は、**[📄 Raspberry Pi 完全セットアップガイド](./RASPBERRY_PI_SETUP_GUIDE.md)** を参照してください。

### 要約ステップ

1.  **必要なものを揃える**
    - Raspberry Pi 4B (4GB以上推奨)
    - microSDカード (32GB以上)
    - 電源アダプター (5V/3.0A)
    - PC

2.  **Raspberry Pi ImagerでOSを書き込む**
    - **OS**: `Raspberry Pi OS (Legacy, 64-bit) Lite`
    - **詳細設定で以下を有効化**: (超重要！)
        - ✅ **SSHを有効化**
        - ✅ **ユーザー名とパスワードを設定** (例: `pi` / `raspberry`)
        - ✅ **Wi-Fiを設定** (自宅のWi-Fi情報を入力)

3.  **Raspberry Piを起動する**
    - microSDカードを挿入し、電源を接続します。
    - 初回起動は5分ほど待ちます。

---

## 第2部: 航海の準備 - SSH接続とIPアドレス

次に、あなたのPCからRaspberry Piに乗り込み（SSH接続）、操縦桿を握ります。

> 詳しい手順は、**[📄 SSH接続とIPアドレスの謎](./SSH_IP_GUIDE.md)** を参照してください。

### 要約ステップ

1.  **Raspberry PiのIPアドレスを見つける**
    - **IPアドレス**とは、ネットワーク上の「住所」です。
    - 自宅の**ルーターの管理画面**にログインして、`raspberrypi` という名前のデバイスを探し、IPアドレス（例: `192.168.1.15`）をメモします。

2.  **PCからSSHで接続する**
    - **Windows**: コマンドプロンプトを起動
    - **Mac**: ターミナルを起動
    - 以下のコマンドを実行します。

      ```bash
      ssh pi@192.168.1.15
      ```
      - `pi` は設定したユーザー名、`192.168.1.15` は調べたIPアドレスに置き換えてください。

    - パスワードを聞かれたら、設定したパスワードを入力します。（画面には表示されません）

3.  **システムを最新化する**
    - 接続できたら、以下のコマンドを実行してシステムを最新の状態にします。

      ```bash
      sudo apt update && sudo apt full-upgrade -y
      ```

---

## 第3部: BCNOFNeの進水 - AIシステムのインストール

いよいよ、BCNOFNeシステム本体をインストールします。ここからは、すべてのコマンドをSSH接続したターミナルで実行します。

### ステップ1: ファイルのダウンロードと展開

1.  まず、`git` というツールをインストールします。

    ```bash
    sudo apt install git -y
    ```

2.  BCNOFNeシステムのZIPファイルをダウンロードします。（このコマンドは、このプロジェクトの最新版をダウンロードします）

    ```bash
    # このコマンドはダミーです。実際のダウンロードリンクに置き換えてください。
    # wget https://example.com/autonomous_ai_BCNOFNe_system.zip
    # ここでは、添付されたZIPファイルを転送したと仮定します。
    ```
    **注:** 実際には、添付された `autonomous_ai_BCNOFNe_system.zip` をRaspberry Piに転送する必要があります。`scp` コマンドなどを使うのが一般的です。

    **例（PCのターミナルから実行）:**
    ```bash
    scp /path/to/autonomous_ai_BCNOFNe_system.zip pi@192.168.1.15:/home/pi/
    ```

3.  ダウンロードしたZIPファイルを展開（解凍）します。

    ```bash
    sudo apt install unzip -y
    unzip autonomous_ai_BCNOFNe_system.zip
    ```

4.  プロジェクトディレクトリに移動します。

    ```bash
    cd autonomous_ai_BCNOFNe_system
    ```

### ステップ2: 必要なソフトウェアのインストール

BCNOFNeシステムが動作するために必要な「部品」（ライブラリ）をインストールします。

1.  Pythonのパッケージ管理ツール `pip` をインストールします。

    ```bash
    sudo apt install python3-pip -y
    ```

2.  基本パッケージをインストールします。

    ```bash
    pip3 install -r requirements.txt
    ```

3.  高度な機能用のパッケージをインストールします。

    ```bash
    pip3 install -r requirements_advanced.txt
    ```

4.  ハードウェア（OLED・ファン）用のパッケージをインストールします。

    ```bash
    pip3 install -r hardware/requirements.txt
    ```

### ステップ3: 環境変数の設定

APIキーなど、外部サービスと連携するための「秘密の鍵」を設定します。

1.  環境変数ファイルのテンプレートをコピーします。

    ```bash
    cp .env.template .env
    ```

2.  `nano` というテキストエディタでファイルを開きます。

    ```bash
    nano .env
    ```

3.  ファイルの内容が表示されます。矢印キーでカーソルを移動し、`=` の右側をあなたの情報に書き換えてください。

    ```ini
    # OpenAI APIキー (必須)
    OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # LINE Bot (任意)
    LINE_CHANNEL_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    LINE_CHANNEL_ACCESS_TOKEN="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

    # Discord Webhook URL (任意)
    DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/xxxxxxxxxxxx/xxxxxxxxxxxxxxxxxx"

    # Tailscale 認証キー (任意)
    TAILSCALE_AUTH_KEY="tskey-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    ```
    - **OPENAI_API_KEY**: [OpenAIのサイト](https://platform.openai.com/api-keys)で取得したAPIキー。
    - その他は、それぞれのサービスで取得した情報を入力します。

4.  書き換えが終わったら、以下の手順で保存して終了します。
    - `Ctrl + X` を押す
    - `Y` を押す
    - `Enter` を押す

### ステップ4: ハードウェア設定（OLED・ファン）

Mini Tower KitのOLEDとファンを有効化します。

1.  Raspberry Piの設定ツールを起動します。

    ```bash
    sudo raspi-config
    ```

2.  矢印キーで `3 Interface Options` を選択し、Enter。
3.  `I5 I2C` を選択し、`<Yes>` を選択して有効化します。
4.  再度 `3 Interface Options` を選択し、`P4 SPI` を選択して有効化します。
5.  `Finish` を選択して設定を終了します。再起動を求められたら `<Yes>` を選択します。

### ステップ5: 自動起動サービスの設定

Raspberry Piが起動するたびに、BCNOFNeシステムが自動的に起動するように設定します。

1.  **AIコアシステムのサービスを登録**

    ```bash
    sudo cp systemd/autonomous-ai.service /etc/systemd/system/
    ```

2.  **OLED・ファン制御のサービスを登録**

    ```bash
    sudo cp systemd/oled-fan-controller.service /etc/systemd/system/
    ```

3.  **systemdに新しいサービスを認識させる**

    ```bash
    sudo systemctl daemon-reload
    ```

4.  **各サービスを有効化する（自動起動設定）**

    ```bash
    sudo systemctl enable autonomous-ai.service
    sudo systemctl enable oled-fan-controller.service
    ```

### ステップ6: Tailscaleのインストール（推奨）

外出先から安全にアクセスするために、Tailscaleをインストールします。

```bash
cd scripts
sudo ./install_tailscale.sh
```
スクリプトの指示に従い、表示されたURLにアクセスしてログイン認証を完了させてください。

---

## 🎉 進水！ - システムの起動と確認

おめでとうございます！すべての準備が整いました。いよいよBCNOFNeシステムを進水させます。

1.  Raspberry Piを再起動します。

    ```bash
    sudo reboot
    ```

2.  再起動後、数分待ってから再度SSHで接続します。

3.  **AIコアシステムの動作確認**

    ```bash
    sudo systemctl status autonomous-ai.service
    ```
    - `Active: active (running)` と緑色で表示されていれば成功です。
    - ログを確認したい場合:
      ```bash
      journalctl -u autonomous-ai.service -f
      ```
      (`Ctrl + C`で終了)

4.  **OLED・ファン制御の動作確認**

    ```bash
    sudo systemctl status oled-fan-controller.service
    ```
    - こちらも `active (running)` となっていれば成功です。
    - ケースのOLED画面に、CPU温度などが表示されているはずです。

5.  **Tailscaleの動作確認**

    ```bash
    tailscale ip -4
    ```
    - `100.x.x.x` のようなIPアドレスが表示されれば成功です。

---

---

## 補講: 既存OSへの追加インストール

「すでにRaspberry Piを使っていて、OSもインストール済みだけど、BCNOFNeシステムを追加したい！」

そんなあなたは、ここからスタートです。

> 詳しい手順は、**[📄 既存のRaspberry Pi OSへのSSH有効化＆追加インストールガイド](./EXISTING_OS_GUIDE.md)** を参照してください。

### 要約ステップ

1.  **SSHを有効化する**
    - もしSSHがまだ有効でない場合、上記ガイドに従って有効化してください。
    - **方法A**: モニターとキーボードで `sudo raspi-config` を実行する。
    - **方法B**: PCでmicroSDカードに `ssh` という空ファイルを作成する。

2.  **SSHで接続し、システムを更新する**
    - PCからSSHでRaspberry Piに接続します。
    - `sudo apt update && sudo apt full-upgrade -y` を実行して、システムを最新の状態にします。

3.  **BCNOFNeシステムをインストールする**
    - このガイドの **[第3部: BCNOFNeの進水](#第3部-bcnofneの進水---aiシステムのインストール)** に戻り、ステップ1から順番に実行してください。


## 🧭 これからの航海

あなたのBCNOFNeシステムは、今、静かに自律航行を開始しました。

- **日常の運用**: **[📄 USER_MANUAL.md](./USER_MANUAL.md)** を読んで、AIとの対話方法やシステムの管理方法を学びましょう。
- **LINEやDiscordで通知**を受け取ったり、指示を出したりできます。
- **自己進化**: AIは自らのコードを改善し、日々賢くなっていきます。

**ようこそ、BCNOFNeの船長。あなたの素晴らしい航海が、今ここから始まります！**
