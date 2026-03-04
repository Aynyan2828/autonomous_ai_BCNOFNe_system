import os
import subprocess
from pathlib import Path

def get_version() -> str:
    """
    BCNOFNe の現在バージョンを取得します。
    VERSION ファイルが存在しない場合は '0.0.0' を返します。
    """
    version_file = Path(__file__).parent.parent / "VERSION"
    if not version_file.exists():
        return "0.0.0"
    
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"

def get_git_sha() -> str:
    """
    現在の Git 短縮 SHA を取得します。
    取得できない場合は空文字列を返します。
    """
    try:
        # 作業ディレクトリをプロジェクトルートに設定
        root_dir = Path(__file__).parent.parent
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception:
        return ""

def get_full_version_string() -> str:
    """
    'BCNOFNe v1.0.0 (abc1234)' 形式の文字列を返します。
    """
    version = get_version()
    sha = get_git_sha()
    if sha:
        return f"BCNOFNe v{version} ({sha})"
    return f"BCNOFNe v{version}"

if __name__ == "__main__":
    print(get_full_version_string())
