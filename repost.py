import asyncio
import os
import random
from telethon import TelegramClient
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
API_ID = int(os.getenv('API_ID', '28881388'))
API_HASH = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
SESSION_NAME = 'telegram_session'

# =================== BOT SETTINGS ===================
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')
SEND_INTERVAL = 2 * 60 * 60  # 2 horas em segundos

# Canal doador -> Canal receptor (VIP)
donor_recipient_pairs = {
    -1002957443418: -1002646886211,
}

# =================== CLIENTE TELEGRAM ===================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# =================== FUNÇÕES ===================

async def connect_with_session():
    """Conecta ao Telegram usando sessão existente."""
    try:
        print("🔗 Conectando com sessão pré-existente...")
        await client.connect()

        if not await client.is_user_authorized():
            print("❌ Sessão inválida ou expirada. Suba o arquivo .session correto.")
            return False

        print("✅ Conectado ao Telegram via sessão!")
        return True

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False


async def get_messages(donor_id):
    """Obtém mensagens (texto + mídias) do canal doador."""
    try:
        messages = []
        async for msg in client.iter_messages(donor_id, limit=100):
            if msg.text or msg.media:
                messages.append(msg)
        print(f"📥 {len(messages)} mensagens coletadas do canal {donor_id}")
        return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens de {donor_id}: {e}")
        return []


async def send_message_safe(message, recipient_id, all_messages):
    """Envia mensagens SEM mostrar 'Forwarded from'."""
    try:
        # Se for álbum (grouped_id)
        if message.grouped_id:
            grouped = [
                m for m in all_messages
                if m.grouped_id == message.grouped_id
            ]
            media_files = []
            for m in grouped:
                if m.media:
                    path = await m.download_media()
                    media_files.append((path, m.text or ""))

            await client.send_file(
                recipient_id,
                [f for f, _ in media_files],
                caption=grouped[0].text or "",
                parse_mode="html"
            )

            for f, _ in media_files:
                os.remove(f)

        # Se for mídia única
        elif message.media:
            file_path = await message.download_media()
            await client.send_file(
                recipient_id,
                file_path,
                caption=message.text or "",
                parse_mode="html"
            )
            os.remove(file_path)

        # Se for apenas texto
        elif message.text:
            await client.send_message(recipient_id, message.text, parse_mode="html")

        print("✅ Mensagem enviada (sem encaminhamento)!")
        return True

    except Exception as ex:
        print(f"❌ Erro ao enviar mensagem: {ex}")
        return False


async def bot_loop():
    """Loop principal do bot (envia 1 mídia a cada 2 horas)."""
    print("🔄 Iniciando ciclo principal...")

    # Coleta inicial das mensagens
    donor_messages = {}
    last_sent_indices = {}

    for donor_id in donor_recipient_pairs:
        messages = await get_messages(donor_id)
        donor_messages[donor_id] = messages
        last_sent_indices[donor_id] = []

    while True:
        try:
            # Garante conexão ativa
            if not client.is_connected():
                if not await connect_with_session():
                    print("🔄 Tentando reconectar em 1 minuto...")
                    await asyncio.sleep(60)
                    continue

            now = datetime.now(BR_TIMEZONE)
            print(f"\n🕒 {now.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando envio...")

            # Processa um envio por ciclo
            for donor_id, recipient_id in donor_recipient_pairs.items():
                messages = donor_messages[donor_id]
                sent_indices = last_sent_indices[donor_id]

                if not messages:
                    print("⚠️ Nenhuma mensagem disponível no canal doador.")
                    continue

                # Escolhe mensagem ainda não enviada
                available = [i for i in range(len(messages)) if i not in sent_indices]
                if not available:
                    sent_indices.clear()
                    available = list(range(len(messages)))

                selected_index = random.choice(available)
                msg = messages[selected_index]

                success = await send_message_safe(msg, recipient_id, messages)
                if success:
                    sent_indices.append(selected_index)

                # Pequena pausa antes de finalizar o ciclo
                await asyncio.sleep(3)

            print(f"⏳ Próximo envio em {SEND_INTERVAL/3600:.1f} horas...\n")
            await asyncio.sleep(SEND_INTERVAL)

        except Exception as e:
            print(f"💥 Erro no loop principal: {e}")
            await asyncio.sleep(120)  # espera 2 min antes de tentar novamente


async def main():
    print("=" * 50)
    print("🤖 BOT TELEGRAM - RAILWAY MEDIA FORWARDER")
    print("=" * 50)

    # Verifica sessão existente
    if not os.path.exists(f"{SESSION_NAME}.session"):
        print(f"❌ Arquivo de sessão '{SESSION_NAME}.session' não encontrado!")
        print("💡 Faça login localmente com Telethon para gerar o arquivo e suba no Railway.")
        return

    if not await connect_with_session():
        print("❌ Falha na autenticação via sessão.")
        return

    await bot_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido manualmente.")
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
