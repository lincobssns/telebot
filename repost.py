# bot.py - Código completo com suporte a variáveis de ambiente
import asyncio
import os
import random
import logging
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

class TelegramRepostBot:
    def __init__(self):
        # Carrega das variáveis de ambiente com fallback
        self.api_id = int(os.getenv('API_ID', '28881388'))
        self.api_hash = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
        self.phone = os.getenv('PHONE_NUMBER', '+5541988405232')
        self.password = os.getenv('TWO_FA_PASSWORD', '529702')
        self.session_name = os.getenv('SESSION_NAME', 'telegram_session')
        
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
        
        logger.info("🤖 Bot inicializado com configurações:")
        logger.info(f"   📱 Sessão: {self.session_name}")
        logger.info(f"   ⏰ Intervalo: {self.min_interval//60}-{self.max_interval//60}min")
        logger.info(f"   📊 Canais: {self.donor_channel} → {self.target_channel}")

    async def connect(self):
        """Conecta ao Telegram"""
        try:
            await self.client.start(phone=self.phone, password=self.password)
            logger.info("✅ Conectado ao Telegram com sucesso!")
            return True
        except errors.SessionPasswordNeededError:
            logger.error("❌ Senha 2FA incorreta")
            return False
        except Exception as e:
            logger.error(f"❌ Erro de conexão: {e}")
            return False

    async def get_available_messages(self):
        """Coleta mensagens não enviadas"""
        try:
            messages = []
            async for message in self.client.iter_messages(self.donor_channel, limit=100):
                if message and not message.empty:
                    # Cria um ID único para a mensagem
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
        
        # Se não há mensagens, reinicia o ciclo
        if not available_messages:
            logger.info("🔄 Todas as mensagens foram enviadas! Reiniciando ciclo...")
            self.sent_messages.clear()
            available_messages = await self.get_available_messages()
            
            if not available_messages:
                logger.warning("📭 Nenhuma mensagem disponível no canal")
                return False

        # Seleciona mensagem aleatória
        message, msg_id = random.choice(available_messages)
        
        try:
            await self.client.forward_messages(self.target_channel, [message])
            self.sent_messages.add(msg_id)
            logger.info(f"✅ Mensagem enviada com sucesso!")
            logger.info(f"   📊 Total enviadas: {len(self.sent_messages)}")
            logger.info(f"   🎯 Restantes: {len(available_messages) - 1}")
            return True
            
        except errors.FloodWaitError as e:
            logger.warning(f"⏳ Flood wait detectado: {e.seconds} segundos")
            await asyncio.sleep(e.seconds)
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem: {e}")
            return False

    async def run(self):
        """Loop principal do bot"""
        logger.info("🚀 Iniciando Telegram Repost Bot...")
        
        if not await self.connect():
            logger.error("❌ Falha na conexão. Encerrando.")
            return

        logger.info("🎯 Bot iniciado com sucesso no Koyeb!")
        
        while True:
            try:
                # Tenta enviar uma mensagem
                success = await self.send_random_message()
                
                # Calcula próximo intervalo
                wait_time = random.randint(self.min_interval, self.max_interval)
                next_time = datetime.now(self.timezone) + timedelta(seconds=wait_time)
                
                if success:
                    logger.info(f"⏰ Próximo envio em {wait_time//60} minutos")
                    logger.info(f"   🕒 Horário: {next_time.strftime('%d/%m %H:%M')}")
                else:
                    logger.warning(f"🔄 Nova tentativa em {wait_time//60} minutos")
                
                # Aguarda o intervalo
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"💥 Erro no loop principal: {e}")
                logger.info("🔄 Reiniciando em 5 minutos...")
                await asyncio.sleep(300)  # 5 minutos

async def main():
    bot = TelegramRepostBot()
    await bot.run()

if __name__ == "__main__":
    # Verifica se está rodando no Koyeb
    if os.getenv('KOYEB_APP') or os.getenv('KOYEB_SERVICE'):
        logger.info("🌐 Ambiente Koyeb detectado")
    
    asyncio.run(main())
