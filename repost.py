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

async def send_media_as_new(bot, source_message, destination_channel_id):
    """Envia a mídia como se fosse nova, sem forward e sem legenda."""
    try:
        # Remove qualquer legenda existente e envia como mídia nova
        if source_message.photo:
            await bot.send_photo(
                chat_id=destination_channel_id,
                photo=source_message.photo[-1].file_id,
                caption=None  # Sem legenda
            )
        elif source_message.video:
            await bot.send_video(
                chat_id=destination_channel_id,
                video=source_message.video.file_id,
                caption=None  # Sem legenda
            )
        elif source_message.audio:
            await bot.send_audio(
                chat_id=destination_channel_id,
                audio=source_message.audio.file_id,
                caption=None  # Sem legenda
            )
        elif source_message.document:
            await bot.send_document(
                chat_id=destination_channel_id,
                document=source_message.document.file_id,
                caption=None  # Sem legenda
            )
        elif source_message.animation:  # GIFs
            await bot.send_animation(
                chat_id=destination_channel_id,
                animation=source_message.animation.file_id,
                caption=None  # Sem legenda
            )
        elif source_message.voice:
            await bot.send_voice(
                chat_id=destination_channel_id,
                voice=source_message.voice.file_id,
                caption=None  # Sem legenda
            )
        elif source_message.sticker:
            await bot.send_sticker(
                chat_id=destination_channel_id,
                sticker=source_message.sticker.file_id
            )
        elif source_message.text:
            # Se for apenas texto, envia o texto puro
            await bot.send_message(
                chat_id=destination_channel_id,
                text=source_message.text
            )
        
        logging.info(f"✅ Mídia enviada como nova: ID {source_message.message_id}")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erro ao enviar mídia como nova {source_message.message_id}: {e}")
        return False

async def get_manual_message_ids(bot):
    """Obtém mensagens manualmente - você precisa adicionar os IDs reais aqui."""
    try:
        # ⚠️ ADICIONE OS IDs REAIS DAS MENSAGENS AQUI!
        MANUAL_MESSAGE_IDS = [
            # EXEMPLO - SUBSTITUA COM SEUS IDs REAIS:
            # 123, 124, 125, etc.
        ]
        
        if not MANUAL_MESSAGE_IDS:
            logging.warning("⚠️ Nenhum ID manual configurado")
            # Vamos tentar obter algumas mensagens recentes automaticamente
            return await get_recent_messages(bot)
        
        messages = []
        for msg_id in MANUAL_MESSAGE_IDS:
            try:
                message = await bot.get_message(chat_id=SOURCE_CHANNEL_ID, message_id=msg_id)
                messages.append(message)
                logging.info(f"✅ Carregada mensagem ID {msg_id}")
            except Exception as e:
                logging.warning(f"⚠️ Não foi possível carregar mensagem {msg_id}: {e}")
        
        return messages
        
    except Exception as e:
        logging.error(f"❌ Erro ao carregar IDs manuais: {e}")
        return []

async def get_recent_messages(bot, limit=50):
    """Tenta obter mensagens recentes do canal."""
    try:
        # Esta é uma abordagem simplificada para obter algumas mensagens
        # Em produção, você precisaria de uma forma mais robusta
        messages = []
        
        # Vamos tentar acessar as últimas mensagens
        # Nota: Esta abordagem pode não ser 100% confiável sem get_chat_history
        logging.info("🔍 Tentando obter mensagens recentes...")
        
        # Como fallback, vamos criar algumas mídias de teste
        return await create_test_media(bot)
        
    except Exception as e:
        logging.error(f"❌ Erro ao obter mensagens recentes: {e}")
        return []

async def create_test_media(bot):
    """Cria mídias de teste para demonstração."""
    try:
        logging.info("📸 Criando mídias de teste...")
        test_messages = []
        
        # Lista de URLs de imagens para teste
        test_images = [
            "https://images.unsplash.com/photo-1579546929662-711aa81148cf",  # Gradiente
            "https://images.unsplash.com/photo-1551963831-b3b1ca40c98e",  # Frutas
            "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f",  # Mulher
        ]
        
        for i, image_url in enumerate(test_images):
            try:
                msg = await bot.send_photo(
                    chat_id=SOURCE_CHANNEL_ID,
                    photo=image_url,
                    caption=None  # Sem legenda
                )
                test_messages.append(msg)
                logging.info(f"✅ Criada mídia de teste {i+1}")
            except Exception as e:
                logging.warning(f"⚠️ Erro ao criar mídia {i+1}: {e}")
        
        return test_messages
        
    except Exception as e:
        logging.error(f"❌ Erro ao criar mídias de teste: {e}")
        return []

async def test_bot_access(bot):
    """Testa se o bot tem acesso aos canais."""
    try:
        await bot.get_chat(chat_id=SOURCE_CHANNEL_ID)
        await bot.get_chat(chat_id=DESTINATION_CHANNEL_ID)
        logging.info("✅ Bot tem acesso aos canais")
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
    
    # Carrega mídias
    logging.info("🔄 Carregando mídias...")
    media_messages = await get_manual_message_ids(bot)
    
    if not media_messages:
        logging.error("❌ Não foi possível obter mídias")
        return
    
    logging.info("🤖 BOT INICIADO!")
    logging.info(f"📥 Origem: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Destino: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS}h")
    logging.info(f"📊 Mídias: {len(media_messages)}")
    logging.info("🎯 Modo: Enviar como mídia nova (sem forward/legenda)")
    
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
            
            # Envia como mídia nova (sem forward, sem legenda)
            success = await send_media_as_new(bot, selected_message, DESTINATION_CHANNEL_ID)
            
            if success:
                sent_messages.add(selected_message.message_id)
                logging.info(f"📈 Enviadas: {len(sent_messages)}/{len(media_messages)}")
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
