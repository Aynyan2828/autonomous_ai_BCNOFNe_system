#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit GUI モジュール
自律AIシステムの状態確認・目標入力・メンテナンス操作

使い方:
  streamlit run gui_app.py --server.port 8501
"""

import os
import json
import glob
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st

# パス設定
BASE_DIR = "/home/pi/autonomous_ai"
AI_STATE_FILE = "/var/run/ai_state.json"
AGENT_LOG = os.path.join(BASE_DIR, "logs", "agent.log")
INBOX_FILE = os.path.join(BASE_DIR, "commands", "inbox.jsonl")
HISTORY_DIR = os.path.join(BASE_DIR, "commands", "history")
GOAL_HISTORY = os.path.join(BASE_DIR, "memory", "goal_history.jsonl")
STORAGE_CONFIG = os.path.join(BASE_DIR, "storage_config.json")


# ============================
# ユーティリティ
# ============================
def read_ai_state() -> dict:
    """AI状態ファイルを読み取り"""
    try:
        if os.path.exists(AI_STATE_FILE):
            with open(AI_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"state": "Unknown", "task": "", "timestamp": ""}


def read_last_log_lines(path: str, n: int = 50) -> str:
    """末尾n行を読み取り"""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return "".join(lines[-n:])
    except Exception:
        pass
    return "(読み取り不可)"


def get_command_history(limit: int = 30) -> list:
    """コマンド履歴を取得（新しい順）"""
    entries = []
    try:
        for day_dir in sorted(glob.glob(os.path.join(HISTORY_DIR, "*")), reverse=True):
            for fpath in sorted(glob.glob(os.path.join(day_dir, "*.json")), reverse=True):
                with open(fpath, 'r', encoding='utf-8') as f:
                    entries.append(json.load(f))
                if len(entries) >= limit:
                    return entries
    except Exception:
        pass
    return entries


def get_goal_history(limit: int = 20) -> list:
    """目標履歴を取得"""
    entries = []
    try:
        if os.path.exists(GOAL_HISTORY):
            with open(GOAL_HISTORY, 'r', encoding='utf-8') as f:
                for line in f:
                    entries.append(json.loads(line.strip()))
            return entries[-limit:]
    except Exception:
        pass
    return entries


def submit_goal(text: str, event_type: str = "goal"):
    """目標/質問をインボックスに追記"""
    os.makedirs(os.path.dirname(INBOX_FILE), exist_ok=True)
    with open(INBOX_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            "type": event_type,
            "text": text,
            "user_id": "gui",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False) + "\n")


def get_service_status(service: str) -> str:
    """systemctlで状態確認"""
    try:
        r = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "不明"


def get_disk_usage() -> dict:
    """ディスク使用量"""
    import shutil
    result = {}
    for name, path in [("SSD", BASE_DIR), ("HDD", "/mnt/hdd/archive")]:
        try:
            usage = shutil.disk_usage(path)
            result[name] = {
                "total_gb": usage.total / (1024**3),
                "used_gb": usage.used / (1024**3),
                "free_gb": usage.free / (1024**3),
                "percent": (usage.used / usage.total) * 100
            }
        except Exception:
            result[name] = None
    return result


# ============================
# Streamlit ページ
# ============================
st.set_page_config(
    page_title="自律AI BCNOFNe 管理パネル",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 自律AI BCNOFNe 管理パネル")

# --- サイドバー ---
with st.sidebar:
    st.header("⚡ クイック操作")
    
    # 目標入力
    st.subheader("📝 目標入力")
    new_goal = st.text_area("目標テキスト", height=80)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 目標設定", use_container_width=True):
            if new_goal.strip():
                submit_goal(new_goal.strip(), "goal")
                st.success("目標を送信しました")
    with col2:
        if st.button("❓ 質問送信", use_container_width=True):
            if new_goal.strip():
                submit_goal(new_goal.strip(), "query")
                st.success("質問を送信しました")
    
    st.divider()
    
    # 緊急停止
    st.subheader("🛑 システム操作")
    if st.button("🛑 緊急停止", type="primary", use_container_width=True):
        try:
            subprocess.run(
                ["sudo", "systemctl", "stop", "autonomous-ai.service"],
                timeout=10
            )
            st.error("AIエージェントを停止しました")
        except Exception as e:
            st.error(f"停止失敗: {e}")
    
    if st.button("🚀 再起動", use_container_width=True):
        try:
            subprocess.run(
                ["sudo", "systemctl", "restart", "autonomous-ai.service"],
                timeout=10
            )
            st.success("AIエージェントを再起動しました")
        except Exception as e:
            st.error(f"再起動失敗: {e}")
    
    st.divider()
    
    # 手動メンテ
    st.subheader("🔧 メンテナンス")
    if st.button("📦 ファイル整理 (dry-run)", use_container_width=True):
        submit_goal("ファイル整理を実行してください（dry-run）", "goal")
        st.info("メンテナンス指示を送信しました")

# --- メインコンテンツ ---
# 状態パネル
col_state, col_storage = st.columns(2)

with col_state:
    st.subheader("📊 現在の状態")
    ai_state = read_ai_state()
    service_status = get_service_status("autonomous-ai.service")
    
    status_icon = "🟢" if service_status == "active" else "🔴"
    st.metric("サービス", f"{status_icon} {service_status}")
    st.metric("AI状態", ai_state.get("state", "Unknown"))
    st.metric("タスク", ai_state.get("task", "-") or "-")
    st.caption(f"更新: {ai_state.get('timestamp', '-')}")

with col_storage:
    st.subheader("💾 ストレージ")
    disk = get_disk_usage()
    for name, info in disk.items():
        if info:
            st.progress(
                min(info["percent"] / 100, 1.0),
                text=f"{name}: {info['used_gb']:.1f} GB / {info['total_gb']:.1f} GB ({info['percent']:.1f}%)"
            )
        else:
            st.warning(f"{name}: 未接続")

# ログビューアー
st.subheader("📋 エージェントログ (最新50行)")
log_content = read_last_log_lines(AGENT_LOG, 50)
st.code(log_content, language="text")

# コマンド履歴
st.subheader("📨 コマンド履歴")
history = get_command_history(20)
if history:
    for entry in history:
        etype = entry.get("type", "goal")
        icon = "❓" if etype == "query" else "🎯"
        ts = entry.get("timestamp", "")[:19]
        text = entry.get("text", entry.get("command", ""))
        st.text(f"{icon} [{ts}] {text[:80]}")
else:
    st.info("履歴はありません")

# 目標履歴
st.subheader("🎯 目標変更履歴")
goal_hist = get_goal_history(10)
if goal_hist:
    for gh in reversed(goal_hist):
        ts = gh.get("timestamp", "")[:19]
        st.text(
            f"[{ts}] {gh.get('reason', '')} | "
            f"{gh.get('old_goal', '')[:30]} → {gh.get('new_goal', '')[:30]}"
        )
else:
    st.info("目標変更履歴はありません")
