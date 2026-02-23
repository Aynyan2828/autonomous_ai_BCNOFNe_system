# LINE Bot制御機能セットアップガイド

このガイドでは、LINEからAIエージェントを「停止」「再開」できるようにする設定を説明します。

## 概要

LINE Botサーバーを独立したプロセスとして動作させ、LINEからのコマンドでAIエージェントを制御できるようにします。

### 対応コマンド

| コマンド | 動作 |
|---------|------|
| `停止`, `ストップ`, `stop` | AIエージェントを停止 |
| `再開`, `起動`, `start` | AIエージェントを起動 |
| `状態`, `ステータス`, `status` | AIエージェントの状態を確認 |

---

## セットアップ手順

### 1. sudoers設定のインストール

piユーザーがパスワードなしで`systemctl`コマンドを実行できるようにします。

```bash
# sudoers設定ファイルをコピー
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/autonomous-ai-sudoers /etc/sudoers.d/autonomous-ai

# 権限を設定
sudo chmod 0440 /etc/sudoers.d/autonomous-ai

# 構文チェック
sudo visudo -c -f /etc/sudoers.d/autonomous-ai
```

**重要**: 構文エラーがある場合は、システムにログインできなくなる可能性があります。必ず`visudo -c`で確認してください。

---

### 2. LINE Botサーバーの更新

修正済みの`line_bot.py`を配置します。

```bash
# 既存のLINE Botサーバーを停止
sudo systemctl stop line-bot.service

# 新しいファイルで上書き
cp /home/pi/autonomous_ai_BCNOFNe_system/src/line_bot.py /home/pi/autonomous_ai/src/

# LINE Botサーバーを再起動
sudo systemctl start line-bot.service

# 状態確認
sudo systemctl status line-bot.service
```

---

### 3. 動作確認

#### 3-1. 状態確認

LINEで「状態」と送信して、現在の状態を確認します。

**期待される返信**:
```
✅ AIエージェント: 稼働中

停止するには「停止」と送信してください。
```

#### 3-2. 停止テスト

LINEで「停止」と送信します。

**期待される返信**:
```
⏹️ AIエージェントを停止しました

再開するには「再開」と送信してください。
```

Discordで停止通知が送信されることを確認します。

#### 3-3. 再開テスト

LINEで「再開」と送信します。

**期待される返信**:
```
🚀 AIエージェントを起動しました

数秒後に動作を開始します。
```

Discordで起動通知が送信されることを確認します。

---

## トラブルシューティング

### エラー: 「sudo: a password is required」

**原因**: sudoers設定が正しくインストールされていません。

**解決策**:
```bash
# sudoers設定を再インストール
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/autonomous-ai-sudoers /etc/sudoers.d/autonomous-ai
sudo chmod 0440 /etc/sudoers.d/autonomous-ai
sudo visudo -c -f /etc/sudoers.d/autonomous-ai
```

### エラー: 「停止に失敗しました」

**原因**: AIエージェントサービスが存在しないか、既に停止しています。

**解決策**:
```bash
# サービスの状態を確認
sudo systemctl status autonomous-ai.service

# サービスが存在しない場合はインストール
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/autonomous-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable autonomous-ai.service
```

### LINE Botサーバーが起動しない

**原因**: 環境変数が正しく設定されていません。

**解決策**:
```bash
# .envファイルを確認
cat /home/pi/autonomous_ai/.env

# 以下の変数が設定されているか確認
# LINE_CHANNEL_ACCESS_TOKEN
# LINE_CHANNEL_SECRET
# LINE_TARGET_USER_ID
```

---

## セキュリティ上の注意

1. **sudoers設定は最小限の権限のみ付与**
   - `autonomous-ai.service`の操作のみ許可
   - 他のサービスや`sudo su`などは許可していません

2. **LINE Botサーバーは常時稼働**
   - Webhookを受信するため、常に動作している必要があります
   - AIエージェントのみ停止/起動できます

3. **ngrokのセキュリティ**
   - ngrokの無料プランは8時間で切断されます
   - 有料プランまたはTailscaleの使用を推奨します

---

## よくある質問

### Q: LINE Botサーバーも停止できますか？

A: できますが、推奨しません。LINE Botサーバーを停止すると、LINEからのコマンドを受信できなくなります。

### Q: 複数のユーザーから制御できますか？

A: 現在は`LINE_TARGET_USER_ID`に設定されたユーザーのみです。複数ユーザー対応は今後のアップデートで実装予定です。

### Q: Discord Botでも同じことができますか？

A: 可能です。同様の仕組みをDiscord Botにも実装できます。

---

## 次のステップ

- [メモリ管理ガイド](MEMORY_MANAGEMENT.md)
- [コスト管理ガイド](COST_MANAGEMENT.md)
- [トラブルシューティング](TROUBLESHOOTING.md)
