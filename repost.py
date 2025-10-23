"""
bot_forwarder_secure.py
Versão segura: NÃO imprime segredos. Lê todas as credenciais via ENV.
Use secrets no Railway / Heroku / seu host e NÃO suba .env público.
"""

import os
import random
import asyncio
import sys
import json
import traceback
from datetime import datetime
import pytz

from telethon import TelegramClient, errors as tele_errors
from telegram import Bot, ParseMode
from telegram.error import TelegramError

# ============ UTIL =============
BR_TIMEZONE = pytz.timezone(os.getenv("TZ", "America/Sao_Paulo"))

def now_str():
    return datetime.now(BR_TIMEZONE).strftime('%d/%m/%Y %H:%M:%S')

def safe_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

def mask_secret(value: str, keep=4):
    """Mascarar segredos para log (mostra apenas últimos `keep` chars)."""
    if not value:
        return "<empty>"
    s = str(value)
    if len(s) <= keep:
        return "*" * len(s)
    return ("*" * (len(s) - keep)) + s[-keep:]

# ============ CARREGAMENTO DE VARIÁVEIS (obrigatórias) =============
# Variáveis obrigatórias (defina como secrets no Railway)
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_FILE = os.getenv("SESSION_FILE", "telegram_session.session")  # nome do arquivo .session no container
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configuráveis
INTERVAL_HOURS = float(os.getenv("INTERVAL_HOURS", "2"))
SEND_INTERVAL = int(INTERVAL_HOURS * 3600)
LIMIT_MESSAGES = int(os.getenv("LIMIT_MESSAGES", "100"))

# PARES doador -> receptor (JSON string ou fallback hardcoded seguro)
# Exemplo de variável de ambiente:
# DONOR_RECIPIENT_PAIRS='{"-1002957443418": -1002646886211}'
pairs_env = os.getenv("DONOR_RECIPIENT_PAIRS")
if pairs_env:
    try:
        donor_recipient_pairs = {int(k): int(v) for k, v in json.loads(pairs_env).items()}
    except Exception:
        safe_print(f"{now_str()} ❌ DONOR_RECIPIENT_PAIRS inválido. Use JSON como '{{\"-100...\": -100...}}'")
        donor_recipient_pairs = {}
else:
    # fallback - vazio (evita expor IDs no código)
    donor_recipient_pairs = {}

# ============ VALIDAÇÕES INICIAIS ============
def validate_config_or_exit():
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not donor_recipient_pairs:
        missing.append("DONOR_RECIPIENT_PAIRS (não foi fornecido ou inválido)")

    if missing:
        safe_print(f"{now_str()} ❌ Configuração incompleta. Variáveis faltando: {', '.join(missing)}")
        safe_print("Defina as variáveis de ambiente necessárias e reinicie o serviço.")
        sys.exit(1)

    # Sessão: apenas checar presença do arquivo (se estiver usando Telethon)
    if not os.path.exists(SESSION_FILE):
        safe_print(f"{now_str()} ❌ Arquivo de sessão '{SESSION_FILE}' não encontrado no container.")
        safe_print("⚠️ Gere a sessão localmente e faça upload do arquivo via painel (Files) do Railway/host.")
        sys.exit(1)

# ============ LOG DE CONFIGURAÇÃO (mascarado) ============
safe_print("=" * 60)
safe_print("✅ INICIANDO (modo seguro). Configurações carregadas:")
safe_print(f"- API_ID: {mask_secret(API_ID)}")
safe_print(f"- API_HASH: {mask_secret(API_HASH)}")
safe_print(f"- BOT_TOKEN: {mask_secret(BOT_TOKEN)}")
safe_print(f"- SESSION_FILE: {SESSION_FILE} (não será exibido conteúdo)")
safe_print(f"- INTERVAL_HOURS: {INTERVAL_HOURS}")
safe_print(f"- LIMIT_MESSAGES: {LIMIT_MESSAGES}")
safe_print(f"- PARES: {len(donor_recipient_pairs)} pares carregados (IDs não mostrados por segurança)")
safe_print("=" * 60)

validate_config_or_exit()

# ============ CLIENTES ============
tele_client = TelegramClient(SESSION_FILE, int(API_ID), API_HASH)
bot = Bot(token=BOT_TOKEN)

# ============ FUNÇÕES PRINCIPAIS ============

async def fetch_random_message(donor_id):
    """Busca uma mensagem RECENTE do canal doador (sempre atual)."""
    try:
        msgs = []
        async for m in tele_client.iter_messages(donor_id, limit=LIMIT_MESSAGES):
            if m is None:
                continue
            # Só aceita texto ou mídia
            if m.text or m.media:
                msgs.append(m)
        if not msgs:
            safe_print(f"{now_str()} ⚠️ Nenhuma mensagem válida encontrada no doador (masked).")
            return None
        return random.choice(msgs)
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro ao ler canal doador (masked): {e}")
        return None

def download_media_bytes_sync(message):
    """
    Baixa mídia para bytes (sincrono). O Telethon tem download_media que normalmente grava em disco.
    Aqui fazemos o download para arquivo temporário e lemos bytes - isso evita expor caminhos no log.
    """
    import tempfile
    try:
        temp = tempfile.NamedTemporaryFile(delete=False)
        path = temp.name
        temp.close()
        # Telethon download_media é async - chamamos via loop no async caller
        return path
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro ao criar temp file: {e}")
        return None

async def send_via_bot(recipient_id, message):
    """
    Envia conteúdo do Telethon via Bot API.
    Faz download da mídia no momento do envio (evita file reference expired).
    Não imprime valores sensíveis.
    """
    try:
        # Álbuns / grouped_id -> coletar todos do mesmo grouped_id
        if getattr(message, "grouped_id", None):
            grouped = []
            async for m in tele_client.iter_messages(message.peer_id, limit=LIMIT_MESSAGES):
                if getattr(m, "grouped_id", None) == message.grouped_id:
                    grouped.append(m)
            # montar envio multipart via envio sequencial (Bot API: enviar vários arquivos individualmente)
            for m in grouped:
                sent = await send_via_bot(recipient_id, m)  # reentrância simples para cada item
                await asyncio.sleep(0.5)
            return True

        # mídia única
        if getattr(message, "photo", None) or getattr(message, "video", None) or getattr(message, "document", None) or getattr(message, "media", None):
            # Baixar para bytes via Telethon (download para arquivo temporário e le leitura)
            temp_path = await message.download_media()
            if not temp_path:
                # fallback para texto
                if message.text:
                    bot.send_message(chat_id=recipient_id, text=message.text or "", parse_mode=ParseMode.HTML)
                    return True
                return False
            # Ler bytes em modo binário e enviar via Bot
            try:
                with open(temp_path, "rb") as fh:
                    data = fh.read()
                # Escolher tipo de envio
                if getattr(message, "photo", None):
                    bot.send_photo(chat_id=recipient_id, photo=data, caption=message.text or "", parse_mode=ParseMode.HTML)
                elif getattr(message, "video", None):
                    bot.send_video(chat_id=recipient_id, video=data, caption=message.text or "", parse_mode=ParseMode.HTML)
                else:
                    # documento / genérico
                    bot.send_document(chat_id=recipient_id, document=data, caption=message.text or "", parse_mode=ParseMode.HTML)
            finally:
                # remove arquivo temporário sem log sensível
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            return True

        # texto puro
        if getattr(message, "text", None):
            bot.send_message(chat_id=recipient_id, text=message.text, parse_mode=ParseMode.HTML)
            return True

        return False

    except TelegramError as te:
        safe_print(f"{now_str()} ❌ Erro Bot API (não vazou token): {str(te)}")
        return False
    except tele_errors.rpcerrorlist.FileReferenceExpiredError as e:
        safe_print(f"{now_str()} ⚠️ File reference expirado: {e}")
        return False
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro inesperado no envio (masked): {e}")
        safe_print(traceback.format_exc())
        return False

# ============ LOOP PRINCIPAL ============
async def forward_loop():
    safe_print(f"{now_str()} 🔄 Iniciando loop seguro. Intervalo: {INTERVAL_HOURS}h")
    sent_cache = {donor: set() for donor in donor_recipient_pairs.keys()}
    while True:
        try:
            # Conferir conexão Telethon
            if not await tele_client.is_connected():
                safe_print(f"{now_str()} 🔁 Telethon desconectado, tentando reconectar...")
                try:
                    await tele_client.connect()
                except Exception as e:
                    safe_print(f"{now_str()} ❌ Falha ao reconectar Telethon (masked): {e}")
                    await asyncio.sleep(60)
                    continue

            for donor_id, recipient_id in donor_recipient_pairs.items():
                try:
                    message = await fetch_random_message(donor_id)
                    if not message:
                        continue

                    # evita reenviar a mesma mensagem repetidamente
                    if message.id in sent_cache[donor_id]:
                        safe_print(f"{now_str()} ⚠️ Mensagem já enviada anteriormente (id masked). Pulando.")
                        continue

                    success = await send_via_bot(recipient_id, message)
                    if success:
                        sent_cache[donor_id].add(message.id)
                        safe_print(f"{now_str()} ✅ Enviado com sucesso (origem masked -> destino masked).")
                    else:
                        safe_print(f"{now_str()} ⚠️ Falha no envio; será tentado no próximo ciclo (masked).")

                    await asyncio.sleep(2)  # evitar flood
                except Exception as inner_e:
                    safe_print(f"{now_str()} ❌ Erro interno ao processar par (masked): {inner_e}")
                    safe_print(traceback.format_exc())
                    # se for erro de conexão, forçar restart do tele_client
                    try:
                        await tele_client.disconnect()
                    except:
                        pass

            safe_print(f"{now_str()} ⏳ Aguardando {INTERVAL_HOURS} horas para próximo envio (masked).")
            await asyncio.sleep(SEND_INTERVAL)

        except Exception as e:
            safe_print(f"{now_str()} 💥 Erro no loop principal (masked): {e}")
            safe_print(traceback.format_exc())
            await asyncio.sleep(60)
            try:
                await tele_client.disconnect()
            except:
                pass

# ============ START =============
async def main():
    safe_print(f"{now_str()} ▶️ Inicializando serviços (modo seguro).")
    # conecta Telethon (usa o arquivo .session provisionado)
    try:
        await tele_client.connect()
        if not await tele_client.is_user_authorized():
            safe_print(f"{now_str()} ❌ Sessão Telethon inválida (verifique o arquivo .session).")
            return
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro ao conectar Telethon (masked): {e}")
        return

    safe_print(f"{now_str()} ✅ Telethon conectado com sucesso (user masked).")
    # Teste rápido do bot (sem mostrar token)
    try:
        me = bot.get_me()
        safe_print(f"{now_str()} ✅ Bot API OK (username masked: {mask_secret(me.username if hasattr(me, 'username') else str(me), keep=6)})")
    except Exception as e:
        safe_print(f"{now_str()} ❌ Falha ao autenticar Bot API (masked): {e}")
        return

    await forward_loop()

if __name__ == "__main__":
    try:
        validate_config_or_exit()
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("\n🛑 Interrompido manualmente.")
    except Exception as e:
        safe_print(f"{now_str()} 💥 Erro fatal (masked): {e}")
        safe_print(traceback.format_exc())
