#!/bin/bash

# BCNOFNe Release Script
# Usage: ./scripts/release.sh 1.2.3

set -e

NEW_VERSION=$1

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.0"
    exit 1
fi

# プロジェクトルートへ移動
cd "$(dirname "$0")/.."

echo "🚀 Releasing BCNOFNe v$NEW_VERSION..."

# 1. VERSION ファイルの更新
echo "$NEW_VERSION" > VERSION

# 2. CHANGELOG.md のチェック（手動更新を推奨するが、存在確認のみ）
if ! grep -q "## \[$NEW_VERSION\]" CHANGELOG.md; then
    echo "⚠️  Warning: $NEW_VERSION not found in CHANGELOG.md. Please update it."
    # 中断せず継続するが警告
fi

# 3. Git 操作
git add VERSION CHANGELOG.md
git commit -m "release: v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo "✅ Local commit and tag created."
echo "Next step: git push origin main && git push origin --tags"
