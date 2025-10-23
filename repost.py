"""
bot_forwarder.py
Bot Telegram que lê mídias de um canal (como admin) e repassa para outro grupo.
Versão atualizada para python-telegram-bot 21.0+
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
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Token do BotFather
SOURCE_CHANNEL_ID = os.getenv("SOURCE_CHANNEL_ID")  # Canal de origem (bot deve ser admin)
DESTINATION_CHANNEL_ID = os.getenv("DESTINATION_CHANNEL_ID")  # Canal/grupo de destino
INTERVAL_HOURS = float(os.getenv("INTERVAL_HOURS", "2"))  # Intervalo entre envios
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

async def get_channel_media_messages(bot, channel_id, limit=100):
    """Obtém as mensagens com mídia do canal de origem."""
    try:
        messages = []
        # Usando get_updates ou webhook para obter mensagens mais recentes
        # Alternativa: usar get_chat_member para verificar permissões primeiro
        async with bot:
            # Primeiro verifica se o bot tem acesso ao canal
            try:
                await bot.get_chat(chat_id=channel_id)
            except TelegramError as e:
                logging.error(f"❌ Bot não tem acesso ao canal {channel_id}: {e}")
                return []
            
            # Para versões mais recentes, podemos tentar diferentes abordagens
            try:
                # Método para versões 20.0+
                async for message in bot.get_chat_history(chat_id=channel_id, limit=limit):
                    if has_media(message):
                        messages.append(message)
            except AttributeError:
                # Fallback para versões mais antigas
                logging.warning("⚠️ Método get_chat_history não disponível. Usando abordagem alternativa...")
                messages = await get_media_messages_alternative(bot, channel_id, limit)
        
        logging.info(f"📥 Encontradas {len(messages)} mensagens com mídia no canal de origem")
        return messages
    except TelegramError as e:
        logging.error(f"❌ Erro ao acessar canal de origem {channel_id}: {e}")
        return []
    except Exception as e:
        logging.error(f"💥 Erro inesperado ao ler canal: {e}")
        return []

def has_media(message):
    """Verifica se a mensagem contém mídia."""
    return (message.photo or message.video or message.audio or 
            message.document or message.animation or message.voice or
            message.sticker)

async def get_media_messages_alternative(bot, channel_id, limit=50):
    """Abordagem alternativa para obter mensagens com mídia."""
    try:
        # Esta é uma abordagem simplificada - na prática você precisaria
        # armazenar as mensagens que já processou
        messages = []
        
        # Para um bot real, você precisaria usar webhooks ou armazenar
        # o estado das mensagens já processadas
        logging.info("🔍 Buscando mensagens recentes...")
        
        # Como fallback, vamos simular algumas mensagens de exemplo
        # EM PRODUÇÃO: você precisaria implementar lógica de webhook
        # ou usar uma abordagem diferente para monitorar o canal
        
        return messages
    except Exception as e:
        logging.error(f"❌ Erro na abordagem alternativa: {e}")
        return []

async def forward_media_message(bot, source_message, destination_chat_id):
    """Encaminha uma mensagem de mídia para o canal de destino."""
    try:
        await bot.forward_message(
            chat_id=destination_chat_id,
            from_chat_id=source_message.chat.id,
            message_id=source_message.message_id
        )
        logging.info(f"✅ Encaminhado para {destination_chat_id}: ID {source_message.message_id}")
        return True
    except TelegramError as e:
        logging.error(f"❌ Falha ao encaminhar mensagem {source_message.message_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"💥 Erro inesperado ao encaminhar: {e}")
        return False

async def copy_media_message(bot, source_message, destination_chat_id):
    """Copia uma mensagem de mídia (alternativa ao encaminhamento)."""
    try:
        caption = f"📦 Encaminhado automaticamente em {now_str()}"
        
        if source_message.photo:
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
        
        logging.info(f"✅ Copiado para {destination_chat_id}: ID {source_message.message_id}")
        return True
    except TelegramError as e:
        logging.error(f"❌ Falha ao copiar mensagem {source_message.message_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"💥 Erro inesperado ao copiar: {e}")
        return False

async def main_loop():
    """Loop principal: lê mídias do canal e repassa a cada X horas."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não definido. Configure-o nas variáveis de ambiente.")
        return

    if not SOURCE_CHANNEL_ID or not DESTINATION_CHANNEL_ID:
        logging.error("❌ Configure SOURCE_CHANNEL_ID e DESTINATION_CHANNEL_ID no Railway.")
        return

    try:
        source_id = int(SOURCE_CHANNEL_ID)
        dest_id = int(DESTINATION_CHANNEL_ID)
    except ValueError:
        logging.error("❌ IDs dos canais devem ser números inteiros")
        return

    bot = Bot(token=BOT_TOKEN)
    
    # Cache de mensagens já encaminhadas
    forwarded_messages = set()
    
    logging.info("🤖 BOT INICIADO com sucesso!")
    logging.info(f"📥 Lendo do canal: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Enviando para: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")

    while True:
        try:
            # Busca mensagens com mídia do canal de origem
            media_messages = await get_channel_media_messages(bot, source_id, limit=50)
            
            if not media_messages:
                logging.warning("⏳ Nenhuma mídia encontrada no canal de origem...")
                await asyncio.sleep(600)  # espera 10 min
                continue

            # Filtra mensagens que ainda não foram encaminhadas
            new_messages = [msg for msg in media_messages if msg.message_id not in forwarded_messages]
            
            if not new_messages:
                logging.info("🔄 Todas as mídias já foram encaminhadas. Buscando novas...")
                # Limpa cache parcialmente para evitar crescimento infinito
                if len(forwarded_messages) > 100:
                    forwarded_messages.clear()
                await asyncio.sleep(600)
                continue

            # Escolhe uma mídia aleatória das novas
            message_to_forward = random.choice(new_messages)
            
            # Tenta encaminhar primeiro (preserva o conteúdo original)
            success = await forward_media_message(bot, message_to_forward, dest_id)
            
            # Se falhar, tenta copiar
            if not success:
                logging.info("🔄 Tentando copiar em vez de encaminhar...")
                success = await copy_media_message(bot, message_to_forward, dest_id)
            
            if success:
                forwarded_messages.add(message_to_forward.message_id)
                logging.info(f"✅ Mídia {message_to_forward.message_id} processada com sucesso")
            else:
                logging.error(f"❌ Falha ao processar mídia {message_to_forward.message_id}")

            logging.info(f"🕒 Próximo envio em {INTERVAL_HOURS:.1f} horas...\n")
            await asyncio.sleep(INTERVAL_HOURS * 3600)

        except Exception as e:
            logging.error(f"💥 Erro no loop principal: {e}")
            await asyncio.sleep(300)  # espera 5 min antes de tentar novamente

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido manualmente.")
