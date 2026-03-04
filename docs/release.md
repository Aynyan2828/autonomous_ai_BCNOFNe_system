# BCNOFNe Release Procedure

BCNOFNe システムのバージョン管理とリリース手順について説明します。
本プロジェクトは [Semantic Versioning (SemVer)](https://semver.org/spec/v2.0.0.html) を採用しています。

## バージョン番号のルール

バージョンは `MAJOR.MINOR.PATCH` の形式で管理します。

1.  **MAJOR**: 互換性のない大幅な変更、アーキテクチャの刷新
2.  **MINOR**: 後方互換性のある機能追加（新しいコマンド、新しいセンサー対応など）
3.  **PATCH**: 後方互換性のあるバグ修正、文言の修正、ドキュメント更新

## リリースフロー

新しいバージョンをリリースする際は、以下の手順を手動またはスクリプトで行います。

### 1. バージョンの決定
現在の `VERSION` ファイルを確認し、次のバージョン番号を決定します。

### 2. ファイルの更新
-   `VERSION` ファイルの書き換え（例: `1.0.1`）
-   `CHANGELOG.md` に変更内容を追記（`Keep a Changelog` 形式）

### 3. コミットとタグ付け
```bash
git add VERSION CHANGELOG.md
git commit -m "release: v1.0.1"
git tag -a v1.0.1 -m "Release v1.0.1"
```

### 4. Push
```bash
git push origin main
git push origin --tags
```

---

## 自動リリーススクリプト (`scripts/release.sh`)

以下のスクリプトを使用して、手順2〜4を自動化できます。

```bash
# 使用例
./scripts/release.sh 1.0.1
```

※スクリプトは `scripts/release.sh` に配置されています。実行権限が必要です (`chmod +x scripts/release.sh`)。
