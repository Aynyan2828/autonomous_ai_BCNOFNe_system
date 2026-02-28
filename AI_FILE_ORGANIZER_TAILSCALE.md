# AI自動ファイル整理 & Tailscale統合 - 技術仕様書

---

## 概要

このドキュメントでは、完全自律型AIシステムに追加された以下の機能について説明します。

1. **AI自動ファイル整理機能** - ファイルの内容を解析して自動分類・整理
2. **Tailscale統合** - 外出先から安全にRaspberry Piにアクセス

---

## 1. AI自動ファイル整理機能

### 1.1 概要

AIがファイルの内容を理解して、自動的に分類・整理する機能です。画像、ドキュメント、音楽、動画などを適切なフォルダに振り分けます。

### 1.2 主な機能

#### ファイルタイプの自動検出

MIMEタイプに基づいて、ファイルを以下のカテゴリに分類します。

| メインカテゴリ | サブカテゴリ | 説明 |
| :--- | :--- | :--- |
| **images** | landscape, people, food, animals, objects, screenshots, other | 画像ファイル |
| **documents** | work, personal, study, finance, receipts, other | ドキュメント |
| **music** | rock, pop, classical, jazz, electronic, other | 音楽ファイル |
| **videos** | movies, tutorials, recordings, other | 動画ファイル |
| **archives** | backups, downloads, other | アーカイブファイル |

#### 画像の自動分類

- **ファイル名解析**: ファイル名から内容を推測
- **スクリーンショット検出**: "screenshot"や"screen"を含むファイルを自動検出

#### ドキュメントの自動分類

- **ファイル名解析**: "invoice", "receipt", "work", "study"などのキーワードを検出
- **テキスト内容解析**: GPT-4を使ってテキストの内容を分類

#### 重複ファイルの検出と削除

- **SHA256ハッシュ**: ファイルのハッシュ値を計算
- **自動削除**: 重複ファイルを検出して自動削除
- **履歴記録**: 削除されたファイルの情報を記録

### 1.3 ファイル構成

```
src/
└── ai_file_organizer.py      # AI自動ファイル整理モジュール

nas/
└── organized/                 # 整理後のディレクトリ
    ├── images/
    │   ├── landscape/
    │   ├── people/
    │   ├── food/
    │   └── ...
    ├── documents/
    │   ├── work/
    │   ├── personal/
    │   └── ...
    └── duplicates.json        # 重複ファイル記録
```

### 1.4 使用例

#### 単一ファイルの整理

```python
from ai_file_organizer import AIFileOrganizer
from pathlib import Path

# 初期化
organizer = AIFileOrganizer(api_key=os.getenv("OPENAI_API_KEY"))

# ファイルを整理
result = organizer.organize_file(Path("/home/pi/Downloads/photo.jpg"))
print(result)
# {
#   "file": "/home/pi/Downloads/photo.jpg",
#   "success": True,
#   "action": "move",
#   "destination": "/home/pi/autonomous_ai/nas/organized/images/landscape/photo.jpg",
#   "category": "images/landscape"
# }
```

#### ディレクトリ全体の整理

```python
# ディレクトリ全体を整理（ドライラン）
stats = organizer.organize_directory(
    target_dir=Path("/home/pi/Downloads"),
    recursive=True,
    dry_run=True  # 実際には移動しない
)

print(stats)
# {
#   "total": 150,
#   "success": 145,
#   "failed": 5,
#   "duplicates": 20,
#   "moved": 125,
#   "categories": {
#     "images/landscape": 30,
#     "documents/work": 25,
#     ...
#   }
# }
```

#### 実際に整理を実行

```python
# ドライランをオフにして実行
stats = organizer.organize_directory(
    target_dir=Path("/home/pi/Downloads"),
    recursive=True,
    dry_run=False  # 実際に移動する
)
```

#### 整理状況の統計を取得

```python
stats = organizer.get_statistics()
print(stats)
# {
#   "total_files": 500,
#   "categories": {
#     "images": {
#       "landscape": 80,
#       "people": 50,
#       ...
#     },
#     "documents": {
#       "work": 100,
#       "personal": 70,
#       ...
#     }
#   },
#   "duplicates_count": 45
# }
```

### 1.5 AIエージェントとの統合

AIエージェントのJSONレスポンスに追加:

```json
{
  "say": "ファイルを整理します",
  "organize_files": {
    "enabled": true,
    "target_dir": "/home/pi/Downloads",
    "dry_run": false
  }
}
```

### 1.6 自動整理スケジュール

定期的に自動整理を実行する設定:

```bash
# cronで毎日午前3時に実行
0 3 * * * python3 /home/pi/autonomous_ai/src/ai_file_organizer.py
```

---

## 2. Tailscale統合

### 2.1 概要

Tailscaleを統合することで、外出先からRaspberry Piに安全にアクセスできます。VPN不要でプライベートネットワークを構築します。

### 2.2 主な機能

#### Tailscaleのインストール

```python
from tailscale_manager import TailscaleManager

manager = TailscaleManager()

# インストール
if manager.install():
    print("✅ インストール完了")
```

#### Tailscaleの起動

```python
# 起動（初回は認証が必要）
if manager.start():
    print("✅ 起動完了")

# IPアドレスを取得
ip_address = manager.get_ip_address()
print(f"Tailscale IP: {ip_address}")
```

#### ステータスの取得

```python
status = manager.get_status()
print(status)
# {
#   "installed": True,
#   "running": True,
#   "ip_address": "100.x.x.x",
#   "hostname": "raspberry-pi",
#   "peers": 3
# }
```

#### 接続されているピアの一覧

```python
peers = manager.get_peers()
for peer in peers:
    print(f"{peer['hostname']} ({peer['ip_address']}) - {'オンライン' if peer['online'] else 'オフライン'}")
```

#### Exit Nodeの有効化

```python
# Raspberry PiをExit Nodeとして使用
if manager.enable_exit_node():
    print("✅ Exit Node有効化")
```

#### Tailscale SSHの有効化

```python
# Tailscale経由でSSH接続を有効化
if manager.enable_ssh():
    print("✅ SSH有効化")
```

### 2.3 ファイル構成

```
src/
└── tailscale_manager.py       # Tailscale管理モジュール

scripts/
└── install_tailscale.sh       # Tailscaleインストールスクリプト

tailscale_config.json          # Tailscale設定ファイル
```

### 2.4 インストール手順

#### 方法1: インストールスクリプトを使用

```bash
cd /home/pi/autonomous_ai/scripts
sudo ./install_tailscale.sh
```

スクリプトが以下を自動的に実行します:
1. Tailscaleのダウンロード
2. インストール
3. 起動（オプション）
4. ステータス表示

#### 方法2: Pythonモジュールを使用

```python
from tailscale_manager import TailscaleManager

manager = TailscaleManager()

# インストール
manager.install()

# 起動
manager.start()

# ステータス確認
status = manager.get_status()
print(f"Tailscale IP: {status['ip_address']}")
```

### 2.5 外出先からのアクセス方法

#### SSH接続

```bash
# Tailscale IPアドレスを使用
ssh pi@100.x.x.x
```

#### NASへのアクセス

```bash
# Sambaを使用
smb://100.x.x.x/nas
```

#### LINE Botからの操作

外出先からLINE Botを使ってAIに指示を送信できます:

```
「ファイルを整理して」
「システムの状態を教えて」
「温度は何度?」
```

### 2.6 セキュリティ

Tailscaleは以下のセキュリティ機能を提供します:

- ✅ **エンドツーエンド暗号化** - すべての通信が暗号化
- ✅ **ゼロトラストネットワーク** - デバイスごとに認証
- ✅ **ファイアウォール不要** - NAT越えを自動処理
- ✅ **アクセス制御** - デバイスごとにアクセス権限を設定

### 2.7 AIエージェントとの統合

AIエージェントのJSONレスポンスに追加:

```json
{
  "say": "Tailscaleの状態を確認します",
  "tailscale": {
    "action": "status"
  }
}
```

利用可能なアクション:
- `status`: ステータスを取得
- `start`: 起動
- `stop`: 停止
- `get_ip`: IPアドレスを取得
- `get_peers`: ピア一覧を取得

---

## 3. システム統合

### 3.1 AIエージェントとの統合

新しい機能はAIエージェントのコアシステムに統合されています。

#### AI自動ファイル整理の利用

```python
# agent_core.py内
from ai_file_organizer import AIFileOrganizer

class AutonomousAgent:
    def __init__(self):
        # ...
        self.file_organizer = AIFileOrganizer(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def organize_files(self, target_dir: str, dry_run: bool = False):
        """ファイルを整理"""
        stats = self.file_organizer.organize_directory(
            target_dir=Path(target_dir),
            dry_run=dry_run
        )
        return stats
```

#### Tailscaleの利用

```python
# agent_core.py内
from tailscale_manager import TailscaleManager

class AutonomousAgent:
    def __init__(self):
        # ...
        self.tailscale = TailscaleManager()
    
    def get_tailscale_status(self):
        """Tailscaleの状態を取得"""
        return self.tailscale.get_status()
```

### 3.2 LINE Botとの連携

外出先からLINE Botを使って操作:

```python
# line_bot.py内
@app.route("/webhook", methods=["POST"])
def webhook():
    # ...
    
    if "ファイル整理" in message:
        # ファイルを整理
        stats = agent.organize_files("/home/pi/Downloads")
        reply = f"ファイルを整理しました: {stats['moved']}個移動"
    
    elif "Tailscale" in message:
        # Tailscaleの状態を取得
        status = agent.get_tailscale_status()
        reply = f"Tailscale IP: {status['ip_address']}"
```

### 3.3 自動化

#### 定期的なファイル整理

```bash
# cronで毎日午前3時に実行
0 3 * * * python3 /home/pi/autonomous_ai/src/ai_file_organizer.py
```

#### Tailscaleの自動起動

systemdサービスとして登録:

```bash
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
```

---

## 4. パフォーマンスと制限

### 4.1 パフォーマンス

| 機能 | 処理時間 | メモリ使用量 |
| :--- | :--- | :--- |
| AI自動ファイル整理（1ファイル） | 〜2秒 | 〜100MB |
| AI自動ファイル整理（100ファイル） | 〜3分 | 〜150MB |
| Tailscale起動 | 〜10秒 | 〜50MB |
| Tailscaleステータス取得 | 〜1秒 | 〜10MB |

### 4.2 制限

- **OpenAI API**: テキスト分類にOpenAI APIを使用するため、APIキーが必要です。
- **Tailscaleアカウント**: Tailscaleを使用するには、無料アカウントが必要です。
- **ディスク容量**: ファイル整理にディスク容量が必要です。

---

## 5. トラブルシューティング

### 5.1 AI自動ファイル整理

#### ファイルが移動されない

```bash
# ドライランで確認
python3 src/ai_file_organizer.py

# ログを確認
journalctl -u autonomous-ai.service -f
```

#### 重複ファイルが削除されない

```bash
# 重複ファイル記録を確認
cat /home/pi/autonomous_ai/nas/organized/duplicates.json
```

### 5.2 Tailscale

#### Tailscaleが起動しない

```bash
# ステータスを確認
sudo tailscale status

# ログを確認
sudo journalctl -u tailscaled -f
```

#### 認証エラー

```bash
# 再認証
sudo tailscale up
```

#### IPアドレスが取得できない

```bash
# IPアドレスを確認
tailscale ip -4
```

---

## 6. 今後の拡張案

### 6.1 AI自動ファイル整理

- ✅ GPT-4 Visionを使った画像の高度な分類
- ✅ 音声ファイルの自動文字起こしと分類
- ✅ 動画ファイルのサムネイル生成と分類
- ✅ 自動タグ付け機能

### 6.2 Tailscale

- ✅ Tailscale Funnel（公開Webサーバー）
- ✅ Tailscale Serve（プライベートWebサーバー）
- ✅ MagicDNS（ホスト名でアクセス）
- ✅ ACL（アクセス制御リスト）

---

**以上で、AI自動ファイル整理 & Tailscale統合の技術仕様書は終わりです。**
