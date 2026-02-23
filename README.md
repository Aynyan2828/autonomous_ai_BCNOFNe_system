# BCNOFNe（ボクノフネ）- 完全自律型AIシステム on Raspberry Pi 4B

[![GitHub stars](https://img.shields.io/github/stars/Aynyan2828/autonomous_ai_BCNOFNe_system?style=social)](https://github.com/Aynyan2828/autonomous_ai_BCNOFNe_system/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Aynyan2828/autonomous_ai_BCNOFNe_system?style=social)](https://github.com/Aynyan2828/autonomous_ai_BCNOFNe_system/network/members)
[![GitHub issues](https://img.shields.io/github/issues/Aynyan2828/autonomous_ai_BCNOFNe_system)](https://github.com/Aynyan2828/autonomous_ai_BCNOFNe_system/issues)
[![License: MIT](https://img.shields.io/github/license/Aynyan2828/autonomous_ai_BCNOFNe_system)](./LICENSE)

****BCNOFNe（ボクノフネ）** は、GPTを搭載した完全自律型のパーソナルAIサーバーです。**

Raspberry Pi 4B上で24時間365日稼働し、自律的に思考・行動し、長期的な記憶を持ち、外部サービスと連携しながら、厳格な課金制御の下で動作するAIシステムです。

---

## 🌟 主な機能

### 🧠 完全自律型エージェント
- GPT-4がタスク計画、コマンド実行、評価、改善を自律的に行います
- 長期メモリ保存により、再起動後も記憶を保持します
- 自己修正機能により、エラーから学習して改善します

### 🔄 自動再起動
- systemdによる完全自動化
- シャットダウン後30秒で自動起動
- クラッシュしても自動復旧

### 🌐 外部連携
- **Discord**: システム状況をリアルタイム通知
- **LINE Bot**: スマホからAIに指示を送信可能
- **ブラウザ操作**: Playwrightでウェブサイトの自動操作

### 💾 階層型ストレージ (NAS)
- SSD: 高速メインストレージ
- HDD: 大容量長期保存用NAS
- 未使用ファイルを自動でSSD→HDDへ移動

### 💰 課金安全制御（最重要）
- OpenAI API使用料をリアルタイム監視
- 通常日: 200円で注意、300円で自動停止
- 特別日（0, 6, 12, 18, 24, 30日目）: 500円で注意、900円で警告、1000円で自動停止
- 課金前にLINEで確認を求め、許可なしで実行キャンセル

### 🧬 自己進化機能（NEW！）
- **AIが自身のソースコードを読み込み、バグ修正や機能追加を自律的に実行**
- GPT-4によるコード分析と修正提案
- 自動バックアップ作成とロールバック機能
- リスク評価による安全な自己改善
- 修正履歴の完全記録

### 🧠 ベクトルデータベース（NEW！）
- **ChromaDB / FAISS**による長期記憶の強化
- テキストの意味的な類似検索
- 過去の経験と知識を効率的に検索
- 大規模データにも対応

### 🧪 自動テスト生成（NEW！）
- **GPT-4がPythonコードから自動的にユニットテストを生成**
- 正常系・異常系・エッジケースを網羅
- pytestフレームワークを使用
- 自己進化後の品質保証

### 🚀 高度な自己進化（NEW！）
- **複数ファイルにまたがる修正**に対応
- **Git連携**（自動コミット、ロールバック）
- 修正前後の自動テスト実行
- コードベース全体の解析と最適化

### 📁 AI自動ファイル整理（NEW！）
- **AIがファイルの内容を理解して自動分類・整理**
- 画像、ドキュメント、音楽、動画を自動仕分け
- 重複ファイルの検出と削除
- GPT-4によるテキスト内容の分類

### 🌐 Tailscale統合（NEW！）
- **外出先からRaspberry Piに安全にアクセス**
- VPN不要でプライベートネットワーク構築
- LINE Botと組み合わせて外出先からAIに指示
- NASへのリモートアクセス

---

## 📦 システム構成

```
autonomous_ai_system/
├── src/                          # ソースコード
│   ├── main.py                   # メインプログラム
│   ├── agent_core.py             # AIコアエージェント
│   ├── memory.py                 # メモリ管理
│   ├── self_modifier.py          # 自己コード修正（NEW!）
│   ├── executor.py               # コマンド実行エンジン
│   ├── billing_guard.py          # 課金安全制御
│   ├── discord_notifier.py       # Discord通知
│   ├── line_bot.py               # LINE Bot
│   ├── browser_controller.py     # ブラウザ操作
│   └── storage_manager.py        # ストレージ管理
├── systemd/                      # systemd設定
│   └── autonomous-ai.service     # サービスファイル
├── requirements.txt              # Python依存パッケージ
├── .env.template                 # 環境変数テンプレート
├── ARCHITECTURE.md               # システムアーキテクチャ設計書
├── INSTALL_GUIDE.md              # 詳細インストールガイド
└── README.md                     # このファイル
```

---

## 🚀 はじめに

このリポジトリは、Raspberry Pi 4B上で動作する完全自律型AIサーバー「BCNOFNe（ボクノフネ）」の全ソースコードとドキュメントを管理しています。

### 📖 まずはガイドを読もう！

このシステムは非常に多機能なため、まずは以下のドキュメントを読むことを強く推奨します。

- **[🚀 INSTALL_GUIDE_ULTIMATE.md](./INSTALL_GUIDE_ULTIMATE.md)**: **完全初心者向けの超詳細インストールガイド。ここから始めましょう！**
- **[📖 USER_MANUAL.md](./USER_MANUAL.md)**: 日常的な運用方法やAIとの対話方法。

## 🚀 クイックスタート（技術者向け）

### 必要なもの

- **Raspberry Pi 4B** (RAM 4GB以上推奨)
- **SSD** (64GB以上)
- **HDD** (1TB以上、任意)
- **OpenAI APIキー**
- **Discord Webhook URL**
- **LINE Messaging API** (Channel Access Token, Channel Secret, User ID)

### インストール

詳細な手順は **[INSTALL_GUIDE_ULTIMATE.md](./INSTALL_GUIDE_ULTIMATE.md)** を参照してください。

```bash
# 1. プロジェクトをクローン
git clone https://github.com/Aynyan2828/autonomous_ai_BCNOFNe_system.git
cd autonomous_ai_BCNOFNe_system
cd /home/pi/autonomous_ai

# 2. 依存パッケージをインストール
pip3 install -r requirements.txt
playwright install chromium

# 3. 環境変数を設定
cp .env.template .env
nano .env  # APIキーなどを入力

# 4. systemdサービスを登録
sudo cp systemd/autonomous-ai.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable autonomous-ai.service
sudo systemctl start autonomous-ai.service

# 5. 動作確認
sudo systemctl status autonomous-ai.service
journalctl -u autonomous-ai.service -f
```

---

## 📚 ドキュメント一覧

このプロジェクトには、初心者から上級者まで、すべてのユーザーをサポートするための豊富なドキュメントが用意されています。

### 🚀 初心者向けガイド（4つ）
1. **[RASPBERRY_PI_SETUP_GUIDE.md](./RASPBERRY_PI_SETUP_GUIDE.md)**: Raspberry Piの初期設定
2. **[SSH_IP_GUIDE.md](./SSH_IP_GUIDE.md)**: SSH接続とIPアドレスの確認
3. **[INSTALL_GUIDE_ULTIMATE.md](./INSTALL_GUIDE_ULTIMATE.md)**: BCNOFNeシステムのインストール
4. **[EXISTING_OS_GUIDE.md](./EXISTING_OS_GUIDE.md)**: 既存のRaspberry Pi OSへの追加インストール

### 📚 コアシステムドキュメント
5. **[USER_MANUAL.md](./USER_MANUAL.md)**: 取扱説明書（日常運用方法）
6. **[ARCHITECTURE.md](./ARCHITECTURE.md)**: システムアーキテクチャ設計書
7. **[SELF_EVOLUTION.md](./SELF_EVOLUTION.md)**: 自己進化機能技術仕様書

### 🔬 高度な機能ドキュメント
8. **[ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md)**: 高度な機能技術仕様書
9. **[AI_FILE_ORGANIZER_TAILSCALE.md](./AI_FILE_ORGANIZER_TAILSCALE.md)**: AI自動ファイル整理 & Tailscale技術仕様書

### ⚙️ ハードウェアドキュメント
10. **[hardware/README_HARDWARE.md](./hardware/README_HARDWARE.md)**: OLED・ファン制御概要
11. **[hardware/INSTALL_GUIDE_HARDWARE.md](./hardware/INSTALL_GUIDE_HARDWARE.md)**: インストールガイド

### 🤝 コミュニティ
12. **[CONTRIBUTING.md](./CONTRIBUTING.md)**: プロジェクトへの貢献方法

- **[INSTALL_GUIDE.md](./INSTALL_GUIDE.md)**: 初心者向け詳細インストール手順（全ソースコード付き）
- **[USER_MANUAL.md](./USER_MANUAL.md)**: 取扱説明書（日常的な運用方法）
- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: システムアーキテクチャ設計書
- **[SELF_EVOLUTION.md](./SELF_EVOLUTION.md)**: 自己進化機能技術仕様書

---

## 🔒 セキュリティ

このシステムは強力な機能を持ち、インターネットに接続して自律的に動作するため、セキュリティには最大限の注意を払ってください。

- `.env` ファイルは絶対に公開しないでください
- SSHは強力なパスワードまたは公開鍵認証を使用してください
- 課金監視機能を過信せず、OpenAI公式サイトでも定期的に利用額を確認してください
- AIが実行するコマンドを定期的に監視してください

詳細は **[INSTALL_GUIDE_ULTIMATE.md](./INSTALL_GUIDE_ULTIMATE.md)** のセキュリティに関するセクションを参照してください。

---

## 🛠️ トラブルシューティング

### サービスが起動しない

```bash
# ログを確認
journalctl -u autonomous-ai.service -n 50

# 環境変数が正しく設定されているか確認
cat /home/pi/autonomous_ai/.env

# 手動で起動してエラーを確認
cd /home/pi/autonomous_ai/src
python3 main.py
```

### 課金が止まらない

システムが自動停止しない場合は、手動で停止してください。

```bash
sudo systemctl stop autonomous-ai.service
```

### LINEやDiscordに通知が来ない

- Webhook URLやAPIキーが正しいか確認してください
- ネットワーク接続を確認してください
- ログでエラーメッセージを確認してください

---

## 🤝 貢献

このプロジェクトはオープンソースです。バグ報告、機能提案、ドキュメントの改善、コードの修正など、どんな形でも貢献を歓迎します。

詳細は **[CONTRIBUTING.md](./CONTRIBUTING.md)** を参照してください。

- ベクトルデータベース (ChromaDB, FAISS) の導入
- マルチモーダル対応 (GPT-4V)
- カレンダーAPI連携
- スマートホームデバイス制御
- 自動テスト生成機能
- 自己進化のさらなる高度化（複数ファイルにまたがる修正、Git連携など）

---

## 📜 ライセンス

MIT License

---

## 🙏 謝辞

このプロジェクトは、OpenAI、Raspberry Pi Foundation、そしてオープンソースコミュニティの素晴らしい成果の上に成り立っています。

---

**AIと共に、新しい可能性を探求してください！**
