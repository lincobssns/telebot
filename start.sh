#!/bin/bash
set -e

echo "🚀 Instalando Python e dependências..."
apt-get update -y && apt-get install -y python3 python3-pip python3-venv

# Cria e ativa um ambiente virtual isolado
echo "🐍 Criando ambiente virtual..."
python3 -m venv .venv
source .venv/bin/activate

echo "📦 Instalando dependências do projeto..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Iniciando bot Telegram..."
python repost.py
