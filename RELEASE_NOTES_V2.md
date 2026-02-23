# リリースノート v2.0

## 更新日: 2026年2月23日

## 主な変更点

### 1. LINE Bot自動起動機能の追加

**問題**: LINE Botサーバーが手動起動のみで、システム再起動時に自動起動しない

**解決策**:
- `systemd/line-bot.service`を追加
- LINE Botサーバーがsystemdサービスとして自動起動
- ngrokとの連携により、Webhookが常時動作

**ファイル**:
- `systemd/line-bot.service` (新規)
- `docs/LINE_BOT_SETUP.md` (新規)

### 2. ngrok自動起動機能の追加

**問題**: Webhookに必要な公開HTTPS URLを手動で設定する必要がある

**解決策**:
- `systemd/ngrok.service`を追加
- ngrokがsystemdサービスとして自動起動
- LINE Bot Webhookへの公開アクセスが可能

**ファイル**:
- `systemd/ngrok.service` (新規)

### 3. Discord通知の詳細度向上

**問題**: Discordログが「実行コマンド: なし」「成功: 0 / 失敗: 0」と表示され、AIが何をしているのか不明

**解決策**:
- `discord_notifier.py`の`send_execution_log`メソッドに`thinking`パラメータを追加
- AIの思考プロセス（`say`フィールド）を表示
- 実際に実行したコマンドと結果を表示

**変更ファイル**:
- `src/discord_notifier.py`
- `src/agent_core.py`
- `src/main.py`

**改善例**:
```
📊 実行ログ #30

目標: 抽出した不整合・抜け漏れ詳細を解析し、改善案抽出元データとの突合を進める。

🧠 AIの思考:
filtered_analysis.txtの内容を解析し、正規表現ごとに改善案詳細を構造化して具体的実施策リストの原案を作成する。

実行コマンド:
```bash
cat /path/to/filtered_analysis.txt
```

実行結果:
✅ 成功: 1 / ❌ 失敗: 0
```

### 4. LINEからのコマンド受信機能の統合

**問題**: LINEで目標設定しても返事がなく、システムが反応しない

**解決策**:
- `main.py`に`check_line_commands`メソッドを追加
- LINEから送信されたメッセージを`/home/pi/autonomous_ai/commands/user_commands.jsonl`から読み取り
- エージェントの目標（`current_goal`）を自動更新
- 確認通知をLINEとDiscordに送信

**変更ファイル**:
- `src/main.py`

**動作フロー**:
1. ユーザーがLINEでメッセージを送信
2. LINE Botサーバーが受信して`user_commands.jsonl`に保存
3. メインシステムが定期的に`user_commands.jsonl`をチェック
4. 新しいコマンドがあれば目標を更新
5. 確認通知をLINEとDiscordに送信

### 5. .env読み込み処理の修正

**問題**: `line_bot.py`が環境変数を読み込めず、`ValueError: LINE認証情報が設定されていません`エラーが発生

**解決策**:
- `line_bot.py`に`load_dotenv()`を追加
- `.env`ファイルのパスを自動検出
- 代替パス（`/home/pi/autonomous_ai/.env`）もサポート

**変更ファイル**:
- `src/line_bot.py`

### 6. Webhookエンドポイントの統一

**問題**: `line_bot.py`のエンドポイントが`/callback`だが、ngrokのスクリーンショットでは`/webhook`にリクエストが来ている

**解決策**:
- エンドポイントを`/webhook`に統一

**変更ファイル**:
- `src/line_bot.py`

### 7. エージェント実行履歴の保存

**問題**: エージェントの実行内容が通知に含まれていない

**解決策**:
- `agent_core.py`に実行履歴を保存する属性を追加
  - `last_commands`: 実行したコマンドのリスト
  - `last_results`: 実行結果のリスト
  - `last_thinking`: AIの思考プロセス
  - `last_action`: 最後のアクション

**変更ファイル**:
- `src/agent_core.py`

## インストール方法

### 新規インストール

1. ZIPファイルを解凍
2. `INSTALL_GUIDE.md`に従ってインストール
3. `docs/LINE_BOT_SETUP.md`に従ってLINE Botとngrokをセットアップ

### 既存システムからのアップグレード

```bash
# 既存システムを停止
sudo systemctl stop autonomous-ai.service

# ファイルをバックアップ
cp -r /home/pi/autonomous_ai_BCNOFNe_system /home/pi/autonomous_ai_BCNOFNe_system.backup

# 新しいファイルで上書き
cd /home/pi
unzip autonomous_ai_system_v2_with_linebot.zip
cd autonomous_ai_BCNOFNe_system

# .envファイルをコピー（既存の設定を維持）
cp /home/pi/autonomous_ai/.env .env

# LINE Botとngrokのセットアップ
# docs/LINE_BOT_SETUP.mdを参照

# システムを再起動
sudo systemctl daemon-reload
sudo systemctl start autonomous-ai.service
sudo systemctl start ngrok.service
sudo systemctl start line-bot.service
```

## 動作確認

### 1. システムが起動しているか確認

```bash
sudo systemctl status autonomous-ai.service
sudo systemctl status ngrok.service
sudo systemctl status line-bot.service
```

### 2. Discordで詳細ログを確認

Discordの`#ai-notifications`チャンネルで以下のような詳細ログが表示されることを確認：

```
📊 実行ログ #30

目標: システムの状態確認

🧠 AIの思考:
システムのディスク使用量とメモリ使用量を確認する

実行コマンド:
```bash
df -h
```

実行結果:
✅ 成功: 1 / ❌ 失敗: 0
```

### 3. LINEで目標設定をテスト

LINEで以下のメッセージを送信：
```
ラズパイのCPU温度を確認して
```

数秒後に以下の返信が来ることを確認：
```
✅ 目標を設定しました:
ラズパイのCPU温度を確認して
```

Discordでも以下の通知が来ることを確認：
```
📨 LINEから新しい目標を受信:
ラズパイのCPU温度を確認して
```

## トラブルシューティング

詳細は`docs/LINE_BOT_SETUP.md`の「トラブルシューティング」セクションを参照してください。

## 既知の問題

- ngrokの無料プランは8時間でセッションが切断されます。切断後は自動的に再接続されますが、URLが変更されるため、LINE Developers ConsoleでWebhook URLを更新する必要があります。
- LINE Bot SDK v2を使用していますが、v3への移行が推奨されています（非推奨警告が表示されます）。

## 今後の改善予定

- LINE Bot SDK v3への移行
- Tailscale + Caddyによる固定URL対応
- Webhookの自動URL更新機能
- より詳細な実行ログ（コマンド出力の一部を含める）

## サポート

問題が発生した場合は、以下のログを確認してください：

```bash
# メインシステムのログ
sudo journalctl -u autonomous-ai.service -n 100

# LINE Botのログ
sudo journalctl -u line-bot.service -n 100

# ngrokのログ
sudo journalctl -u ngrok.service -n 100
```

## ライセンス

MIT License（詳細は`LICENSE`ファイルを参照）
