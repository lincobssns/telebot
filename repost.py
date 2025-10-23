import asyncio
import os
import random
import logging
from telegram import Bot
from telegram.error import TelegramError
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

# =================== FUNÇÕES ===================

def now_str():
    return datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

async def test_bot_access(bot):
    """Testa se o bot tem acesso aos canais."""
    try:
        # Testa acesso ao canal de origem
        chat = await bot.get_chat(chat_id=SOURCE_CHANNEL_ID)
        logging.info(f"✅ Acesso ao canal de origem: {chat.title}")
        
        # Testa acesso ao canal de destino
        chat_dest = await bot.get_chat(chat_id=DESTINATION_CHANNEL_ID)
        logging.info(f"✅ Acesso ao canal de destino: {chat_dest.title}")
        
        return True
    except TelegramError as e:
        logging.error(f"❌ Erro de acesso: {e}")
        return False

async def get_manual_message_ids(bot):
    """Obtém mensagens manualmente - você precisa adicionar os IDs reais aqui."""
    try:
        # ⚠️ IMPORTANTE: Adicione os IDs reais das mensagens do seu canal
        # Como obter os IDs:
        # 1. Encaminhe a mensagem para @userinfobot
        # 2. Ou adicione @RawDataBot ao canal
        # 3. Ou use qualquer bot que mostre o ID da mensagem
        
        MANUAL_MESSAGE_IDS = [
            # EXEMPLO - SUBSTITUA COM SEUS IDs REAIS:
            # 123, 124, 125, etc.
            # Adicione pelo menos 5-10 IDs para testar
        ]
        
        if not MANUAL_MESSAGE_IDS:
            logging.warning("⚠️ Nenhum ID manual configurado")
            return []
        
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

async def create_test_media(bot):
    """Cria mídias de teste para demonstração."""
    try:
        logging.info("🔄 Criando mídias de teste...")
        test_messages = []
        
        # Envia algumas fotos de exemplo
        photo_urls = [
            "https://images.unsplash.com/photo-1579546929662-711aa81148cf",
            "https://images.unsplash.com/photo-1551963831-b3b1ca40c98e",
            "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f"
        ]
        
        for i, url in enumerate(photo_urls):
            try:
                msg = await bot.send_photo(
                    chat_id=SOURCE_CHANNEL_ID,
                    photo=url,
                    caption=f"📸 Foto de teste {i+1} - {now_str()}"
                )
                test_messages.append(msg)
                logging.info(f"✅ Criada mídia de teste {i+1}")
            except Exception as e:
                logging.warning(f"⚠️ Erro ao criar mídia {i+1}: {e}")
        
        return test_messages
        
    except Exception as e:
        logging.error(f"❌ Erro ao criar mídias de teste: {e}")
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

async def send_random_media(bot, media_messages):
    """Envia uma mídia aleatória para o canal de destino."""
    global sent_messages
    
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
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Testa acesso aos canais
    if not await test_bot_access(bot):
        return
    
    # Carrega mídias (primeiro tenta manual, depois cria teste)
    logging.info("🔄 Carregando mídias...")
    media_messages = await get_manual_message_ids(bot)
    
    if not media_messages:
        logging.info("🔄 Criando mídias de teste...")
        media_messages = await create_test_media(bot)
    
    if not media_messages:
        logging.error("❌ Não foi possível obter mídias")
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
            success = await send_random_media(bot, media_messages)
            
            if success:
                sent_count += 1
            
            # Aguarda o intervalo
            logging.info(f"⏳ Aguardando {INTERVAL_HOURS} horas...")
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
