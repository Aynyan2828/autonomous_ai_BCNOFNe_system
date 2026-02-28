# ホットフィックス v2.2

## 更新日: 2026年2月23日

## 修正内容

### 問題: LINEコマンド読み取りエラー「name 'json' is not defined」

**症状**:
- ログに繰り返し以下のエラーが表示される：
  ```
  [ERROR] LINEコマンド読み取りエラー: name 'json' is not defined
  ```
- LINEから送信したコマンドが読み取れない
- AIが新しい目標を受け取れない

**原因**:
- `main.py`の`check_line_commands`メソッドで`json`モジュールを使用しているが、インポートされていない
- v2.1で`check_line_commands`メソッドを追加した際に、`json`モジュールのインポートを忘れていた

**修正内容**:

### main.pyにjsonモジュールのインポートを追加

**修正前**:
```python
import os
import sys
import time
import signal
from datetime import datetime
from typing import Optional
```

**修正後**:
```python
import os
import sys
import time
import signal
import json
from datetime import datetime
from typing import Optional
```

**変更ファイル**: `src/main.py`

---

## アップグレード方法

### 既存システムからのアップグレード

```bash
# 既存システムを停止
sudo systemctl stop autonomous-ai.service

# ファイルをバックアップ
cp -r /home/pi/autonomous_ai_BCNOFNe_system /home/pi/autonomous_ai_BCNOFNe_system.backup

# 新しいファイルで上書き
cd /home/pi
unzip autonomous_ai_system_v2_2_json_fix.zip
cd autonomous_ai_BCNOFNe_system

# .envファイルをコピー（既存の設定を維持）
cp /home/pi/autonomous_ai/.env .env

# システムを再起動
sudo systemctl daemon-reload
sudo systemctl start autonomous-ai.service
```

---

## 動作確認

### 1. エラーログが消えたことを確認

```bash
sudo journalctl -u autonomous-ai.service -n 100 -f
```

以下のエラーが表示されなくなることを確認：
```
[ERROR] LINEコマンド読み取りエラー: name 'json' is not defined
```

### 2. LINEで目標設定が動作することを確認

LINEで以下のメッセージを送信：
```
ラズパイのCPU温度を確認して
```

数秒後に以下の返信が来ることを確認：
```
📝 指示を受け付けました
```

### 3. Discordで新しい目標が表示されることを確認

Discordの`#ai-notifications`チャンネルで以下の通知が来ることを確認：
```
📨 LINEから新しい目標を受信:
ラズパイのCPU温度を確認して
```

### 4. AIが新しい目標を実行することを確認

数分後、Discordで実行ログが送信されることを確認：
```
📊 実行ログ #XX

目標: ラズパイのCPU温度を確認して

🧠 AIの思考:
vcgencmdコマンドを使用してCPU温度を取得する

実行コマンド:
```bash
vcgencmd measure_temp
```

実行結果:
✅ 成功: 1 / ❌ 失敗: 0
```

---

## トラブルシューティング

### まだエラーが表示される場合

```bash
# Pythonのキャッシュをクリア
cd /home/pi/autonomous_ai_BCNOFNe_system
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# システムを再起動
sudo systemctl restart autonomous-ai.service
```

### LINEコマンドが読み取れない場合

```bash
# コマンドファイルのパスを確認
ls -la /home/pi/autonomous_ai/commands/

# コマンドファイルの内容を確認
cat /home/pi/autonomous_ai/commands/user_commands.jsonl
```

---

## 変更ファイル一覧

- `src/main.py`: `json`モジュールのインポートを追加

---

## 既知の問題

### 1. AIが存在しないファイルを操作しようとする

**症状**:
```
head: 'draft_explanation_candidates_20260223_193135.txt' を 読み込み用に開くことが出来ません: そのようなファイルやディレクトリはありません
```

**原因**: 古い目標が残っている

**対処法**:
```bash
# 目標をリセット
cd /home/pi/autonomous_ai_BCNOFNe_system
python3 << EOF
from agent_core import AutonomousAgent
from memory import MemoryManager

memory = MemoryManager()
agent = AutonomousAgent(memory)
agent.current_goal = "システムの状態を確認する"
memory.save_state(agent.current_goal)
EOF

# システムを再起動
sudo systemctl restart autonomous-ai.service
```

### 2. awkコマンドが許可されていない

**症状**:
```
安全性チェック失敗: 許可されていないコマンド: awk
```

**原因**: `executor.py`のホワイトリストに`awk`が含まれていない

**対処法**: 次回アップデートで`awk`, `sed`, `cut`などの基本的なテキスト処理コマンドを許可リストに追加予定

---

## 次回アップデート予定

- `executor.py`の許可コマンドリストに`awk`, `sed`, `cut`などを追加
- 目標リセット機能の追加
- LINE Bot SDK v3への移行
- より詳細な実行ログ（コマンド出力の一部を含める）

---

## v2.0からの変更履歴

- **v2.0**: LINE Bot自動起動、Discord通知詳細化、LINEコマンド受信機能
- **v2.1**: 無限ループ問題修正、起動通知重複防止
- **v2.2**: LINEコマンド読み取りエラー修正（jsonモジュールインポート追加）
