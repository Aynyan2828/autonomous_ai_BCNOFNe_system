# リリースノート v2.3 - LINE制御機能追加

**リリース日**: 2026年2月23日  
**バージョン**: v2.3 (LINE Control Update)

---

## 🎯 主な新機能

### LINEからAIエージェントを制御

LINEから以下のコマンドでAIエージェントを停止・再開できるようになりました。

| コマンド | 動作 | 返信例 |
|---------|------|--------|
| `停止`, `ストップ`, `stop` | AIエージェントを停止 | ⏹️ AIエージェントを停止しました |
| `再開`, `起動`, `start` | AIエージェントを起動 | 🚀 AIエージェントを起動しました |
| `状態`, `ステータス`, `status` | 状態を確認 | ✅ AIエージェント: 稼働中 |

**使用例**:
1. LINEで「停止」と送信 → AIエージェントが停止
2. LINEで「再開」と送信 → AIエージェントが起動
3. LINEで「状態」と送信 → 現在の状態を確認

---

## 🔧 技術的な変更

### 1. LINE Botサーバーの独立化

**変更前**:
- AIエージェントとLINE Botが同じプロセスで動作
- AIを停止するとLINE Botも停止

**変更後**:
- LINE Botサーバーが独立したsystemdサービスとして常時稼働
- AIエージェントのみ停止・起動可能
- LINEからのコマンドをいつでも受信可能

### 2. sudoers設定の追加

piユーザーがパスワードなしで`systemctl`コマンドを実行できるようになりました。

**許可されたコマンド**:
- `sudo systemctl start autonomous-ai.service`
- `sudo systemctl stop autonomous-ai.service`
- `sudo systemctl restart autonomous-ai.service`
- `sudo systemctl status autonomous-ai.service`

**セキュリティ**:
- `autonomous-ai.service`の操作のみ許可
- 他のサービスや`sudo su`などは許可していません

### 3. line_bot.pyの機能追加

**追加されたメソッド**:
- `_stop_ai_service()`: AIエージェントを停止
- `_start_ai_service()`: AIエージェントを起動
- `_check_ai_service_status()`: 状態を確認

**変更されたメソッド**:
- `handle_message()`: 特別なコマンドを処理

---

## 📦 新規ファイル

| ファイル | 説明 |
|---------|------|
| `systemd/autonomous-ai-sudoers` | sudoers設定ファイル |
| `docs/LINE_CONTROL_SETUP.md` | LINE制御機能のセットアップガイド |
| `RELEASE_NOTES_V2_3.md` | このリリースノート |

---

## 🚀 アップグレード方法

### 既存システムからのアップグレード

```bash
# システムを停止
sudo systemctl stop autonomous-ai.service
sudo systemctl stop line-bot.service

# 新しいファイルで上書き
cd /home/pi
unzip -o autonomous_ai_system_v2_3_line_control.zip

# .envファイルを維持
cp /home/pi/autonomous_ai/.env /home/pi/autonomous_ai_BCNOFNe_system/.env

# sudoers設定をインストール
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/autonomous-ai-sudoers /etc/sudoers.d/autonomous-ai
sudo chmod 0440 /etc/sudoers.d/autonomous-ai
sudo visudo -c -f /etc/sudoers.d/autonomous-ai

# systemdサービスを更新
sudo cp /home/pi/autonomous_ai_BCNOFNe_system/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# サービスを起動
sudo systemctl start line-bot.service
sudo systemctl start autonomous-ai.service

# 状態確認
sudo systemctl status line-bot.service
sudo systemctl status autonomous-ai.service
```

### 新規インストール

`docs/LINE_CONTROL_SETUP.md`を参照してください。

---

## ✅ 動作確認

### 1. 状態確認

LINEで「状態」と送信:

**期待される返信**:
```
✅ AIエージェント: 稼働中

停止するには「停止」と送信してください。
```

### 2. 停止テスト

LINEで「停止」と送信:

**期待される返信**:
```
⏹️ AIエージェントを停止しました

再開するには「再開」と送信してください。
```

Discordで停止通知が送信されることを確認。

### 3. 再開テスト

LINEで「再開」と送信:

**期待される返信**:
```
🚀 AIエージェントを起動しました

数秒後に動作を開始します。
```

Discordで起動通知が送信されることを確認。

---

## 🐛 修正されたバグ

- **v2.2**: LINEで「停止」と送信しても、目標として設定されるだけで停止しなかった
- **v2.1**: システム起動通知が無限ループで送信される
- **v2.0**: LINEコマンド読み取りエラー（jsonモジュール未インポート）

---

## 📚 ドキュメント

- [LINE制御機能セットアップガイド](docs/LINE_CONTROL_SETUP.md)
- [LINE Botセットアップガイド](docs/LINE_BOT_SETUP.md)
- [インストールガイド](INSTALL_GUIDE.md)
- [ユーザーマニュアル](USER_MANUAL.md)

---

## 🔮 今後の予定

- [ ] Discord Botによる制御機能（ユーザーリクエストにより中止）
- [ ] 複数ユーザー対応
- [ ] Webhookのセキュリティ強化
- [ ] スケジュール実行機能

---

## 🙏 謝辞

このアップデートは、ユーザーからのフィードバックに基づいて実装されました。ありがとうございます！

---

## 📝 変更履歴

- **v2.3**: LINE制御機能追加
- **v2.2**: LINEコマンド読み取りエラー修正
- **v2.1**: 無限ループ問題修正
- **v2.0**: LINE Bot自動起動、Discord通知詳細化
- **v1.0**: 初回リリース
