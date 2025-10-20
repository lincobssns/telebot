import asyncio
import os
import random
from telethon import TelegramClient
from asyncio import sleep
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES DO TELEGRAM ===================
API_ID = 28881388
API_HASH = 'd9e8b04bb4a85f373cc9ba4692dd6cf4'
PHONE_NUMBER = '+5541988405232'  # Substitua pelo seu número de telefone
# =================== PARES DE CANAIS ===================
donor_recipient_pairs = {
    -1002957443418: -1002646886211,  # Doador -> Receptor
}

# =================== CONFIGURAÇÕES DO SISTEMA ===================
SESSION_NAME = 'telegram_session'
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')

# Intervalo de 2 horas
SEND_INTERVAL = 2 * 60 * 60  # 2 horas em segundos

# =================== INICIALIZAÇÃO DO TELETHON ===================
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# =================== FUNÇÕES ===================

async def connect_client():
    """Conecta ao Telegram com autenticação."""
    try:
        await client.start(PHONE_NUMBER, password=TWO_FA_PASSWORD)
        print("✅ Conectado ao Telegram com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        exit(1)

async def get_messages(donor_id):
    """Obtém todas as mensagens de um canal doador."""
    messages = []
    async for message in client.iter_messages(donor_id):
        messages.append(message)
    return messages

async def send_random_message(messages, last_sent_indices, recipient_id):
    """Envia uma mensagem aleatória, evitando repetições."""
    available_messages = [i for i in range(len(messages)) if i not in last_sent_indices]

    if not available_messages:
        last_sent_indices.clear()
        available_messages = list(range(len(messages)))

    selected_index = random.choice(available_messages)
    original_message = messages[selected_index]

    # Se for álbum (múltiplas mídias agrupadas)
    if original_message.grouped_id:
        grouped_messages = [msg for msg in messages if msg.grouped_id == original_message.grouped_id]
        grouped_indices = [idx for idx, msg in enumerate(messages) if msg.grouped_id == original_message.grouped_id]
    else:
        grouped_messages = [original_message]
        grouped_indices = [selected_index]

    for attempt in range(5):  # Tenta até 5 vezes
        try:
            await client.forward_messages(
                recipient_id,
                grouped_messages,
                from_peer=grouped_messages[0].peer_id
            )
            last_sent_indices.extend(grouped_indices)
            print(f"📤 Mensagem encaminhada com sucesso para {recipient_id}.")
            break
        except Exception as e:
            print(f"⚠️ Tentativa {attempt + 1} falhou ao enviar: {e}")
            await sleep(2)

    else:  # Se falhar em todas as tentativas, envia manualmente
        print("⚙️ Tentando envio manual...")
        try:
            for msg in grouped_messages:
                if msg.photo or msg.video or msg.document:
                    file_path = await msg.download_media()
                    await client.send_file(
                        recipient_id,
                        file_path,
                        caption=msg.text or "",
                        parse_mode="html"
                    )
                    os.remove(file_path)
                elif msg.text:
                    await client.send_message(recipient_id, msg.text, parse_mode="html")
        except Exception as ex:
            print(f"❌ Erro ao enviar manualmente: {ex}")

async def schedule_messages():
    """Agenda o envio automático a cada 2 horas."""
    donor_messages = {}
    last_sent_indices = {}

    # Coleta inicial de mensagens
    for donor_id in donor_recipient_pairs.keys():
        messages = await get_messages(donor_id)
        donor_messages[donor_id] = messages
        last_sent_indices[donor_id] = []

    while True:
        now = datetime.now(BR_TIMEZONE)
        print(f"\n🕒 {now.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando ciclo de envio...")

        for donor_id, recipient_id in donor_recipient_pairs.items():
            await send_random_message(donor_messages[donor_id], last_sent_indices[donor_id], recipient_id)

        print(f"✅ Ciclo concluído. Aguardando {SEND_INTERVAL / 3600:.0f} horas até o próximo envio...\n")
        await sleep(SEND_INTERVAL)

async def main():
    print("🚀 Bot iniciado. Aguardando o próximo envio automático...")
    await connect_client()
    await schedule_messages()

if __name__ == "__main__":
    asyncio.run(main())
