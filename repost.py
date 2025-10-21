# railway_bot.py
import asyncio
import os
import random
import sys
import traceback
from telethon import TelegramClient, errors
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
API_ID = int(os.getenv('API_ID', '28881388'))
API_HASH = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_session')  # telegram_session.session
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')

# Intervalo configurável em horas (padrão 2)
INTERVAL_HOURS = float(os.getenv('INTERVAL_HOURS', '2'))
SEND_INTERVAL = int(INTERVAL_HOURS * 3600)

# Quantas mensagens recentes buscar do canal doador quando for enviar (padrão 100)
LIMIT_MESSAGES = int(os.getenv('LIMIT_MESSAGES', '100'))

# Par de doador -> receptor
donor_recipient_pairs = {
    -1002957443418: -1002646886211,  # ajuste conforme necessário
}

# Cliente Telethon
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# =================== UTIL ===================
def now_str():
    return datetime.now(BR_TIMEZONE).strftime('%d/%m/%Y %H:%M:%S')

def safe_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

# =================== CONEXÃO ===================
async def connect_with_session(force_reconnect=False):
    """Conecta usando a sessão existente; retorna True se ok."""
    try:
        safe_print(f"{now_str()} 🔗 Tentando conectar via sessão (force_reconnect={force_reconnect})...")
        if force_reconnect:
            try:
                await client.disconnect()
            except Exception:
                pass

        await client.connect()
        # garante autorizado
        if not await client.is_user_authorized():
            safe_print(f"{now_str()} ❌ Sessão inválida ou expirada.")
            return False

        # limpa updates pendentes
        try:
            await client.get_dialogs(limit=1)
        except Exception:
            # não crítico
            pass

        safe_print(f"{now_str()} ✅ Conectado ao Telegram via sessão!")
        return True

    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro na conexão: {e}")
        return False

# =================== ENVIO SEGURO ===================
async def fetch_random_message_from_donor(donor_id):
    """
    Busca uma mensagem RECENTE do canal doador (sempre atual).
    Retorna Telethon Message ou None.
    """
    try:
        msgs = []
        async for m in client.iter_messages(donor_id, limit=LIMIT_MESSAGES):
            if m is None:
                continue
            if m.text or m.media:
                msgs.append(m)
        if not msgs:
            return None
        return random.choice(msgs)
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro ao buscar mensagens do {donor_id}: {e}")
        return None

async def download_media_safe(message):
    """Baixa a mídia e retorna o caminho do arquivo (ou lista de caminhos se álbum)."""
    # Se álbum (grouped_id), retorna lista de (path, text)
    if message.grouped_id:
        grouped = []
        async for m in client.iter_messages(message.peer_id, limit=LIMIT_MESSAGES):
            # coletamos os que possuem mesmo grouped_id
            if getattr(m, "grouped_id", None) == message.grouped_id:
                grouped.append(m)
        media_files = []
        for m in grouped:
            if m.media:
                path = await m.download_media()
                media_files.append((path, m.text or ""))
        return media_files  # list of tuples
    else:
        if message.media:
            path = await message.download_media()
            return path
        return None

async def send_message_no_forward(message, recipient_id):
    """
    Envia uma única mensagem ao recipient_id sem mostrar 'Forwarded from'.
    Faz download no momento do envio (evita file reference expired).
    """
    try:
        # Álbum
        if message.grouped_id:
            # buscar novamente o álbum diretamente do canal (garante referências válidas)
            grouped = []
            async for m in client.iter_messages(message.peer_id, limit=LIMIT_MESSAGES):
                if getattr(m, "grouped_id", None) == message.grouped_id:
                    grouped.append(m)
            # baixar mídia
            media_files = []
            for m in grouped:
                if m.media:
                    p = await m.download_media()
                    media_files.append((p, m.text or ""))

            if media_files:
                await client.send_file(
                    recipient_id,
                    [p for p, _ in media_files],
                    caption=grouped[0].text or "",
                    parse_mode="html",
                )
                for p, _ in media_files:
                    try: os.remove(p)
                    except: pass
                return True
            # fallback: if none had media but text present
            if grouped and grouped[0].text:
                await client.send_message(recipient_id, grouped[0].text, parse_mode="html")
                return True
            return False

        # Mídia única
        if message.media:
            # refetch the message fresh (by id) to ensure valid file reference
            try:
                fresh = await client.get_messages(message.peer_id, ids=message.id)
                if fresh:
                    message = fresh
            except Exception:
                # não crítico, prossegue com a message original
                pass

            file_path = await message.download_media()
            if file_path:
                await client.send_file(recipient_id, file_path, caption=message.text or "", parse_mode="html")
                try: os.remove(file_path)
                except: pass
                return True
            else:
                # se download não retornou caminho, tenta enviar texto
                if message.text:
                    await client.send_message(recipient_id, message.text, parse_mode="html")
                    return True
                return False

        # Apenas texto
        if message.text:
            await client.send_message(recipient_id, message.text, parse_mode="html")
            return True

        return False

    except errors.rpcerrorlist.FileReferenceExpiredError as e:
        # file reference expirado — avisar e retornar False para tentar próxima vez
        safe_print(f"{now_str()} ⚠️ File reference expired: {e}")
        return False
    except errors.FloodWaitError as e:
        safe_print(f"{now_str()} ⛔ Flood wait: {e}. Dormindo {e.seconds}s")
        await asyncio.sleep(e.seconds + 2)
        return False
    except Exception as e:
        safe_print(f"{now_str()} ❌ Erro ao enviar sem forward: {e}")
        safe_print(traceback.format_exc())
        return False

# =================== LOOP PRINCIPAL ===================
async def bot_loop():
    safe_print(f"{now_str()} 🔄 Iniciando ciclo principal (envio cada {INTERVAL_HOURS}h)...")
    # Guarda índices enviados para evitar repetição imediata enquanto o processo roda
    last_sent = {donor: set() for donor in donor_recipient_pairs}

    backoff_seconds = 5

    while True:
        try:
            # Assegura conexão
            if not client.is_connected():
                ok = await connect_with_session(force_reconnect=True)
                if not ok:
                    safe_print(f"{now_str()} 🔁 Falha ao conectar — tentando em 60s...")
                    await asyncio.sleep(60)
                    continue
                # limpa pequenas inconsistências
                try: await client.get_dialogs(limit=1)
                except: pass

            safe_print(f"\n{now_str()} 🕒 Iniciando ciclo de envio...")
            for donor_id, recipient_id in donor_recipient_pairs.items():
                try:
                    # Busca uma mensagem sempre ao enviar (garante referências válidas)
                    message = await fetch_random_message_from_donor(donor_id)
                    if not message:
                        safe_print(f"{now_str()} ⚠️ Nenhuma mensagem encontrada no doador {donor_id}")
                        continue

                    # Evita reenviar a mesma mensagem se já enviada recentemente
                    attempts = 0
                    while message.id in last_sent[donor_id] and attempts < 5:
                        message = await fetch_random_message_from_donor(donor_id)
                        attempts += 1

                    success = await send_message_no_forward(message, recipient_id)
                    if success:
                        last_sent[donor_id].add(message.id)
                        # mantém apenas últimas 500 ids para não crescer indefinidamente
                        if len(last_sent[donor_id]) > 500:
                            # remove alguns aleatoriamente
                            to_remove = list(last_sent[donor_id])[:100]
                            for r in to_remove:
                                last_sent[donor_id].remove(r)
                        safe_print(f"{now_str()} ✅ Enviado do {donor_id} -> {recipient_id} (msg id {message.id})")
                    else:
                        safe_print(f"{now_str()} ⚠️ Falha ao enviar mensagem id {getattr(message, 'id', 'n/a')}, será tentada no próximo ciclo")

                    # Pausa curta entre envios para evitar flood
                    await asyncio.sleep(2)

                except Exception as inner:
                    safe_print(f"{now_str()} ❌ Erro ao processar par {donor_id}->{recipient_id}: {inner}")
                    safe_print(traceback.format_exc())
                    # Se for erro de conexão, reinicia o client
                    if isinstance(inner, (ConnectionResetError, errors.rpcerrorlist.RPCError)):
                        try:
                            await client.disconnect()
                        except: pass

            safe_print(f"{now_str()} ⏳ Próximo envio em {INTERVAL_HOURS:.1f} horas...")
            backoff_seconds = 5  # reset backoff after successful cycle
            await asyncio.sleep(SEND_INTERVAL)

        except Exception as e:
            safe_print(f"{now_str()} 💥 Erro no loop principal: {e}")
            safe_print(traceback.format_exc())
            # Tentativa de recuperação com backoff exponencial
            await asyncio.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 600)
            try:
                await client.disconnect()
            except:
                pass

# =================== MAIN ===================
async def main():
    safe_print("=" * 50)
    safe_print("🤖 BOT TELEGRAM - RAILWAY MEDIA FORWARDER (Aprimorado)")
    safe_print("=" * 50)

    # Verifica sessão existente
    session_file = f"{SESSION_NAME}.session"
    if not os.path.exists(session_file):
        safe_print(f"{now_str()} ❌ Arquivo de sessão '{session_file}' não encontrado!")
        safe_print("💡 Gere a sessão localmente com Telethon (ou suba o arquivo .session correto).")
        return

    if not await connect_with_session():
        safe_print(f"{now_str()} ❌ Falha na autenticação via sessão. Certifique-se de subir o arquivo .session gerado localmente.")
        return

    # Inicia loop principal
    await bot_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("\n🛑 Bot interrompido manualmente.")
    except Exception as e:
        safe_print(f"💥 Erro fatal de execução: {e}")
        safe_print(traceback.format_exc())
