import asyncio
import os
import random
import logging
import base64
from telethon import TelegramClient, errors
from datetime import datetime, timedelta
import pytz
from flask import Flask
from threading import Thread
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(level=logging.INFO, format='%(asime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Servidor de Health Check
app = Flask(__name__)

@app.route('/')
def health_check():
    return 'OK', 200

@app.route('/health')
def health():
    return 'OK', 200

def run_health_server():
    port = int(os.getenv('PORT', 8000))
    logger.info(f"🩺 Servidor de health check na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

class SessionManager:
    @staticmethod
    def load_session():
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
        SessionManager.load_session()
        
        self.api_id = 26949670
        self.api_hash = 'fcb4ebdda2cc008abb37ad9fd9ce3c3a'
        self.donor_channel = -1003106957508
        self.target_channel = -1003135697010
        self.min_interval = 1800
        self.max_interval = 7200
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
        self.client = TelegramClient('koyeb_session', self.api_id, self.api_hash)
        self.sent_messages = set()

    async def connect(self):
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("❌ Sessão inválida! Execute localmente para criar nova sessão.")
                return False
                
            logger.info("✅ Conectado com sessão existente!")
            me = await self.client.get_me()
            logger.info(f"👤 Logado como: {me.first_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro de conexão: {e}")
            return False

    def is_media_message(self, message):
        if not message:
            return False
        return hasattr(message, 'media') and message.media

    async def get_available_media_messages(self):
        try:
            logger.info(f"🔍 Coletando MÍDIAS do canal {self.donor_channel}")
            media_messages = []
            
            async for message in self.client.iter_messages(self.donor_channel, limit=200):
                if message and self.is_media_message(message):
                    msg_id = f"{message.id}_{self.donor_channel}"
                    if msg_id not in self.sent_messages:
                        media_messages.append((message, msg_id))
            
            logger.info(f"🎯 {len(media_messages)} mídias disponíveis")
            return media_messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao coletar mídias: {e}")
            return []

    async def download_and_send_media(self, message):
        try:
            file_path = await message.download_media()
            if not file_path:
                return False
            
            await self.client.send_file(
                self.target_channel,
                file_path,
                caption="",
                supports_streaming=True
            )
            
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mídia: {e}")
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            return False

    async def send_random_media(self):
        available_media = await self.get_available_media_messages()
        
        if not available_media:
            logger.info("🔄 Reiniciando ciclo...")
            self.sent_messages.clear()
            available_media = await self.get_available_media_messages()
            
        if not available_media:
            return False

        message, msg_id = random.choice(available_media)
        
        try:
            logger.info(f"📤 Enviando mídia ID {message.id}...")
            success = await self.download_and_send_media(message)
            
            if success:
                self.sent_messages.add(msg_id)
                logger.info(f"✅ Mídia enviada! Total: {len(self.sent_messages)}")
                return True
            return False
            
        except errors.FloodWaitError as e:
            logger.warning(f"⏳ Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mídia: {e}")
            return False

    async def run(self):
        logger.info("🚀 Iniciando Bot...")
        
        if not await self.connect():
            return

        logger.info("🎯 Bot rodando!")
        
        while True:
            try:
                success = await self.send_random_media()
                
                wait_time = random.randint(self.min_interval, self.max_interval)
                next_time = datetime.now(self.timezone) + timedelta(seconds=wait_time)
                
                if success:
                    logger.info(f"⏰ Próxima em {wait_time//60}min ({next_time.strftime('%H:%M')})")
                else:
                    logger.warning(f"🔄 Tentativa em {wait_time//60}min")
                
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Erro: {e}")
                await asyncio.sleep(300)

async def main():
    health_thread = Thread(target=run_health_server, daemon=True)
    health_thread.start()
    await asyncio.sleep(2)
    
    bot = TelegramRepostBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
