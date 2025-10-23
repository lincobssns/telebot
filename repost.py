"""
bot_forwarder_webhook.py
Bot Telegram que monitora um canal via webhook e repassa mídias automaticamente.
"""

import os
import logging
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from datetime import datetime
import pytz
import json

# =================== CONFIGURAÇÕES ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = int(os.getenv("SOURCE_CHANNEL_ID", "-1003106957508"))
DESTINATION_CHANNEL_ID = int(os.getenv("DESTINATION_CHANNEL_ID", "-1003135697010"))
INTERVAL_HOURS = float(os.getenv("INTERVAL_HOURS", "2"))
TIMEZONE = pytz.timezone(os.getenv("TZ", "America/Sao_Paulo"))
PORT = int(os.getenv("PORT", "8080"))

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# =================== ARMAZENAMENTO ===================
# Arquivo para armazenar mensagens processadas
PROCESSED_MESSAGES_FILE = "processed_messages.json"

def load_processed_messages():
    """Carrega as mensagens já processadas do arquivo."""
    try:
        if os.path.exists(PROCESSED_MESSAGES_FILE):
            with open(PROCESSED_MESSAGES_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logging.error(f"❌ Erro ao carregar mensagens processadas: {e}")
    return set()

def save_processed_messages(messages):
    """Salva as mensagens processadas no arquivo."""
    try:
        with open(PROCESSED_MESSAGES_FILE, 'w') as f:
            json.dump(list(messages), f)
    except Exception as e:
        logging.error(f"❌ Erro ao salvar mensagens processadas: {e}")

# Conjunto de mensagens já processadas
processed_messages = load_processed_messages()

# =================== FUNÇÕES ===================

def now_str():
    return datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

def has_media(message):
    """Verifica se a mensagem contém mídia."""
    return (message.photo or message.video or message.audio or 
            message.document or message.animation or message.voice or
            message.sticker)

async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa mensagens recebidas no canal de origem."""
    try:
        message = update.effective_message
        
        # Verifica se a mensagem é do canal de origem
        if message.chat.id != SOURCE_CHANNEL_ID:
            return
        
        # Verifica se já processou esta mensagem
        if message.message_id in processed_messages:
            return
        
        # Verifica se tem mídia
        if has_media(message):
            logging.info(f"📥 Nova mídia detectada: ID {message.message_id}")
            
            # Adiciona à fila para processamento posterior
            if 'media_queue' not in context.bot_data:
                context.bot_data['media_queue'] = []
            
            context.bot_data['media_queue'].append(message)
            processed_messages.add(message.message_id)
            save_processed_messages(processed_messages)
            
            logging.info(f"✅ Mídia {message.message_id} adicionada à fila. Fila: {len(context.bot_data['media_queue'])}")
            
    except Exception as e:
        logging.error(f"💥 Erro ao processar mensagem: {e}")

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
    except Exception as e:
        logging.error(f"❌ Falha ao encaminhar mensagem {source_message.message_id}: {e}")
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
        elif source_message.animation:
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
    except Exception as e:
        logging.error(f"❌ Falha ao copiar mensagem {source_message.message_id}: {e}")
        return False

async def scheduled_forwarder(context: ContextTypes.DEFAULT_TYPE):
    """Tarefa agendada que envia mídias da fila a cada X horas."""
    try:
        bot = context.bot
        
        if 'media_queue' not in context.bot_data or not context.bot_data['media_queue']:
            logging.info("⏳ Nenhuma mídia na fila para enviar...")
            return
        
        # Pega a mídia mais antiga da fila
        message_to_send = context.bot_data['media_queue'].pop(0)
        
        logging.info(f"🔄 Processando mídia da fila: ID {message_to_send.message_id}")
        
        # Tenta encaminhar
        success = await forward_media_message(bot, message_to_send, DESTINATION_CHANNEL_ID)
        
        # Se falhar, tenta copiar
        if not success:
            logging.info("🔄 Tentando copiar em vez de encaminhar...")
            success = await copy_media_message(bot, message_to_send, DESTINATION_CHANNEL_ID)
        
        if success:
            logging.info(f"✅ Mídia {message_to_send.message_id} enviada com sucesso")
        else:
            # Se falhou, recoloca na fila
            context.bot_data['media_queue'].insert(0, message_to_send)
            logging.error(f"❌ Falha ao processar mídia {message_to_send.message_id}")
        
        logging.info(f"📊 Fila restante: {len(context.bot_data['media_queue'])} mídias")
        
    except Exception as e:
        logging.error(f"💥 Erro no agendador: {e}")

async def initialize_bot():
    """Inicializa o bot e configura o webhook."""
    try:
        # Cria a application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Adiciona handler para mensagens do canal
        application.add_handler(
            MessageHandler(
                filters.Chat(chat_id=SOURCE_CHANNEL_ID) & 
                (filters.PHOTO | filters.VIDEO | filters.AUDIO | 
                 filters.DOCUMENT | filters.ANIMATION | filters.VOICE | 
                 filters.STICKER),
                handle_channel_message
            )
        )
        
        # Agenda o envio periódico
        job_queue = application.job_queue
        job_queue.run_repeating(
            scheduled_forwarder,
            interval=INTERVAL_HOURS * 3600,
            first=10  # Primeira execução em 10 segundos
        )
        
        # Configura webhook (para Railway)
        webhook_url = os.getenv("RAILWAY_STATIC_URL")
        if webhook_url:
            await application.bot.set_webhook(f"{webhook_url}/webhook")
            logging.info(f"🌐 Webhook configurado: {webhook_url}")
        else:
            # Se não tem webhook URL, usa polling (para desenvolvimento)
            logging.info("🔍 Usando polling...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
        
        logging.info("🤖 BOT INICIADO com sucesso!")
        logging.info(f"📥 Monitorando canal: {SOURCE_CHANNEL_ID}")
        logging.info(f"📤 Enviando para: {DESTINATION_CHANNEL_ID}")
        logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
        logging.info(f"📊 Mensagens processadas: {len(processed_messages)}")
        
        return application
        
    except Exception as e:
        logging.error(f"💥 Erro ao inicializar bot: {e}")
        return None

async def main():
    """Função principal."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não definido")
        return
    
    application = await initialize_bot()
    
    if application:
        try:
            # Mantém o bot rodando
            await asyncio.Future()  # roda forever
        except KeyboardInterrupt:
            logging.info("🛑 Bot interrompido manualmente")
        finally:
            if application.running:
                await application.stop()
                await application.shutdown()

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    asyncio.run(main())
