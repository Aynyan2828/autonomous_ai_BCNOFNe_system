#!/bin/bash
# Tailscaleインストールスクリプト

set -e

echo "========================================="
echo "  Tailscale インストールスクリプト"
echo "========================================="
echo ""

# rootユーザーで実行されているか確認
if [ "$EUID" -ne 0 ]; then
    echo "このスクリプトはroot権限で実行する必要があります。"
    echo "sudo ./install_tailscale.sh を実行してください。"
    exit 1
fi

# Tailscaleが既にインストールされているか確認
if command -v tailscale &> /dev/null; then
    echo "✅ Tailscaleは既にインストールされています。"
    tailscale version
    echo ""
    
    echo "Tailscaleを再インストールしますか? (y/n): "
    read -r response
    if [ "$response" != "y" ]; then
        echo "インストールをスキップします。"
        exit 0
    fi
fi

# Tailscaleをインストール
echo "📦 Tailscaleをインストール中..."
curl -fsSL https://tailscale.com/install.sh | sh

echo ""
echo "✅ Tailscaleのインストールが完了しました。"
echo ""

# Tailscaleを起動
echo "🚀 Tailscaleを起動しますか? (y/n): "
read -r response

if [ "$response" = "y" ]; then
    echo ""
    echo "Tailscaleを起動します..."
    echo "ブラウザが開くので、Tailscaleアカウントでログインしてください。"
    echo ""
    
    # Tailscaleを起動
    tailscale up
    
    echo ""
    echo "✅ Tailscaleが起動しました。"
    echo ""
    
    # ステータスを表示
    echo "=== Tailscale ステータス ==="
    tailscale status
    echo ""
    
    # IPアドレスを表示
    echo "=== Tailscale IPアドレス ==="
    tailscale ip -4
    echo ""
    
    echo "✅ セットアップが完了しました！"
    echo ""
    echo "外出先からこのRaspberry Piにアクセスするには、"
    echo "上記のIPアドレスを使用してください。"
    echo ""
    echo "例: ssh pi@$(tailscale ip -4)"
else
    echo ""
    echo "Tailscaleを起動するには、以下のコマンドを実行してください:"
    echo "  sudo tailscale up"
fi

echo ""
echo "========================================="
echo "  インストール完了"
echo "========================================="
