# railway_bot.py - Para usar no Railway
import asyncio
import os
import random
from telethon import TelegramClient
from asyncio import sleep
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
API_ID = int(os.getenv('API_ID', '28881388'))
API_HASH = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '+5541988405232')

SESSION_NAME = 'telegram_session'
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')
SEND_INTERVAL = 2 * 60 * 60  # 2 horas

donor_recipient_pairs = {
    -1002957443418: -1002646886211,
}

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def connect_client():
    """Conecta usando sessão existente"""
    try:
        print("🔗 Conectando com sessão existente...")
        await client.start(phone=PHONE_NUMBER)
        
        if await client.is_user_authorized():
            print("✅ Sessão autorizada com sucesso!")
            return True
        else:
            print("❌ Sessão não autorizada")
            return False
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

async def get_messages(donor_id):
    """Obtém mensagens do canal doador"""
    try:
        messages = []
        async for message in client.iter_messages(donor_id, limit=50):
            if message.text or message.media:
                messages.append(message)
        print(f"📥 {len(messages)} mensagens do canal {donor_id}")
        return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
        return []

async def send_random_message(messages, last_sent_indices, recipient_id):
    """Envia mensagem aleatória"""
    if not messages:
        return

    available_indices = [i for i in range(len(messages)) if i not in last_sent_indices]
    
    if not available_indices:
        last_sent_indices.clear()
        available_indices = list(range(len(messages)))

    selected_index = random.choice(available_indices)
    message_to_send = messages[selected_index]

    try:
        await client.forward_messages(recipient_id, message_to_send)
        last_sent_indices.append(selected_index)
        print(f"📤 Mensagem {selected_index + 1} enviada!")
    except Exception as e:
        print(f"❌ Erro ao enviar: {e}")

async def schedule_messages():
    """Agenda envios automáticos"""
    print("🔄 Iniciando agendamento...")
    
    donor_messages = {}
    last_sent_indices = {}

    for donor_id in donor_recipient_pairs.keys():
        donor_messages[donor_id] = await get_messages(donor_id)
        last_sent_indices[donor_id] = []

    while True:
        try:
            now = datetime.now(BR_TIMEZONE)
            print(f"\n🕒 {now.strftime('%d/%m/%Y %H:%M:%S')} - Ciclo iniciado")

            for donor_id, recipient_id in donor_recipient_pairs.items():
                await send_random_message(
                    donor_messages[donor_id], 
                    last_sent_indices[donor_id], 
                    recipient_id
                )

            print(f"⏳ Aguardando {SEND_INTERVAL/3600:.0f} horas...")
            await sleep(SEND_INTERVAL)

        except Exception as e:
            print(f"💥 Erro: {e}")
            await sleep(300)

async def main():
    print("🚀 Bot iniciando no Railway...")
    
    if await connect_client():
        me = await client.get_me()
        print(f"👤 Conectado como: {me.first_name}")
        await schedule_messages()
    else:
        print("❌ Execute localmente primeiro para criar a sessão")

if __name__ == "__main__":
    asyncio.run(main())
