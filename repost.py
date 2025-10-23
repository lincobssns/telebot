"""
bot_forwarder_simple.py
Bot que envia mídias existentes de um canal para outro a cada 2 horas.
"""

import os
import random
import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "-1003106957508"))
DESTINATION_CHANNEL_ID = int(os.getenv("DESTINATION_CHANNEL_ID", "-1003135697010"))
INTERVAL_HOURS = float(os.getenv("INTERVAL_HOURS", "2"))
TIMEZONE = pytz.timezone(os.getenv("TZ", "America/Sao_Paulo"))

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# =================== FUNÇÕES ===================

def now_str():
    return datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

async def get_all_media_messages(bot, channel_id, limit=1000):
    """Obtém TODAS as mensagens com mídia do canal de origem."""
    try:
        messages = []
        logging.info(f"🔍 Buscando até {limit} mensagens do canal...")
        
        # Busca mensagens do histórico do canal
        async for message in bot.get_chat_history(chat_id=channel_id, limit=limit):
            if (message.photo or message.video or message.audio or 
                message.document or message.animation or message.voice or
                message.sticker):
                messages.append(message)
        
        logging.info(f"📥 Encontradas {len(messages)} mensagens com mídia")
        return messages
    except Exception as e:
        logging.error(f"❌ Erro ao buscar mensagens: {e}")
        return []

async def forward_media_message(bot, source_message, destination_chat_id):
    """Encaminha uma mensagem de mídia para o canal de destino."""
    try:
        await bot.forward_message(
            chat_id=destination_chat_id,
            from_chat_id=source_message.chat.id,
            message_id=source_message.message_id
        )
        logging.info(f"✅ Encaminhado: ID {source_message.message_id}")
        return True
    except Exception as e:
        logging.error(f"❌ Falha ao encaminhar {source_message.message_id}: {e}")
        return False

async def copy_media_message(bot, source_message, destination_chat_id):
    """Copia uma mensagem de mídia (alternativa ao encaminhamento)."""
    try:
        caption = f"🕒 {now_str()}"
        
        if source_message.photo:
            # Pega a foto de maior qualidade (último elemento da lista)
            await bot.send_photo(
                chat_id=destination_chat_id,
                photo=source_message.photo[-1].file_id,
                caption=caption
            )
        elif source_message.video:
            await bot.send_video(
                chat_id=destination_chat_id,
                video=source_message.video.file_id,
                caption=caption
            )
        elif source_message.audio:
            await bot.send_audio(
                chat_id=destination_chat_id,
                audio=source_message.audio.file_id,
                caption=caption
            )
        elif source_message.document:
            await bot.send_document(
                chat_id=destination_chat_id,
                document=source_message.document.file_id,
                caption=caption
            )
        elif source_message.animation:  # GIFs
            await bot.send_animation(
                chat_id=destination_chat_id,
                animation=source_message.animation.file_id,
                caption=caption
            )
        elif source_message.voice:
            await bot.send_voice(
                chat_id=destination_chat_id,
                voice=source_message.voice.file_id,
                caption=caption
            )
        elif source_message.sticker:
            await bot.send_sticker(
                chat_id=destination_chat_id,
                sticker=source_message.sticker.file_id
            )
            return True  # Stickers não têm caption
        
        logging.info(f"✅ Copiado: ID {source_message.message_id}")
        return True
    except Exception as e:
        logging.error(f"❌ Falha ao copiar {source_message.message_id}: {e}")
        return False

async def send_random_media(bot, media_messages, destination_chat_id):
    """Envia uma mídia aleatória para o destino."""
    if not media_messages:
        logging.warning("⚠️ Nenhuma mídia disponível para enviar")
        return False
    
    # Escolhe uma mídia aleatória
    message_to_send = random.choice(media_messages)
    logging.info(f"🎲 Mídia selecionada: ID {message_to_send.message_id}")
    
    # Tenta encaminhar primeiro (mais simples)
    success = await forward_media_message(bot, message_to_send, destination_chat_id)
    
    # Se falhar, tenta copiar
    if not success:
        logging.info("🔄 Tentando copiar...")
        success = await copy_media_message(bot, message_to_send, destination_chat_id)
    
    return success

async def main_loop():
    """Loop principal: envia uma mídia a cada 2 horas."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não definido")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Busca TODAS as mídias do canal de origem uma vez
    logging.info("🔄 Carregando mídias do canal de origem...")
    all_media_messages = await get_all_media_messages(bot, SOURCE_CHANNEL_ID, limit=500)
    
    if not all_media_messages:
        logging.error("❌ Nenhuma mídia encontrada no canal de origem")
        logging.error("💡 Verifique se:")
        logging.error("   1. O bot é ADMIN no canal de origem")
        logging.error("   2. Existem mídias no canal")
        logging.error("   3. O ID do canal está correto")
        return
    
    logging.info("🤖 BOT INICIADO com sucesso!")
    logging.info(f"📥 Canal de origem: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Canal de destino: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
    logging.info(f"📊 Total de mídias: {len(all_media_messages)}")
    logging.info("🔄 Iniciando envio automático...")
    
    # Contador de mídias enviadas
    sent_count = 0
    
    while True:
        try:
            # Envia uma mídia aleatória
            success = await send_random_media(bot, all_media_messages, DESTINATION_CHANNEL_ID)
            
            if success:
                sent_count += 1
                logging.info(f"📈 Total enviado: {sent_count}/{len(all_media_messages)}")
            else:
                logging.error("❌ Falha ao enviar mídia")
            
            # Aguarda o intervalo
            wait_hours = INTERVAL_HOURS
            logging.info(f"⏳ Próximo envio em {wait_hours} horas...")
            await asyncio.sleep(wait_hours * 3600)
            
        except Exception as e:
            logging.error(f"💥 Erro no loop principal: {e}")
            logging.info("🔄 Tentando novamente em 5 minutos...")
            await asyncio.sleep(300)  # Espera 5 minutos antes de tentar novamente

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido manualmente")
