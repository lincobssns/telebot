# railway_bot.py
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

# =================== CONFIGURAÇÕES DO BOT ===================
BR_TIMEZONE = pytz.timezone('America/Sao_Paulo')
SEND_INTERVAL = 2 * 60 * 60  # 2 horas

donor_recipient_pairs = {
    -1002957443418: -1002646886211,
}

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def connect_with_session():
    """Conecta usando apenas a sessão, sem pedir código"""
    try:
        print("🔗 Conectando com sessão pré-existente...")
        
        # Método que NÃO pede código
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Sessão inválida ou expirada")
            return False
            
        print("✅ Conectado via sessão!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

async def get_messages(donor_id):
    """Obtém mensagens do canal"""
    try:
        messages = []
        async for message in client.iter_messages(donor_id, limit=100):
            if message.text or message.media:
                messages.append(message)
        print(f"📥 {len(messages)} mensagens do canal {donor_id}")
        return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens: {e}")
        return []

async def bot_loop():
    """Loop principal do bot"""
    print("🔄 Iniciando ciclo de envios...")
    
    # Carrega mensagens
    donor_messages = {}
    last_sent_indices = {}
    
    for donor_id in donor_recipient_pairs:
        messages = await get_messages(donor_id)
        donor_messages[donor_id] = messages
        last_sent_indices[donor_id] = []
    
    while True:
        try:
            # Verifica conexão
            if not client.is_connected():
                if not await connect_with_session():
                    print("🔄 Tentando reconectar em 1 minuto...")
                    await asyncio.sleep(60)
                    continue
            
            now = datetime.now(BR_TIMEZONE)
            print(f"\n🎯 {now.strftime('%d/%m/%Y %H:%M:%S')} - Iniciando envio")
            
            # Processa cada canal
            for donor_id, recipient_id in donor_recipient_pairs.items():
                messages = donor_messages[donor_id]
                sent_indices = last_sent_indices[donor_id]
                
                if not messages:
                    continue
                
                # Encontra mensagens não enviadas
                available = [i for i in range(len(messages)) if i not in sent_indices]
                if not available:
                    sent_indices.clear()
                    available = list(range(len(messages)))
                
                # Seleciona e envia
                selected_index = random.choice(available)
                message = messages[selected_index]
                
                try:
                    await client.forward_messages(recipient_id, message)
                    sent_indices.append(selected_index)
                    print(f"📤 Mensagem {selected_index + 1} enviada!")
                except Exception as e:
                    print(f"❌ Erro ao enviar: {e}")
            
            print(f"⏳ Aguardando {SEND_INTERVAL/3600:.1f} horas...")
            await asyncio.sleep(SEND_INTERVAL)
            
        except Exception as e:
            print(f"💥 Erro no loop: {e}")
            await asyncio.sleep(300)

async def main():
    print("=" * 50)
    print("🤖 BOT TELEGRAM - RAILWAY")
    print("=" * 50)
    
    # Verifica se o arquivo de sessão existe
    session_file = f'{SESSION_NAME}.session'
    if not os.path.exists(session_file):
        print(f"❌ Arquivo {session_file} não encontrado!")
        print("💡 Certifique-se de que o arquivo está no Railway")
        return
    
    print("📁 Sessão encontrada, iniciando bot...")
    await bot_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido")
    except Exception as e:
        print(f"💥 Erro fatal: {e}")
