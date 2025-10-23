# bot.py - Código completo com suporte a sessão Base64
import asyncio
import os
import random
import logging
import base64
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
import pytz

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SessionManager:
    @staticmethod
    def load_session_from_env():
        """Carrega a sessão das variáveis de ambiente Base64"""
        session_data_b64 = os.getenv('SESSION_DATA')
        session_journal_b64 = os.getenv('SESSION_JOURNAL')
        
        if session_data_b64:
            try:
                # Decodifica e salva a sessão principal
                decoded_session = base64.b64decode(session_data_b64)
                with open('telegram_session.session', 'wb') as f:
                    f.write(decoded_session)
                logger.info("✅ Sessão principal carregada do environment")
                
                # Se existir journal, salva também
                if session_journal_b64:
                    decoded_journal = base64.b64decode(session_journal_b64)
                    with open('telegram_session.session-journal', 'wb') as f:
                        f.write(decoded_journal)
                    logger.info("✅ Journal da sessão carregado")
                
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao carregar sessão: {e}")
                return False
        return False

class TelegramRepostBot:
    def __init__(self):
        # Carrega a sessão primeiro
        SessionManager.load_session_from_env()
        
        # Configurações do Telegram
        self.api_id = int(os.getenv('API_ID', '28881388'))
        self.api_hash = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
        self.phone = os.getenv('PHONE_NUMBER', '+5541988405232')
        self.password = os.getenv('TWO_FA_PASSWORD', '529702')
        self.session_name = 'telegram_session'  # Nome fixo
        
        # Configuração de canais
        pairs_str = os.getenv('CHANNEL_PAIRS', '-1002877945842:-1002760356238')
        donor, target = pairs_str.split(':')
        self.donor_channel = int(donor.strip())
        self.target_channel = int(target.strip())
        
        # Intervalos
        self.min_interval = int(os.getenv('MIN_INTERVAL', '1800'))
        self.max_interval = int(os.getenv('MAX_INTERVAL', '7200'))
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
        # Estado
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        self.sent_messages = set()
        
        logger.info("🤖 Bot inicializado com suporte a sessão Base64")

    async def connect(self):
        """Conecta ao Telegram usando sessão existente"""
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("❌ Sessão inválida ou expirada")
                return False
                
            logger.info("✅ Conectado ao Telegram com sessão existente!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro de conexão: {e}")
            return False

    async def get_available_messages(self):
        """Coleta mensagens não enviadas"""
        try:
            messages = []
            async for message in self.client.iter_messages(self.donor_channel, limit=100):
                if message and not message.empty:
                    msg_id = f"{message.id}_{self.donor_channel}"
                    if msg_id not in self.sent_messages:
                        messages.append((message, msg_id))
            
            logger.info(f"📥 {len(messages)} mensagens disponíveis")
            return messages
        except Exception as e:
            logger.error(f"❌ Erro ao coletar mensagens: {e}")
            return []

    async def send_random_message(self):
        """Envia uma mensagem aleatória"""
        available_messages = await self.get_available_messages()
        
        if not available_messages:
            logger.info("🔄 Todas as mensagens foram enviadas! Reiniciando ciclo...")
            self.sent_messages.clear()
            available_messages = await self.get_available_messages()
            
            if not available_messages:
                logger.warning("📭 Nenhuma mensagem disponível no canal")
                return False

        message, msg_id = random.choice(available_messages)
        
        try:
            await self.client.forward_messages(self.target_channel, [message])
            self.sent_messages.add(msg_id)
            logger.info(f"✅ Mensagem enviada! Total: {len(self.sent_messages)}")
            return True
            
        except errors.FloodWaitError as e:
            logger.warning(f"⏳ Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar: {e}")
            return False

    async def run(self):
        """Loop principal do bot"""
        logger.info("🚀 Iniciando Telegram Repost Bot...")
        
        if not await self.connect():
            logger.error("❌ Falha na conexão. Encerrando.")
            return

        logger.info("🎯 Bot rodando no Koyeb com sessão persistente!")
        
        while True:
            try:
                success = await self.send_random_message()
                
                wait_time = random.randint(self.min_interval, self.max_interval)
                next_time = datetime.now(self.timezone) + timedelta(seconds=wait_time)
                
                if success:
                    logger.info(f"⏰ Próximo: {wait_time//60}min ({next_time.strftime('%H:%M')})")
                else:
                    logger.warning(f"🔄 Tentativa em {wait_time//60}min")
                
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Erro: {e}")
                await asyncio.sleep(300)

async def main():
    bot = TelegramRepostBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
