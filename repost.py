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
        
        self.donor_channel = -1003106957508  # Canal de origem
        self.target_channel = -1003135697010  # Canal de destino
        
        self.min_interval = 1800  # 30 minutos
        self.max_interval = 7200  # 2 horas
        self.timezone = pytz.timezone('America/Sao_Paulo')
        
        self.client = TelegramClient('koyeb_session', self.api_id, self.api_hash)
        self.sent_messages = set()

    async def connect(self):
        """Conecta usando sessão existente"""
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

    def is_media_message(self, message):
        """Verifica se a mensagem contém mídia (imagem, vídeo, documento)"""
        if not message:
            return False
        
        # Verifica se tem mídia
        if hasattr(message, 'media') and message.media:
            return True
        
        # Verifica se é foto, vídeo, documento, sticker, etc.
        if (hasattr(message, 'photo') and message.photo or
            hasattr(message, 'video') and message.video or
            hasattr(message, 'document') and message.document or
            hasattr(message, 'sticker') and message.sticker):
            return True
            
        return False

    async def get_available_media_messages(self):
        """Coleta apenas mensagens com mídia/imagens"""
        try:
            logger.info(f"🔍 Coletando MÍDIAS do canal {self.donor_channel}")
            media_messages = []
            
            async for message in self.client.iter_messages(self.donor_channel, limit=200):
                if message and self.is_media_message(message):
                    msg_id = f"{message.id}_{self.donor_channel}"
                    if msg_id not in self.sent_messages:
                        media_messages.append((message, msg_id))
                        logger.info(f"📸 Mídia encontrada: ID {message.id}")
            
            logger.info(f"🎯 {len(media_messages)} mídias disponíveis para envio")
            return media_messages
            
        except Exception as e:
            logger.error(f"❌ Erro ao coletar mídias: {e}")
            return []

    async def send_random_media(self):
        """Envia uma mídia aleatória"""
        available_media = await self.get_available_media_messages()
        
        if not available_media:
            logger.info("🔄 Todas as mídias enviadas! Reiniciando ciclo...")
            self.sent_messages.clear()
            available_media = await self.get_available_media_messages()
            
            if not available_media:
                logger.warning("📭 Nenhuma mídia disponível no canal")
                return False

        # Seleciona mídia aleatória
        message, msg_id = random.choice(available_media)
        
        try:
            logger.info(f"📤 Enviando mídia ID {message.id}...")
            
            # Encaminha a mensagem com mídia
            await self.client.forward_messages(self.target_channel, [message])
            
            self.sent_messages.add(msg_id)
            logger.info(f"✅ Mídia enviada com sucesso!")
            logger.info(f"   📊 Total de mídias enviadas: {len(self.sent_messages)}")
            logger.info(f"   🎯 Mídias restantes: {len(available_media) - 1}")
            
            return True
            
        except errors.FloodWaitError as e:
            logger.warning(f"⏳ Flood wait: {e.seconds} segundos")
            await asyncio.sleep(e.seconds)
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mídia: {e}")
            return False

    async def run(self):
        """Loop principal - apenas mídias"""
        logger.info("🚀 Iniciando Bot de Repostagem de Mídias...")
        
        if not await self.connect():
            logger.error("❌ Falha na conexão")
            return

        logger.info("🎯 Bot de mídias rodando! Apenas imagens/vídeos serão enviados")
        
        while True:
            try:
                # Envia uma mídia aleatória
                success = await self.send_random_media()
                
                # Calcula próximo intervalo
                wait_time = random.randint(self.min_interval, self.max_interval)
                next_time = datetime.now(self.timezone) + timedelta(seconds=wait_time)
                
                if success:
                    logger.info(f"⏰ Próxima mídia em {wait_time//60} minutos")
                    logger.info(f"   🕒 Horário: {next_time.strftime('%d/%m %H:%M')}")
                else:
                    logger.warning(f"🔄 Nova tentativa em {wait_time//60} minutos")
                
                # Aguarda o intervalo
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Erro no loop principal: {e}")
                logger.info("🔄 Reiniciando em 5 minutos...")
                await asyncio.sleep(300)

async def main():
    bot = TelegramRepostBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
