# 高度な機能 - 技術仕様書

---

## 概要

このドキュメントでは、完全自律型AIシステムに追加された高度な機能について説明します。

---

## 1. ベクトルデータベース（ChromaDB / FAISS）

### 1.1 概要

AIエージェントの長期記憶を強化するため、ベクトルデータベースを導入しました。テキストを埋め込みベクトルに変換し、意味的な類似検索を可能にします。

### 1.2 サポートするデータベース

| データベース | 特徴 | 用途 |
| :--- | :--- | :--- |
| **ChromaDB** | 永続化、メタデータフィルタ | 汎用的な長期記憶 |
| **FAISS** | 高速検索、大規模データ | 大量のドキュメント検索 |

### 1.3 主な機能

#### 埋め込み生成

OpenAIの`text-embedding-3-small`モデルを使用して、テキストを1536次元のベクトルに変換します。

```python
from vector_db import VectorDatabase

db = VectorDatabase(db_type="chromadb", api_key="YOUR_API_KEY")
embedding = db.generate_embedding("Raspberry Piについて")
```

#### ドキュメント追加

```python
db.add(
    text="Raspberry Piは小型のシングルボードコンピュータです。",
    metadata={"category": "hardware", "source": "manual"}
)
```

#### 類似検索

```python
results = db.search("コンピュータについて教えて", n_results=5)
for r in results:
    print(f"{r['text']} (距離: {r['distance']:.4f})")
```

### 1.4 ファイル構成

```
src/
└── vector_db.py          # ベクトルデータベース統合モジュール
```

### 1.5 使用例

#### ChromaDBを使った長期記憶

```python
from vector_db import VectorDatabase

# 初期化
db = VectorDatabase(
    db_type="chromadb",
    db_dir="/home/pi/autonomous_ai/vector_db",
    api_key=os.getenv("OPENAI_API_KEY")
)

# 過去の経験を保存
db.add("2024年2月21日、ファン制御システムを実装した", {"type": "experience"})
db.add("CPU温度が70°C以上になると警告を送信する", {"type": "knowledge"})

# 関連する記憶を検索
results = db.search("ファンの制御方法は?", n_results=3)
```

#### FAISSを使った高速検索

```python
db = VectorDatabase(db_type="faiss", api_key=os.getenv("OPENAI_API_KEY"))

# 大量のドキュメントを追加
for doc in documents:
    db.add(doc["text"], metadata=doc["metadata"])

# 高速検索
results = db.search("Raspberry Pi", n_results=10)
```

---

## 2. 自動テスト生成機能

### 2.1 概要

Pythonコードから自動的にユニットテストを生成する機能です。GPT-4を使用して、包括的なテストコードを作成します。

### 2.2 主な機能

#### コード解析

ASTを使用してPythonコードを解析し、関数とクラスを抽出します。

```python
from test_generator import TestGenerator

generator = TestGenerator(api_key="YOUR_API_KEY")
code_info = generator.analyze_code(Path("src/memory.py"))
```

#### テスト生成

```python
test_path = generator.generate_test_for_file(Path("src/memory.py"))
print(f"テストを生成しました: {test_path}")
```

#### ディレクトリ全体のテスト生成

```python
test_paths = generator.generate_tests_for_directory(
    Path("src"),
    exclude_patterns=["__init__.py", "test_*.py"]
)
```

#### テスト実行

```python
result = generator.run_tests()
if result["success"]:
    print("すべてのテストが成功しました")
else:
    print(f"テストが失敗しました:\n{result['stdout']}")
```

### 2.3 生成されるテストの特徴

- ✅ **正常系と異常系の両方をテスト**
- ✅ **エッジケースも考慮**
- ✅ **モックを使った外部依存の分離**
- ✅ **docstringで各テストの目的を説明**
- ✅ **pytestフレームワークを使用**

### 2.4 ファイル構成

```
src/
└── test_generator.py     # 自動テスト生成モジュール

tests/
├── test_memory.py        # 自動生成されたテスト
├── test_executor.py
└── ...
```

### 2.5 使用例

```python
from test_generator import TestGenerator
from pathlib import Path

# 初期化
generator = TestGenerator(
    api_key=os.getenv("OPENAI_API_KEY"),
    test_dir="/home/pi/autonomous_ai/tests"
)

# 単一ファイルのテスト生成
test_path = generator.generate_test_for_file(Path("src/memory.py"))

# テスト実行
result = generator.run_tests()
print(result["stdout"])
```

---

## 3. 高度な自己進化機能

### 3.1 概要

従来の自己進化機能を大幅に強化し、以下の機能を追加しました。

- ✅ **複数ファイルにまたがる修正**
- ✅ **Git連携（自動コミット、ロールバック）**
- ✅ **自動テスト実行**
- ✅ **リスク評価**
- ✅ **修正履歴の記録**

### 3.2 主な機能

#### コードベース全体の解析

```python
from advanced_self_modifier import AdvancedSelfModifier

modifier = AdvancedSelfModifier(api_key="YOUR_API_KEY", git_enabled=True)
codebase_info = modifier.analyze_codebase()
```

#### 修正計画の立案

```python
plan = modifier.plan_modifications(
    request="すべてのログメッセージを日本語に統一してください",
    codebase_info=codebase_info
)

print(f"修正計画: {plan['summary']}")
print(f"リスクレベル: {plan['risk_level']}")
print(f"修正対象ファイル: {len(plan['files_to_modify'])}個")
```

#### 修正の実行

```python
success = modifier.execute_modifications(plan)
if success:
    print("修正が完了しました")
else:
    print("修正が失敗しました（自動ロールバック済み）")
```

#### ワンステップで自己改善

```python
success = modifier.self_improve("パフォーマンスを改善してください")
```

### 3.3 Git連携

#### 自動コミット

修正前後に自動的にGitコミットを作成します。

```
git log --oneline
a1b2c3d Self-modification: すべてのログメッセージを日本語に統一
d4e5f6g Before self-modification
```

#### ロールバック

テストが失敗した場合、自動的にバックアップから復元します。

### 3.4 リスク評価

| リスクレベル | 説明 | 動作 |
| :--- | :--- | :--- |
| **low** | 安全な修正 | 自動実行 |
| **medium** | 注意が必要 | 自動実行 + 警告 |
| **high** | 危険な修正 | 実行をブロック |

### 3.5 修正履歴

すべての修正は`self_modification_history.json`に記録されます。

```json
[
  {
    "timestamp": "2024-02-21T10:30:00",
    "summary": "すべてのログメッセージを日本語に統一",
    "risk_level": "low",
    "modified_files": ["src/memory.py", "src/executor.py"],
    "backup_path": "/home/pi/autonomous_ai/backups/20240221_103000",
    "success": true
  }
]
```

### 3.6 ファイル構成

```
src/
└── advanced_self_modifier.py    # 高度な自己進化モジュール

backups/
├── 20240221_103000/             # バックアップ（タイムスタンプ）
│   └── src/
│       ├── memory.py
│       └── executor.py
└── ...

.git/                            # Gitリポジトリ
self_modification_history.json   # 修正履歴
```

### 3.7 使用例

```python
from advanced_self_modifier import AdvancedSelfModifier

# 初期化
modifier = AdvancedSelfModifier(
    api_key=os.getenv("OPENAI_API_KEY"),
    project_dir="/home/pi/autonomous_ai",
    git_enabled=True
)

# 自己改善
success = modifier.self_improve(
    "すべての関数にtype hintsを追加してください"
)

if success:
    print("自己改善が完了しました")
    print("変更はGitにコミットされました")
else:
    print("自己改善が失敗しました")
```

---

## 4. システム統合

### 4.1 AIエージェントとの統合

新しい機能はAIエージェントのコアシステムに統合されています。

#### ベクトルデータベースの利用

```python
# agent_core.py内
from vector_db import VectorDatabase

class AutonomousAgent:
    def __init__(self):
        # ...
        self.vector_db = VectorDatabase(
            db_type="chromadb",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def remember(self, text: str, metadata: dict):
        """長期記憶に保存"""
        self.vector_db.add(text, metadata)
    
    def recall(self, query: str, n_results: int = 5):
        """長期記憶から検索"""
        return self.vector_db.search(query, n_results)
```

#### 自動テスト生成の利用

```python
# 自己改善後に自動的にテストを生成
from test_generator import TestGenerator

generator = TestGenerator(api_key=os.getenv("OPENAI_API_KEY"))
generator.generate_tests_for_directory(Path("src"))
```

#### 高度な自己進化の利用

```python
# JSONレスポンスに追加
{
  "say": "コードを改善します",
  "advanced_self_improve": {
    "enabled": true,
    "request": "すべての関数にdocstringを追加してください"
  }
}
```

### 4.2 依存関係

新しい機能を使用するには、以下のパッケージが必要です。

```bash
pip3 install -r requirements_advanced.txt
```

---

## 5. パフォーマンスと制限

### 5.1 パフォーマンス

| 機能 | 処理時間 | メモリ使用量 |
| :--- | :--- | :--- |
| ベクトルデータベース（追加） | 〜1秒 | 〜50MB |
| ベクトルデータベース（検索） | 〜0.5秒 | 〜50MB |
| 自動テスト生成 | 〜30秒/ファイル | 〜100MB |
| 高度な自己進化 | 〜60秒/修正 | 〜200MB |

### 5.2 制限

- **OpenAI API**: 埋め込み生成とコード生成にOpenAI APIを使用するため、APIキーが必要です。
- **Gitインストール**: Git連携を使用する場合、Gitがインストールされている必要があります。
- **ディスク容量**: ベクトルデータベースとバックアップにディスク容量が必要です。

---

## 6. トラブルシューティング

### 6.1 ChromaDBが起動しない

```bash
# chromadbを再インストール
pip3 install --upgrade chromadb
```

### 6.2 FAISSがインストールできない

```bash
# ARM64版のFAISSをインストール
pip3 install faiss-cpu
```

### 6.3 Gitコミットが失敗する

```bash
# Gitの初期設定
git config --global user.name "Autonomous AI"
git config --global user.email "ai@localhost"
```

---

**以上で、高度な機能の技術仕様書は終わりです。**
