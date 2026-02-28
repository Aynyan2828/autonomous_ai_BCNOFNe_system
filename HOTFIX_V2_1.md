# ホットフィックス v2.1

## 更新日: 2026年2月23日

## 修正内容

### 問題: システム起動通知と実行ログ#1が無限ループで送信される

**症状**:
- Discordに「システム起動」と「実行ログ #1」が延々と送信される
- LINEにも同様の通知が繰り返し送信される

**原因**:

1. **line_bot.pyのテストコードが実行されていた**
   - systemdサービスで`python3 line_bot.py`を実行すると、`if __name__ == "__main__"`ブロックが実行される
   - このブロックで起動通知と実行ログ#1を送信してから終了
   - systemdの`Restart=always`設定により、終了後すぐに再起動
   - 結果として無限ループが発生

2. **check_line_commandsが重複呼び出しされていた**
   - `run_iteration_with_monitoring`内（159行目）
   - `run`メソッド内（296行目）
   - 両方で呼び出されていたため、重複チェックが発生

3. **起動通知の重複防止機能がなかった**
   - systemdサービスが再起動されるたびに起動通知が送信される
   - 短時間に複数回起動通知が送信される可能性

**修正内容**:

### 1. line_bot.pyのテストコードをWebhookサーバー起動に変更

**修正前**:
```python
# テスト用
if __name__ == "__main__":
    bot = LINEBot()
    
    # テスト送信
    print("起動通知を送信...")
    bot.send_startup_notification()
    
    print("実行ログを送信...")
    bot.send_execution_log(
        iteration=1,
        goal="システムの状態確認",
        commands=["ls -la", "df -h"],
        results=[{"success": True}, {"success": True}]
    )
    
    print("テスト完了")
```

**修正後**:
```python
# Webhookサーバー起動
if __name__ == "__main__":
    print("LINE Bot Webhookサーバーを起動します...")
    print("ポート: 5000")
    print("Ctrl+Cで停止")
    
    # 環境変数から認証情報を取得
    bot = LINEBot()
    
    # Webhookサーバー起動
    bot.run_webhook_server(host="0.0.0.0", port=5000)
```

**変更ファイル**: `src/line_bot.py`

### 2. check_line_commandsの重複呼び出しを削除

**修正前**:
```python
while self.running:
    try:
        # LINEコマンドチェック
        self.check_line_commands()
        
        # イテレーション実行
        self.run_iteration_with_monitoring()
```

**修正後**:
```python
while self.running:
    try:
        # イテレーション実行（LINEコマンドチェックも含む）
        self.run_iteration_with_monitoring()
```

**変更ファイル**: `src/main.py`

### 3. 起動通知の重複防止機能を追加

**新規ファイル**: `src/startup_flag.py`

起動フラグを管理するクラスを追加：
- 最後の起動通知送信時刻を記録
- 5分以内に再度起動通知が送信されないようにする
- systemdサービスの再起動時にも重複通知を防止

**変更ファイル**: `src/main.py`

```python
def send_startup_notifications(self):
    """起動通知を送信（重複防止付き）"""
    # 起動フラグチェック
    startup_flag = StartupFlag("/home/pi/autonomous_ai/.startup_flag")
    
    if not startup_flag.should_send_startup_notification(cooldown_minutes=5):
        print("起動通知は最近5分以内に送信済みです。スキップします。")
        return
    
    print("起動通知を送信中...")
    
    # Discord通知
    self.discord.send_startup_notification()
    
    # LINE通知
    self.line.send_startup_notification()
    
    # 課金サマリーも送信
    summary = self.billing.get_summary()
    self.discord.send_message(f"```\n{summary}\n```")
    self.line.send_message(summary)
```

## アップグレード方法

### 既存システムからのアップグレード

```bash
# 既存システムを停止
sudo systemctl stop autonomous-ai.service
sudo systemctl stop line-bot.service

# ファイルをバックアップ
cp -r /home/pi/autonomous_ai_BCNOFNe_system /home/pi/autonomous_ai_BCNOFNe_system.backup

# 新しいファイルで上書き
cd /home/pi
unzip autonomous_ai_system_v2_1_fixed.zip
cd autonomous_ai_BCNOFNe_system

# .envファイルをコピー（既存の設定を維持）
cp /home/pi/autonomous_ai/.env .env

# システムを再起動
sudo systemctl daemon-reload
sudo systemctl start autonomous-ai.service
sudo systemctl start line-bot.service
```

## 動作確認

### 1. LINE Botサーバーが正常に起動しているか確認

```bash
sudo systemctl status line-bot.service
```

以下のようなログが表示されれば成功：
```
● line-bot.service - LINE Bot Webhook Server
   Active: active (running)
   ...
   LINE Bot Webhookサーバーを起動します...
   ポート: 5000
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:5000
```

### 2. 起動通知が1回だけ送信されることを確認

Discordの`#ai-notifications`チャンネルで、起動通知が1回だけ送信されることを確認。

### 3. 実行ログが正常に送信されることを確認

10回に1回、実行ログが送信されることを確認（イテレーション #10, #20, #30...）。

### 4. LINEで目標設定が動作することを確認

LINEで以下のメッセージを送信：
```
ラズパイのCPU温度を確認して
```

数秒後に以下の返信が来ることを確認：
```
✅ 目標を設定しました:
ラズパイのCPU温度を確認して
```

## トラブルシューティング

### LINE Botサーバーが起動しない場合

```bash
# ログを確認
sudo journalctl -u line-bot.service -n 50

# 手動で起動してエラーを確認
cd /home/pi/autonomous_ai_BCNOFNe_system
source venv/bin/activate
python3 src/line_bot.py
```

### 起動通知が送信されない場合

```bash
# 起動フラグファイルを削除
rm /home/pi/autonomous_ai/.startup_flag

# システムを再起動
sudo systemctl restart autonomous-ai.service
```

### 実行ログが送信されない場合

```bash
# メインシステムのログを確認
sudo journalctl -u autonomous-ai.service -n 100
```

## 変更ファイル一覧

- `src/line_bot.py`: テストコードをWebhookサーバー起動に変更
- `src/main.py`: check_line_commandsの重複呼び出しを削除、起動フラグチェックを追加
- `src/startup_flag.py`: 起動フラグ管理クラスを新規追加

## 既知の問題

なし

## 次回アップデート予定

- LINE Bot SDK v3への移行
- Tailscale + Caddyによる固定URL対応
- より詳細な実行ログ（コマンド出力の一部を含める）
