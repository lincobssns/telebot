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
media_messages = []  # Armazena TODAS as mídias do canal
sent_messages = set()  # IDs das mensagens já enviadas

# =================== FUNÇÕES ===================

async def get_all_media_messages(bot):
    """Busca TODAS as mensagens com mídia do canal."""
    try:
        logging.info("🔍 Buscando TODAS as mídias do canal...")
        
        all_messages = []
        offset_id = None
        batch_count = 0
        
        while True:
            try:
                # Busca um lote de mensagens
                messages = await bot.get_chat_history(
                    chat_id=SOURCE_CHANNEL_ID,
                    limit=100,  # 100 mensagens por vez
                    offset_id=offset_id
                )
                
                if not messages:
                    break
                
                # Filtra apenas mensagens com mídia
                for message in messages:
                    if (message.photo or message.video or message.audio or 
                        message.document or message.animation or message.sticker or
                        message.voice):
                        all_messages.append(message)
                
                batch_count += 1
                logging.info(f"📦 Lote {batch_count}: +{len(messages)} mensagens ({len(all_messages)} mídias totais)")
                
                # Atualiza o offset para a próxima página
                offset_id = messages[-1].message_id
                
                # Para após 10 lotes (1000 mensagens) ou quando não há mais mensagens
                if batch_count >= 10 or len(messages) < 100:
                    break
                    
            except Exception as e:
                logging.error(f"❌ Erro no lote {batch_count}: {e}")
                break
        
        logging.info(f"✅ Total de mídias encontradas: {len(all_messages)}")
        return all_messages
        
    except Exception as e:
        logging.error(f"💥 Erro ao buscar mídias: {e}")
        return []

async def get_media_messages_simple(bot):
    """Busca mídias de forma mais simples (fallback)."""
    try:
        logging.info("🔍 Buscando mídias recentes...")
        messages = []
        
        # Busca as últimas 500 mensagens
        recent_messages = await bot.get_chat_history(
            chat_id=SOURCE_CHANNEL_ID,
            limit=500
        )
        
        # Filtra apenas mensagens com mídia
        for message in recent_messages:
            if (message.photo or message.video or message.audio or 
                message.document or message.animation or message.sticker or
                message.voice):
                messages.append(message)
        
        logging.info(f"✅ Encontradas {len(messages)} mídias recentes")
        return messages
        
    except Exception as e:
        logging.error(f"❌ Erro simples: {e}")
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
    global media_messages
    
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Testa acesso aos canais
    if not await test_bot_access(bot):
        return
    
    # Busca TODAS as mídias do canal
    logging.info("🔄 Carregando mídias do canal...")
    media_messages = await get_all_media_messages(bot)
    
    # Se não conseguiu, tenta método simples
    if not media_messages:
        logging.info("🔄 Tentando método simples...")
        media_messages = await get_media_messages_simple(bot)
    
    if not media_messages:
        logging.error("❌ Não foi possível carregar mídias do canal")
        logging.error("💡 Verifique se:")
        logging.error("   - O bot é ADMIN no canal de origem")
        logging.error("   - O bot tem permissão para ver mensagens")
        logging.error("   - Existem mídias no canal")
        return
    
    logging.info("🤖 BOT INICIADO COM SUCESSO!")
    logging.info(f"📥 Canal de origem: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Canal de destino: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
    logging.info(f"📊 Total de mídias: {len(media_messages)}")
    logging.info("🎯 Modo: Mídia nova (sem forward/legenda)")
    
    sent_count = 0
    
    while True:
        try:
            # Filtra mídias não enviadas
            available_messages = [msg for msg in media_messages if msg.message_id not in sent_messages]
            
            # Se todas foram enviadas, reinicia
            if not available_messages:
                logging.info("🔄 Todas as mídias foram enviadas. Reiniciando ciclo...")
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
                logging.info(f"📈 Total enviadas: {sent_count}/{len(media_messages)}")
            else:
                logging.error("❌ Falha ao enviar mídia")
            
            # Aguarda intervalo
            logging.info(f"⏳ Próxima mídia em {INTERVAL_HOURS} horas...")
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
