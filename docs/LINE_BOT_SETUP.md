# LINE Botとngrokのセットアップガイド

このガイドでは、LINE Botサーバーとngrokを自動起動するための設定方法を説明します。

## 前提条件

- LINE Developers Consoleでチャンネルを作成済み
- Channel Access Token、Channel Secret、User IDを取得済み
- ngrokアカウントを作成済み（https://dashboard.ngrok.com/signup）
- ngrok authtokenを取得済み

## 1. ngrokのインストールと設定

### ngrokのインストール

```bash
# ngrokをダウンロード
cd /tmp
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz

# 解凍してインストール
sudo tar xvzf ngrok-v3-stable-linux-arm.tgz -C /usr/local/bin
```

### ngrokの認証設定

```bash
# authtokenを設定（YOUR_TOKENを実際のトークンに置き換え）
ngrok config add-authtoken YOUR_TOKEN
```

## 2. systemdサービスの設定

### ngrokサービスの有効化

```bash
# ngrok.serviceをコピー
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/ngrok.service /etc/systemd/system/

# サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable ngrok.service
sudo systemctl start ngrok.service

# 起動確認
sudo systemctl status ngrok.service
```

### LINE Botサービスの有効化

```bash
# line-bot.serviceをコピー
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/line-bot.service /etc/systemd/system/

# サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable line-bot.service
sudo systemctl start line-bot.service

# 起動確認
sudo systemctl status line-bot.service
```

## 3. ngrok URLの取得とWebhook設定

### ngrok URLを確認

```bash
# ngrokのログからURLを確認
sudo journalctl -u ngrok.service -n 50 | grep "started tunnel"
```

または、ngrokのWeb UIで確認：
```
http://localhost:4040
```

### LINE Developers ConsoleでWebhook URLを設定

1. LINE Developers Console（https://developers.line.biz/console/）にアクセス
2. 作成したチャンネルを選択
3. 「Messaging API」タブを開く
4. 「Webhook settings」セクションで以下を設定：
   - Webhook URL: `https://YOUR_NGROK_URL.ngrok-free.app/webhook`
   - Use webhook: 有効化
5. 「Verify」ボタンをクリックして接続確認
6. 「Update」をクリックして保存

## 4. 動作確認

### LINE Botにメッセージを送信

1. スマホのLINEアプリで作成したLINE公式アカウントを友だち追加
2. テストメッセージを送信（例: "こんにちは"）
3. 「📝 指示を受け付けました」と返信が来れば成功

### 目標設定のテスト

LINEで以下のようなメッセージを送信：
```
目標はあなたはルート権限が与えられています。ラズパイ4bにつけてるファンが回らないから回るようにPythonコードを作成することとOLEDも表示できてないから修正すること
```

数秒後に以下の返信が来れば成功：
```
✅ 目標を設定しました:
目標はあなたはルート権限が与えられています。ラズパイ4bにつけてるファンが回らないから回るようにPythonコードを作成することとOLEDも表示できてないから修正すること
```

## 5. ログの確認

### ngrokのログ確認

```bash
sudo journalctl -u ngrok.service -f
```

### LINE Botのログ確認

```bash
sudo journalctl -u line-bot.service -f
```

### メインシステムのログ確認

```bash
sudo journalctl -u autonomous-ai.service -f
```

## 6. トラブルシューティング

### ngrokが起動しない場合

```bash
# authtokenが正しく設定されているか確認
cat ~/.config/ngrok/ngrok.yml

# 手動でngrokを起動してエラーを確認
ngrok http 5000
```

### LINE Botサーバーが起動しない場合

```bash
# 環境変数が正しく設定されているか確認
cat /home/pi/autonomous_ai/.env

# 手動でLINE Botサーバーを起動してエラーを確認
cd /home/pi/autonomous_ai_BCNOFNe_system
source venv/bin/activate
python3 src/line_bot.py
```

### Webhookが動作しない場合

1. ngrok URLが正しく設定されているか確認
2. LINE Developers ConsoleでWebhookが有効化されているか確認
3. ファイアウォールでポート5000が開いているか確認

```bash
# ポート5000が使用されているか確認
sudo netstat -tlnp | grep 5000
```

## 7. 再起動時の自動起動

systemdサービスとして登録されているため、Raspberry Piを再起動しても自動的に起動します。

```bash
# 再起動
sudo reboot

# 再起動後、サービスが起動しているか確認
sudo systemctl status ngrok.service
sudo systemctl status line-bot.service
sudo systemctl status autonomous-ai.service
```

## 8. サービスの停止・無効化

### 一時的な停止

```bash
sudo systemctl stop ngrok.service
sudo systemctl stop line-bot.service
```

### 自動起動の無効化

```bash
sudo systemctl disable ngrok.service
sudo systemctl disable line-bot.service
```

## 注意事項

- ngrokの無料プランは8時間でセッションが切断されます
- 切断後は自動的に再接続されますが、URLが変更されるため、LINE Developers ConsoleでWebhook URLを更新する必要があります
- 本番運用では、固定URLを使用できるngrokの有料プランまたはTailscale + Caddyの使用を推奨します

## 代替案: Tailscale + Caddy

ngrokの無料プランの制限を回避するため、Tailscale + Caddyを使用する方法もあります。詳細は別途ドキュメントを参照してください。
