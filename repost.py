import asyncio
import os
import random
import logging
import base64
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SessionManager:
    @staticmethod
    def load_session():
        """Carrega a sessão do environment"""
        session_data = os.getenv('SESSION_DATA')
        if session_data:
            try:
                decoded = base64.b64decode(session_data)
                with open('koyeb_session.session', 'wb') as f:
                    f.write(decoded)
                logger.info("✅ Sessão carregada do environment")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao carregar sessão: {e}")
        return False

class TelegramRepostBot:
    def __init__(self):
        # Carrega sessão primeiro
        SessionManager.load_session()
        
        self.api_id = 26949670
        self.api_hash = 'fcb4ebdda2cc008abb37ad9fd9ce3c3a'
        self.phone = '+5511960188559'
        self.password = 'Isadora44'
        
        self.donor_channel = -1003106957508
        self.target_channel = -1003135697010
        
        self.min_interval = 1800
        self.max_interval = 7200
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
        self.client = TelegramClient('koyeb_session', self.api_id, self.api_hash)
        self.sent_messages = set()

    async def connect(self):
        """Conecta usando sessão existente SEM interação"""
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("❌ Sessão inválida ou expirada")
                return False
                
            logger.info("✅ Conectado com sessão existente!")
            me = await self.client.get_me()
            logger.info(f"👤 Logado como: {me.first_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro de conexão: {e}")
            return False

    async def get_available_messages(self):
        """Coleta mensagens disponíveis"""
        try:
            logger.info(f"🔍 Coletando mensagens do canal {self.donor_channel}")
            messages = []
            async for message in self.client.iter_messages(self.donor_channel, limit=50):
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
        """Envia mensagem aleatória"""
        available = await self.get_available_messages()
        
        if not available:
            logger.info("🔄 Reiniciando ciclo...")
            self.sent_messages.clear()
            available = await self.get_available_messages()
            if not available:
                logger.warning("📭 Nenhuma mensagem disponível")
                return False

        message, msg_id = random.choice(available)
        
        try:
            logger.info(f"📤 Enviando mensagem {message.id}...")
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
        """Loop principal"""
        logger.info("🚀 Iniciando bot...")
        
        if not await self.connect():
            logger.error("❌ Falha na conexão")
            return

        logger.info("🎯 Bot rodando!")
        
        while True:
            try:
                await self.send_random_message()
                
                wait_time = random.randint(self.min_interval, self.max_interval)
                next_time = datetime.now(self.timezone) + timedelta(seconds=wait_time)
                logger.info(f"⏰ Próximo: {wait_time//60}min ({next_time.strftime('%H:%M')})")
                
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Erro: {e}")
                await asyncio.sleep(300)

async def main():
    bot = TelegramRepostBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
