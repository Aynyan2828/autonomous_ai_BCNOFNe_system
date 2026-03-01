#!/usr/bin/env python3
"""
VOICEVOXキャッシュ事前生成スクリプト
定型フレーズをナースロボ＿タイプTの声で生成してキャッシュに保存
"""

import os
import sys
import hashlib
import glob
import time

# キャッシュする定型フレーズ
PHRASES = [
    # 起動・停止
    "あゆにゃん起動。おはよう、マスター",
    "おやすみ、マスター。また明日ね",
    
    # 緊急停止
    "緊急停止するね、マスター",
    
    # 録音
    "聞いてるよ",
    "ちょっと待ってね",
    
    # 独り言
    "独り言ミュートしたよ",
    "独り言再開するね",
    
    # エラー
    "ごめん、うまくいかなかった",
    "エラーが発生したよ",
    
    # 状態
    "全て正常だよ、マスター",
    
    # 声変更
    "声を変えたよ",
    
    # その他
    "了解、マスター",
    "うん、わかった",
]

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
CORE_DIR = os.path.expanduser("~/voicevox/voicevox_core")
SPEAKER_ID = 47  # ナースロボ＿タイプT（ノーマル）


def cache_key(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def main():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
    
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    print("=== VOICEVOX キャッシュ生成 ===")
    print(f"キャラ: ナースロボ＿タイプT (ID: {SPEAKER_ID})")
    print(f"キャッシュ先: {CACHE_DIR}")
    print(f"フレーズ数: {len(PHRASES)}")
    print()
    
    # VOICEVOX初期化
    print("VOICEVOX 初期化中...")
    ort = Onnxruntime.load_once(
        filename=glob.glob(os.path.join(CORE_DIR, "onnxruntime", "lib", "libvoicevox_onnxruntime*"))[0]
    )
    ojt = OpenJtalk(os.path.join(CORE_DIR, "dict", "open_jtalk_dic_utf_8-1.11"))
    synth = Synthesizer(ort, ojt)
    
    for vvm in glob.glob(os.path.join(CORE_DIR, "models", "vvms", "*.vvm")):
        synth.load_voice_model(VoiceModelFile.open(vvm))
    print("初期化完了！\n")
    
    # フレーズ生成
    for i, phrase in enumerate(PHRASES, 1):
        key = cache_key(phrase)
        out_path = os.path.join(CACHE_DIR, f"{key}.wav")
        
        if os.path.exists(out_path):
            print(f"[{i}/{len(PHRASES)}] スキップ（キャッシュ済み）: {phrase}")
            continue
        
        print(f"[{i}/{len(PHRASES)}] 生成中: {phrase} ...", end="", flush=True)
        start = time.time()
        
        wav = synth.tts(phrase, style_id=SPEAKER_ID)
        with open(out_path, 'wb') as f:
            f.write(wav)
        
        elapsed = time.time() - start
        size_kb = os.path.getsize(out_path) / 1024
        print(f" {elapsed:.1f}秒 ({size_kb:.0f}KB)")
    
    print(f"\n=== 完了！{len(PHRASES)}フレーズをキャッシュしました ===")


if __name__ == "__main__":
    main()
