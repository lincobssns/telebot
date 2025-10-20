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
PHONE_NUMBER = '+5541988405232'

# =================== CONFIGURAÇÃO SEGURA ===================
SESSION_NAME = 'telegram_session'
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')
SEND_INTERVAL = 2 * 60 * 60  # 2 horas

# =================== PARES DE CANAIS ===================
donor_recipient_pairs = {
    -1002957443418: -1002646886211,  # Doador -> Receptor
}

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def connect_client():
    """Conecta ao Telegram de forma segura"""
    try:
        if not client.is_connected():
            await client.start(
                phone=PHONE_NUMBER,
                # password=TWO_FA_PASSWORD  # Descomente se tiver 2FA
            )
            print("✅ Conectado ao Telegram com sucesso!")
            return True
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

async def get_messages(donor_id):
    """Obtém mensagens do canal doador"""
    try:
        messages = []
        async for message in client.iter_messages(donor_id, limit=100):
            messages.append(message)
        print(f"📥 Baixadas {len(messages)} mensagens do canal {donor_id}")
        return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
        return []

async def send_random_message(messages, last_sent_indices, recipient_id):
    """Envia mensagem aleatória evitando repetições"""
    if not messages:
        print("⚠️ Nenhuma mensagem disponível para envio")
        return

    available_indices = [i for i in range(len(messages)) if i not in last_sent_indices]
    
    if not available_indices:
        print("🔄 Todas as mensagens foram enviadas, reiniciando ciclo...")
        last_sent_indices.clear()
        available_indices = list(range(len(messages)))

    selected_index = random.choice(available_indices)
    message_to_send = messages[selected_index]

    try:
        await client.forward_messages(recipient_id, message_to_send)
        last_sent_indices.append(selected_index)
        print(f"📤 Mensagem {selected_index + 1} enviada para {recipient_id}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

async def schedule_messages():
    """Agenda envios automáticos"""
    donor_messages = {}
    last_sent_indices = {}

    # Carrega mensagens iniciais
    for donor_id in donor_recipient_pairs.keys():
        messages = await get_messages(donor_id)
        donor_messages[donor_id] = messages
        last_sent_indices[donor_id] = []

    while True:
        try:
            # Verifica conexão
            if not client.is_connected():
                print("🔌 Reconectando...")
                await connect_client()

            now = datetime.now(BR_TIMEZONE)
            print(f"\n🕒 {now.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando envio...")

            # Processa cada par de canais
            for donor_id, recipient_id in donor_recipient_pairs.items():
                await send_random_message(
                    donor_messages[donor_id], 
                    last_sent_indices[donor_id], 
                    recipient_id
                )

            print(f"⏳ Aguardando {SEND_INTERVAL/3600:.0f} horas...")
            await sleep(SEND_INTERVAL)

        except Exception as e:
            print(f"💥 Erro no loop principal: {e}")
            await sleep(60)  # Espera 1 minuto antes de tentar novamente

async def main():
    """Função principal"""
    print("🚀 Iniciando bot...")
    
    if await connect_client():
        await schedule_messages()
    else:
        print("❌ Não foi possível conectar. Verifique suas credenciais.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário")
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
