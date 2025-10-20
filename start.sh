#!/bin/bash
set -e
echo "🚀 Instalando Python e dependências..."
apt-get update -y && apt-get install -y python3 python3-pip

echo "📦 Instalando dependências do projeto..."
pip3 install -r requirements.txt

echo "✅ Iniciando bot Telegram..."
python3 repost.py
