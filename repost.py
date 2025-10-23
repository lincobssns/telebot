import asyncio
import os
import random
import logging
from telegram import Bot
from datetime import datetime
import pytz

# =================== CONFIGURAÇÕES ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Token do seu bot
SOURCE_CHANNEL_ID = -1003106957508  # Canal de origem (onde o bot é admin)
DESTINATION_CHANNEL_ID = -1003135697010  # Canal de destino
INTERVAL_HOURS = 2  # Intervalo de 2 horas
TIMEZONE = pytz.timezone('America/Sao_Paulo')

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# =================== VARIÁVEIS GLOBAIS ===================
sent_messages = set()  # Armazena IDs das mensagens já enviadas
media_messages = []    # Armazena todas as mídias do canal

# =================== FUNÇÕES ===================

def now_str():
    return datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

async def get_media_messages(bot, source_channel_id):
    """Busca todas as mensagens com mídia do canal de origem."""
    try:
        messages = []
        logging.info("🔍 Buscando mídias no canal de origem...")
        
        # Usa get_chat_history para buscar mensagens
        async for message in bot.get_chat_history(chat_id=source_channel_id, limit=1000):
            if (message.photo or message.video or message.audio or 
                message.document or message.animation or message.voice or
                message.sticker):
                messages.append(message)
        
        logging.info(f"📥 Encontradas {len(messages)} mensagens com mídia")
        return messages
    except Exception as e:
        logging.error(f"❌ Erro ao buscar mídias: {e}")
        return []

async def forward_media_message(bot, source_message, destination_channel_id):
    """Encaminha uma mensagem de mídia para o canal de destino."""
    try:
        await bot.forward_message(
            chat_id=destination_channel_id,
            from_chat_id=source_message.chat.id,
            message_id=source_message.message_id
        )
        logging.info(f"✅ Encaminhado: ID {source_message.message_id}")
        return True
    except Exception as e:
        logging.error(f"❌ Falha ao encaminhar {source_message.message_id}: {e}")
        return False

async def copy_media_message(bot, source_message, destination_channel_id):
    """Copia uma mensagem de mídia (alternativa ao encaminhamento)."""
    try:
        caption = f"🕒 {now_str()}"
        
        if source_message.photo:
            await bot.send_photo(
                chat_id=destination_channel_id,
                photo=source_message.photo[-1].file_id,
                caption=caption
            )
        elif source_message.video:
            await bot.send_video(
                chat_id=destination_channel_id,
                video=source_message.video.file_id,
                caption=caption
            )
        elif source_message.audio:
            await bot.send_audio(
                chat_id=destination_channel_id,
                audio=source_message.audio.file_id,
                caption=caption
            )
        elif source_message.document:
            await bot.send_document(
                chat_id=destination_channel_id,
                document=source_message.document.file_id,
                caption=caption
            )
        elif source_message.animation:
            await bot.send_animation(
                chat_id=destination_channel_id,
                animation=source_message.animation.file_id,
                caption=caption
            )
        elif source_message.voice:
            await bot.send_voice(
                chat_id=destination_channel_id,
                voice=source_message.voice.file_id,
                caption=caption
            )
        elif source_message.sticker:
            await bot.send_sticker(
                chat_id=destination_channel_id,
                sticker=source_message.sticker.file_id
            )
            return True
        
        logging.info(f"✅ Copiado: ID {source_message.message_id}")
        return True
    except Exception as e:
        logging.error(f"❌ Falha ao copiar {source_message.message_id}: {e}")
        return False

async def send_random_media(bot):
    """Envia uma mídia aleatória para o canal de destino."""
    global media_messages, sent_messages
    
    if not media_messages:
        logging.warning("⚠️ Nenhuma mídia disponível")
        return False
    
    # Filtra mídias não enviadas
    available_messages = [msg for msg in media_messages if msg.message_id not in sent_messages]
    
    # Se todas foram enviadas, reinicia
    if not available_messages:
        logging.info("🔄 Todas as mídias foram enviadas. Reiniciando ciclo...")
        sent_messages.clear()
        available_messages = media_messages
    
    # Seleciona mídia aleatória
    selected_message = random.choice(available_messages)
    logging.info(f"🎲 Selecionada mídia ID {selected_message.message_id}")
    
    # Tenta encaminhar
    success = await forward_media_message(bot, selected_message, DESTINATION_CHANNEL_ID)
    
    # Se falhar, tenta copiar
    if not success:
        logging.info("🔄 Tentando copiar mídia...")
        success = await copy_media_message(bot, selected_message, DESTINATION_CHANNEL_ID)
    
    if success:
        sent_messages.add(selected_message.message_id)
        logging.info(f"📊 Total de mídias enviadas: {len(sent_messages)}/{len(media_messages)}")
        return True
    else:
        logging.error("❌ Falha ao enviar mídia")
        return False

async def main_loop():
    """Loop principal do bot."""
    global media_messages
    
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Carrega mídias do canal de origem
    logging.info("🔄 Carregando mídias do canal de origem...")
    media_messages = await get_media_messages(bot, SOURCE_CHANNEL_ID)
    
    if not media_messages:
        logging.error("❌ Nenhuma mídia encontrada no canal de origem")
        logging.error("💡 Verifique se:")
        logging.error("   - O bot é ADMIN no canal de origem")
        logging.error("   - Existem mídias no canal")
        logging.error("   - O ID do canal está correto")
        return
    
    logging.info("🤖 BOT INICIADO COM SUCESSO!")
    logging.info(f"📥 Canal de origem: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Canal de destino: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
    logging.info(f"📊 Total de mídias: {len(media_messages)}")
    
    sent_count = 0
    
    while True:
        try:
            # Envia uma mídia
            success = await send_random_media(bot)
            
            if success:
                sent_count += 1
            
            # Calcula próximo horário
            next_time = datetime.now(TIMEZONE) + asyncio.timeout(INTERVAL_HOURS * 3600)
            logging.info(f"⏰ Próximo envio: {next_time.strftime('%d/%m/%Y %H:%M:%S')}")
            logging.info(f"⏳ Aguardando {INTERVAL_HOURS} horas...")
            
            # Aguarda o intervalo
            await asyncio.sleep(INTERVAL_HOURS * 3600)
            
        except Exception as e:
            logging.error(f"💥 Erro no loop principal: {e}")
            logging.info("🔄 Tentando novamente em 5 minutos...")
            await asyncio.sleep(300)

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido manualmente")
