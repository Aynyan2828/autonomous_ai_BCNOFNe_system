# 自己進化機能 - 技術仕様書

---

## 1. 概要

本システムの自己進化機能は、AIが自身のソースコードを読み込み、分析し、バグ修正や機能追加を自律的に行う能力を提供します。これにより、システムは時間とともに自己改善を続け、真の自己進化型AIシステムとして動作します。

## 2. アーキテクチャ

### コンポーネント構成

```
自己進化システム
├── agent_core.py (AIコアエージェント)
│   └── self_improve フィールドによる自己改善のトリガー
├── self_modifier.py (自己コード修正モジュール)
│   ├── コード分析エンジン
│   ├── 修正提案生成エンジン
│   ├── リスク評価エンジン
│   └── 修正適用エンジン
└── バックアップ・ロールバック機構
```

### データフロー

```
1. AIが自己改善の必要性を判断
   ↓
2. self_improve フィールドを有効化
   ↓
3. SelfModifier.self_improve() 呼び出し
   ↓
4. 対象ファイルの読み込み
   ↓
5. GPT-4による分析（バグ・改善点の発見）
   ↓
6. 修正提案の生成
   ↓
7. リスク評価（low/medium/high）
   ↓
8. バックアップ作成
   ↓
9. 修正適用（リスクが低い場合のみ）
   ↓
10. 修正履歴の記録
```

## 3. JSON出力スキーマ

AIエージェントが自己改善を実行する際の出力スキーマは以下の通りです。

```json
{
  "say": "自分のコードを見直して、バグを修正します",
  "cmd": [],
  "memory_write": [],
  "diary_append": "自己改善を実行しました",
  "next_goal": "修正後の動作を確認する",
  "self_improve": {
    "enabled": true,
    "target_file": "memory.py",
    "request": "バグを探して修正してください"
  }
}
```

### フィールド説明

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `enabled` | boolean | 自己改善を実行するかどうか |
| `target_file` | string | 修正対象ファイル名（空の場合は全ファイル） |
| `request` | string | 具体的なリクエスト（例: 「バグを修正して」「パフォーマンスを改善して」） |

## 4. SelfModifier クラス仕様

### 主要メソッド

#### `self_improve(target_file, specific_request, auto_apply)`

自己改善を実行します。

**引数:**
- `target_file` (Optional[str]): 対象ファイル名（指定しない場合は全ファイル）
- `specific_request` (Optional[str]): 特定のリクエスト
- `auto_apply` (bool): 自動で修正を適用するか（デフォルト: False）

**戻り値:**
```python
{
  "analyzed_files": 3,
  "issues_found": 5,
  "improvements_suggested": 8,
  "modifications_applied": 2,
  "files_modified": ["memory.py", "executor.py"]
}
```

#### `analyze_code(file_path, specific_request)`

コードを分析し、問題点と改善提案を返します。

**戻り値:**
```python
{
  "analysis": "このコードには型チェックが不足しています...",
  "issues": [
    "関数add()に引数の型チェックがない",
    "関数divide()にゼロ除算のチェックがない"
  ],
  "improvements": [
    "型ヒントを追加する",
    "例外処理を追加する"
  ],
  "modifications": [
    {
      "file": "executor.py",
      "reason": "ゼロ除算のチェックを追加",
      "original_code": "return a / b",
      "modified_code": "if b == 0:\n    raise ValueError('ゼロ除算')\nreturn a / b",
      "line_start": 10,
      "line_end": 10
    }
  ],
  "risk_level": "low",
  "recommendation": "実行推奨"
}
```

#### `create_backup(file_path)`

ファイルのバックアップを作成します。

**戻り値:** バックアップファイルのパス

#### `rollback(backup_path, target_path)`

バックアップからロールバックします。

## 5. リスク評価基準

GPT-4は、修正のリスクレベルを以下の基準で評価します。

| リスクレベル | 説明 | 自動適用 |
| :--- | :--- | :--- |
| **low** | 軽微なバグ修正、コメント追加、型ヒント追加など | ✅ 可能 |
| **medium** | ロジックの変更、新しい関数の追加など | ❌ 不可 |
| **high** | コアロジックの大幅な変更、セキュリティに関わる変更など | ❌ 不可 |

## 6. 安全機構

### 多層防御

1.  **バックアップ自動作成**: 修正前に必ず元のファイルをバックアップします。
2.  **リスク評価**: GPT-4が修正のリスクを評価し、高リスクの修正は自動適用されません。
3.  **分析のみモード**: デフォルトでは、分析と修正提案のみを行い、実際の適用は行いません（`auto_apply=False`）。
4.  **修正履歴の記録**: すべての修正は `/home/pi/autonomous_ai/logs/self_modifications.jsonl` に記録されます。
5.  **行番号検証**: 修正対象の行番号が有効範囲内かチェックします。

### バックアップ管理

バックアップファイルは以下の命名規則で保存されます。

```
{ファイル名}_{タイムスタンプ}.py
例: agent_core_20260219_123456.py
```

保存先: `/home/pi/autonomous_ai/backups/`

## 7. 使用例

### 例1: 特定のファイルのバグを修正

```python
from self_modifier import SelfModifier

modifier = SelfModifier(api_key="sk-...")

result = modifier.self_improve(
    target_file="memory.py",
    specific_request="バグを探して修正してください",
    auto_apply=False  # 分析のみ
)

print(result)
```

### 例2: 全ファイルのパフォーマンスを改善

```python
result = modifier.self_improve(
    target_file=None,  # 全ファイル
    specific_request="パフォーマンスを改善してください",
    auto_apply=False
)
```

### 例3: ロールバック

```python
from pathlib import Path

modifier.rollback(
    backup_path=Path("/home/pi/autonomous_ai/backups/agent_core_20260219_123456.py"),
    target_path=Path("/home/pi/autonomous_ai/src/agent_core.py")
)
```

## 8. 制限事項

- **GPT-4の制約**: 分析精度はGPT-4の能力に依存します。複雑なバグは検出できない場合があります。
- **コンテキスト長**: 非常に長いファイル（数千行以上）は、一度に分析できない場合があります。
- **実行環境**: 修正後のコードが実際に動作するかは、システムの再起動後に確認する必要があります。
- **依存関係**: 複数のファイルにまたがる修正は、現在のバージョンでは完全には対応していません。

## 9. 今後の拡張案

- **自動テスト生成**: 修正後のコードに対するユニットテストを自動生成
- **段階的適用**: 複数の修正を一度に適用せず、1つずつ適用してテスト
- **ロールバック自動化**: 修正後にエラーが発生した場合、自動でロールバック
- **依存関係解析**: 複数ファイルにまたがる修正を一括で提案
- **バージョン管理統合**: Gitと連携して、修正をコミットとして記録

---

**この機能により、AIは真の自己進化型システムとして、時間とともに成長し続けます。**
