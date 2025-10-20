import asyncio
import os
import random
from telethon import TelegramClient
from asyncio import sleep
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
API_ID = 28881388
API_HASH = 'd9e8b04bb4a85f373cc9ba4692dd6cf4'
PHONE_NUMBER = '+5541988405232'

SESSION_NAME = 'telegram_session'
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')
SEND_INTERVAL = 2 * 60 * 60  # 2 horas

# =================== PARES DE CANAIS ===================
donor_recipient_pairs = {
    -1002957443418: -1002646886211,  # Doador -> Receptor
}

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def connect_client():
    """Conecta ao Telegram com tratamento de login"""
    try:
        print("🔗 Conectando ao Telegram...")
        
        await client.start(
            phone=PHONE_NUMBER,
            code_callback=lambda: input("📱 Digite o código recebido: ")
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
        async for message in client.iter_messages(donor_id, limit=50):  # Limite reduzido para teste
            messages.append(message)
        print(f"📥 Baixadas {len(messages)} mensagens do canal {donor_id}")
        return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
        return []

async def send_random_message(messages, last_sent_indices, recipient_id):
    """Envia mensagem aleatória"""
    if not messages:
        print("⚠️ Nenhuma mensagem disponível")
        return

    available_indices = [i for i in range(len(messages)) if i not in last_sent_indices]
    
    if not available_indices:
        print("🔄 Reiniciando ciclo de mensagens...")
        last_sent_indices.clear()
        available_indices = list(range(len(messages)))

    selected_index = random.choice(available_indices)
    message_to_send = messages[selected_index]

    try:
        await client.forward_messages(recipient_id, message_to_send)
        last_sent_indices.append(selected_index)
        print(f"📤 Mensagem {selected_index + 1} enviada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")

async def schedule_messages():
    """Agenda envios automáticos"""
    print("🔄 Carregando mensagens...")
    
    donor_messages = {}
    last_sent_indices = {}

    # Carrega mensagens
    for donor_id in donor_recipient_pairs.keys():
        messages = await get_messages(donor_id)
        donor_messages[donor_id] = messages
        last_sent_indices[donor_id] = []

    print("⏰ Agendamento iniciado...")
    
    while True:
        try:
            now = datetime.now(BR_TIMEZONE)
            print(f"\n🕒 {now.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando envio...")

            for donor_id, recipient_id in donor_recipient_pairs.items():
                await send_random_message(
                    donor_messages[donor_id], 
                    last_sent_indices[donor_id], 
                    recipient_id
                )

            print(f"⏳ Próximo envio em {SEND_INTERVAL/3600:.0f} horas...")
            await sleep(SEND_INTERVAL)

        except Exception as e:
            print(f"💥 Erro no agendamento: {e}")
            await sleep(300)  # 5 minutos antes de tentar novamente

async def main():
    """Função principal"""
    print("🚀 Iniciando Bot do Telegram")
    print("=" * 40)
    
    if await connect_client():
        me = await client.get_me()
        print(f"👤 Logado como: {me.first_name}")
        print("✅ Bot iniciado com sucesso!")
        await schedule_messages()
    else:
        print("❌ Falha na inicialização")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário")
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
