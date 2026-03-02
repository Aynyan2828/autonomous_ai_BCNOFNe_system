#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
shipOS GUI 管理パネル
モード管理・ヘルス監視・航海日誌・目標入力・メンテナンス

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
BASE_DIR = "/home/pi/autonomous_ai_BCNOFNe_system"
AI_STATE_FILE = "/var/run/ai_state.json"
AGENT_LOG = os.path.join(BASE_DIR, "logs", "agent.log")
INBOX_FILE = os.path.join(BASE_DIR, "commands", "inbox.jsonl")
HISTORY_DIR = os.path.join(BASE_DIR, "commands", "history")
GOAL_HISTORY = os.path.join(BASE_DIR, "memory", "goal_history.jsonl")
SHIP_MODE_FILE = os.path.join(BASE_DIR, "state", "ship_mode.json")
HEALTH_HISTORY = os.path.join(BASE_DIR, "state", "health_history.jsonl")
SHIPS_LOG_DIR = os.path.join(BASE_DIR, "state", "ships_log")
MODE_HISTORY_FILE = os.path.join(BASE_DIR, "state", "mode_history.jsonl")
MOOD_LOG = os.path.join(BASE_DIR, "state", "mood_log.jsonl")

# モード定義
MODES = {
    "autonomous": {"name": "自律航海 ⛵", "desc": "自律思考・整理・学習・保守"},
    "user_first": {"name": "入港待機 🏠", "desc": "ユーザー対話・支援優先"},
    "maintenance": {"name": "ドック入り 🔧", "desc": "保守・メンテナンス専用"},
    "power_save": {"name": "停泊 🌙", "desc": "省電力・最小稼働"},
    "safe": {"name": "救難信号 🆘", "desc": "安全モード・最小機能"},
}


# ============================
# ユーティリティ
# ============================
def read_ai_state() -> dict:
    try:
        if os.path.exists(AI_STATE_FILE):
            with open(AI_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"state": "Unknown", "task": "", "timestamp": ""}


def read_ship_mode() -> dict:
    try:
        if os.path.exists(SHIP_MODE_FILE):
            with open(SHIP_MODE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {"mode": "autonomous", "since": "", "override": False}


def write_ship_mode(mode: str, reason: str = "GUI手動切替"):
    """モードを直接書き換え + 履歴記録"""
    state = read_ship_mode()
    old = state.get("mode", "autonomous")
    new_state = {
        "mode": mode,
        "since": datetime.now().isoformat(),
        "override": True,
        "override_until": None,
        "updated": datetime.now().isoformat()
    }
    os.makedirs(os.path.dirname(SHIP_MODE_FILE), exist_ok=True)
    with open(SHIP_MODE_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)
    # 履歴
    try:
        with open(MODE_HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "from": old, "to": mode, "reason": reason,
                "source": "gui", "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_last_log_lines(path: str, n: int = 50) -> str:
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return "".join(lines[-n:])
    except Exception:
        pass
    return "(読み取り不可)"


def read_jsonl_tail(path: str, n: int = 20) -> list:
    entries = []
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except Exception:
                        continue
    except Exception:
        pass
    return entries[-n:]


def get_command_history(limit: int = 30) -> list:
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
    os.makedirs(os.path.dirname(INBOX_FILE), exist_ok=True)
    with open(INBOX_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            "type": event_type,
            "text": text,
            "user_id": "gui",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False) + "\n")


def get_service_status(service: str) -> str:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "不明"


def get_disk_usage() -> dict:
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


def get_today_ships_log() -> list:
    today_file = os.path.join(SHIPS_LOG_DIR, f"{datetime.now().strftime('%Y%m%d')}.jsonl")
    return read_jsonl_tail(today_file, 30)


# ============================
# Streamlit ページ
# ============================
st.set_page_config(
    page_title="shipOS BCNOFNe",
    page_icon="🚢",
    layout="wide"
)

st.title("🚢 shipOS BCNOFNe 管理パネル")

# --- サイドバー ---
with st.sidebar:
    # === モード切替 ===
    st.header("⛵ 航海モード")
    mode_data = read_ship_mode()
    current_mode = mode_data.get("mode", "autonomous")
    mode_info = MODES.get(current_mode, MODES["autonomous"])

    st.markdown(f"### 現在: {mode_info['name']}")
    st.caption(mode_info['desc'])
    if mode_data.get("override"):
        st.warning("手動オーバーライド中")

    new_mode = st.selectbox(
        "モード切替",
        list(MODES.keys()),
        format_func=lambda m: MODES[m]["name"],
        index=list(MODES.keys()).index(current_mode)
    )
    if st.button("🔄 モード変更", use_container_width=True):
        if new_mode != current_mode:
            write_ship_mode(new_mode)
            st.success(f"切替: {MODES[new_mode]['name']}")
            st.rerun()

    st.divider()

    # === 目標入力 ===
    st.header("📝 指示入力")
    new_goal = st.text_area("テキスト", height=80)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 目標設定", use_container_width=True):
            if new_goal.strip():
                submit_goal(new_goal.strip(), "goal")
                st.success("送信しました")
    with col2:
        if st.button("❓ 質問送信", use_container_width=True):
            if new_goal.strip():
                submit_goal(new_goal.strip(), "query")
                st.success("送信しました")

    st.divider()

    # === システム操作 ===
    st.header("🛑 システム操作")
    if st.button("🛑 緊急停止", type="primary", use_container_width=True):
        try:
            subprocess.run(["sudo", "systemctl", "stop", "autonomous-ai.service"], timeout=10)
            st.error("AIエージェントを停止しました")
        except Exception as e:
            st.error(f"停止失敗: {e}")

    if st.button("🚀 再起動", use_container_width=True):
        try:
            subprocess.run(["sudo", "systemctl", "restart", "autonomous-ai.service"], timeout=10)
            st.success("再起動しました")
        except Exception as e:
            st.error(f"再起動失敗: {e}")


# --- メインコンテンツ ---
# タブ構成
tab_status, tab_health, tab_log, tab_history = st.tabs([
    "📊 状態", "🏥 ヘルス", "📔 航海日誌", "📜 履歴"
])


# ===== タブ1: 状態 =====
with tab_status:
    col_state, col_storage, col_mood = st.columns(3)

    with col_state:
        st.subheader("🤖 AI状態")
        ai_state = read_ai_state()
        svc = get_service_status("autonomous-ai.service")
        icon = "🟢" if svc == "active" else "🔴"
        st.metric("サービス", f"{icon} {svc}")
        st.metric("AI状態", ai_state.get("state", "Unknown"))
        st.metric("タスク", ai_state.get("task", "-") or "-")
        st.caption(f"更新: {ai_state.get('timestamp', '-')}")

        # 追加サービス
        for svc_name in ["shipos-watchdog", "shipos-audio"]:
            s = get_service_status(svc_name)
            svc_icon = "🟢" if s == "active" else "⚪"
            st.caption(f"{svc_icon} {svc_name}: {s}")

    with col_storage:
        st.subheader("💾 ストレージ")
        disk = get_disk_usage()
        for name, info in disk.items():
            if info:
                st.progress(
                    min(info["percent"] / 100, 1.0),
                    text=f"{name}: {info['used_gb']:.1f}/{info['total_gb']:.1f}GB ({info['percent']:.1f}%)"
                )
            else:
                st.warning(f"{name}: 未接続")

    with col_mood:
        st.subheader("😊 Mood")
        mood_entries = read_jsonl_tail(MOOD_LOG, 1)
        if mood_entries:
            m = mood_entries[-1]
            mood = m.get("mood", {})
            st.metric("スコア", f"{mood.get('emoji', '')} {mood.get('score', '?')}")
            st.caption(mood.get("line", ""))
            sys_info = m.get("system", {})
            st.caption(
                f"CPU:{sys_info.get('cpu_temp', '?')}℃ "
                f"MEM:{sys_info.get('mem_percent', '?')}% "
                f"NET:{'✅' if sys_info.get('net_ok') else '❌'}"
            )
        else:
            st.info("Moodデータなし")


# ===== タブ2: ヘルス =====
with tab_health:
    st.subheader("🏥 ヘルスモニタ")
    health_entries = read_jsonl_tail(HEALTH_HISTORY, 1)
    if health_entries:
        h = health_entries[-1]
        ts = h.get("timestamp", "")[:19]
        st.caption(f"最終チェック: {ts}")
        checks = h.get("checks", [])
        for c in checks:
            status = c.get("status", "UNKNOWN")
            icon = {"OK": "🟢", "WARN": "🟡", "CRITICAL": "🔴"}.get(status, "⚪")
            st.text(f"{icon} {c.get('name', '')}: {c.get('message', '')}")
    else:
        st.info("ヘルスデータなし")

    st.divider()

    # モード切替履歴
    st.subheader("🔄 モード切替履歴")
    mode_hist = read_jsonl_tail(MODE_HISTORY_FILE, 10)
    if mode_hist:
        for mh in reversed(mode_hist):
            ts = mh.get("timestamp", "")[:19]
            fr = MODES.get(mh.get("from", ""), {}).get("name", mh.get("from", ""))
            to = MODES.get(mh.get("to", ""), {}).get("name", mh.get("to", ""))
            st.text(f"[{ts}] {fr} → {to} ({mh.get('source', '')}: {mh.get('reason', '')})")
    else:
        st.info("モード切替履歴なし")


# ===== タブ3: 航海日誌 =====
with tab_log:
    st.subheader("📔 本日の航海日誌")
    log_entries = get_today_ships_log()
    if log_entries:
        # 統計
        total = len(log_entries)
        success = sum(1 for e in log_entries if e.get("success", True))
        types = {}
        for e in log_entries:
            t = e.get("type", "?")
            types[t] = types.get(t, 0) + 1

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("行動回数", total)
        col_b.metric("成功率", f"{(success/total*100):.0f}%" if total else "0%")
        col_c.metric("種類", len(types))

        st.divider()

        # 最新エントリ
        for e in reversed(log_entries[-20:]):
            ts = e.get("ts", "")[:19]
            icon = "✅" if e.get("success", True) else "❌"
            st.text(f"{icon} [{ts}] {e.get('type', '')}: {e.get('detail', '')[:60]}")
    else:
        st.info("本日のエントリなし")

    st.divider()

    # エージェントログ
    st.subheader("📋 エージェントログ (最新50行)")
    log_content = read_last_log_lines(AGENT_LOG, 50)
    st.code(log_content, language="text")


# ===== タブ4: 履歴 =====
with tab_history:
    col_cmd, col_goal = st.columns(2)

    with col_cmd:
        st.subheader("📨 コマンド履歴")
        history = get_command_history(20)
        if history:
            for entry in history:
                etype = entry.get("type", "goal")
                icon = "❓" if etype == "query" else "🎯"
                ts = entry.get("timestamp", "")[:19]
                text = entry.get("text", entry.get("command", ""))
                st.text(f"{icon} [{ts}] {text[:60]}")
        else:
            st.info("履歴なし")

    with col_goal:
        st.subheader("🎯 目標変更履歴")
        goal_hist = get_goal_history(10)
        if goal_hist:
            for gh in reversed(goal_hist):
                ts = gh.get("timestamp", "")[:19]
                st.text(
                    f"[{ts}] {gh.get('reason', '')} | "
                    f"{gh.get('old_goal', '')[:25]} → {gh.get('new_goal', '')[:25]}"
                )
        else:
            st.info("目標変更履歴なし")
