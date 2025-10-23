import asyncio
import os
import random
import logging
from telegram import Bot
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = -1003106957508
DESTINATION_CHANNEL_ID = -1003135697010
INTERVAL_HOURS = 2
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# =================== VARIÁVEIS GLOBAIS ===================
sent_messages = set()

# =================== FUNÇÕES ===================

async def get_recent_media_messages(bot):
    """Busca mídias recentes usando métodos básicos."""
    try:
        logging.info("🔍 Procurando mídias recentes...")
        
        # Vamos tentar acessar algumas mensagens específicas
        # Começando da mensagem mais recente para trás
        media_messages = []
        current_id = 1  # Começa do ID 1
        
        for i in range(500):  # Tenta até 500 mensagens
            try:
                message = await bot.get_message(
                    chat_id=SOURCE_CHANNEL_ID, 
                    message_id=current_id
                )
                
                # Verifica se tem mídia
                if (message.photo or message.video or message.audio or 
                    message.document or message.animation or message.sticker or
                    message.voice):
                    media_messages.append(message)
                    logging.info(f"✅ Encontrada mídia ID {current_id}")
                
                current_id += 1
                
            except Exception:
                # Se não encontrar a mensagem, continua para a próxima
                current_id += 1
                continue
        
        logging.info(f"📊 Total de mídias encontradas: {len(media_messages)}")
        return media_messages
        
    except Exception as e:
        logging.error(f"❌ Erro ao buscar mídias: {e}")
        return []

async def send_media_clean(bot, message):
    """Envia mídia sem forward e sem legenda."""
    try:
        # Envia como nova mídia baseada no tipo
        if message.photo:
            await bot.send_photo(
                chat_id=DESTINATION_CHANNEL_ID,
                photo=message.photo[-1].file_id,
                caption=None
            )
        elif message.video:
            await bot.send_video(
                chat_id=DESTINATION_CHANNEL_ID,
                video=message.video.file_id,
                caption=None
            )
        elif message.document:
            await bot.send_document(
                chat_id=DESTINATION_CHANNEL_ID,
                document=message.document.file_id,
                caption=None
            )
        elif message.audio:
            await bot.send_audio(
                chat_id=DESTINATION_CHANNEL_ID,
                audio=message.audio.file_id,
                caption=None
            )
        elif message.animation:
            await bot.send_animation(
                chat_id=DESTINATION_CHANNEL_ID,
                animation=message.animation.file_id,
                caption=None
            )
        elif message.sticker:
            await bot.send_sticker(
                chat_id=DESTINATION_CHANNEL_ID,
                sticker=message.sticker.file_id
            )
        elif message.voice:
            await bot.send_voice(
                chat_id=DESTINATION_CHANNEL_ID,
                voice=message.voice.file_id,
                caption=None
            )
        elif message.text:
            await bot.send_message(
                chat_id=DESTINATION_CHANNEL_ID,
                text=message.text
            )
        
        logging.info(f"✅ Mídia enviada: ID {message.message_id}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao enviar mídia {message.message_id}: {e}")
        return False

async def test_bot_access(bot):
    """Testa se o bot tem acesso aos canais."""
    try:
        source_chat = await bot.get_chat(chat_id=SOURCE_CHANNEL_ID)
        dest_chat = await bot.get_chat(chat_id=DESTINATION_CHANNEL_ID)
        
        logging.info(f"✅ Acesso ao canal de origem: {source_chat.title}")
        logging.info(f"✅ Acesso ao canal de destino: {dest_chat.title}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro de acesso: {e}")
        return False

async def main_loop():
    """Loop principal do bot."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Testa acesso aos canais
    if not await test_bot_access(bot):
        return
    
    # Busca mídias do canal
    logging.info("🔄 Buscando mídias no canal...")
    media_messages = await get_recent_media_messages(bot)
    
    if not media_messages:
        logging.error("❌ Nenhuma mídia encontrada")
        logging.info("💡 Vamos tentar uma abordagem diferente...")
        logging.info("📝 Envie uma mensagem no canal e note o ID")
        return
    
    logging.info("🤖 BOT INICIADO!")
    logging.info(f"📥 Origem: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Destino: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS}h")
    logging.info(f"📊 Mídias: {len(media_messages)}")
    
    sent_count = 0
    
    while True:
        try:
            # Filtra mídias não enviadas
            available_messages = [msg for msg in media_messages if msg.message_id not in sent_messages]
            
            # Se todas foram enviadas, reinicia
            if not available_messages:
                logging.info("🔄 Todas as mídias enviadas. Reiniciando...")
                sent_messages.clear()
                available_messages = media_messages
            
            # Seleciona mídia aleatória
            selected_message = random.choice(available_messages)
            logging.info(f"🎲 Enviando mídia ID {selected_message.message_id}...")
            
            # Envia como mídia nova
            success = await send_media_clean(bot, selected_message)
            
            if success:
                sent_messages.add(selected_message.message_id)
                sent_count += 1
                logging.info(f"📈 Enviadas: {sent_count}")
            else:
                logging.error("❌ Falha ao enviar mídia")
            
            # Aguarda intervalo
            logging.info(f"⏳ Próxima em {INTERVAL_HOURS} horas...")
            await asyncio.sleep(INTERVAL_HOURS * 3600)
            
        except Exception as e:
            logging.error(f"💥 Erro: {e}")
            await asyncio.sleep(300)

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido")
