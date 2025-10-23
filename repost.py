import asyncio
import os
import logging
import json
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# =================== CONFIGURAÇÕES ===================
BOT_TOKEN = os.getenv("BOT_TOKEN")
SOURCE_CHANNEL_ID = -1003106957508
DESTINATION_CHANNEL_ID = -1003135697010
INTERVAL_HOURS = 2

# =================== LOGGING ===================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

# =================== ARMAZENAMENTO ===================
MEDIA_QUEUE_FILE = "media_queue.json"

def load_media_queue():
    """Carrega a fila de mídias do arquivo."""
    try:
        if os.path.exists(MEDIA_QUEUE_FILE):
            with open(MEDIA_QUEUE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"❌ Erro ao carregar fila: {e}")
    return []

def save_media_queue(queue):
    """Salva a fila de mídias no arquivo."""
    try:
        with open(MEDIA_QUEUE_FILE, 'w') as f:
            json.dump(queue, f)
    except Exception as e:
        logging.error(f"❌ Erro ao salvar fila: {e}")

# =================== FUNÇÕES ===================

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura novas mensagens do canal de origem."""
    try:
        message = update.effective_message
        
        # Verifica se é do canal de origem
        if message.chat.id != SOURCE_CHANNEL_ID:
            return
        
        # Verifica se tem mídia
        has_media = (message.photo or message.video or message.audio or 
                    message.document or message.animation or message.sticker or
                    message.voice)
        
        if has_media:
            # Adiciona à fila
            queue = load_media_queue()
            queue.append({
                'message_id': message.message_id,
                'chat_id': message.chat.id,
                'timestamp': message.date.isoformat() if message.date else None
            })
            save_media_queue(queue)
            
            logging.info(f"📥 Nova mídia adicionada à fila: ID {message.message_id}")
            logging.info(f"📊 Fila atual: {len(queue)} mídias")
            
    except Exception as e:
        logging.error(f"💥 Erro ao processar mensagem: {e}")

async def send_from_queue(context: ContextTypes.DEFAULT_TYPE):
    """Envia uma mídia da fila a cada 2 horas."""
    try:
        bot = context.bot
        queue = load_media_queue()
        
        if not queue:
            logging.info("⏳ Nenhuma mídia na fila...")
            return
        
        # Pega a mídia mais antiga
        media_info = queue.pop(0)
        message_id = media_info['message_id']
        
        logging.info(f"📤 Enviando mídia da fila: ID {message_id}")
        
        # Tenta encaminhar
        try:
            await bot.forward_message(
                chat_id=DESTINATION_CHANNEL_ID,
                from_chat_id=SOURCE_CHANNEL_ID,
                message_id=message_id
            )
            logging.info(f"✅ Mídia {message_id} encaminhada com sucesso")
            
        except Exception as e:
            logging.error(f"❌ Erro ao encaminhar {message_id}: {e}")
            # Se falhar, recoloca na fila
            queue.insert(0, media_info)
        
        # Salva a fila atualizada
        save_media_queue(queue)
        logging.info(f"📊 Fila restante: {len(queue)} mídias")
        
    except Exception as e:
        logging.error(f"💥 Erro no agendador: {e}")

async def initialize_existing_media(bot):
    """Tenta carregar mídias existentes do canal (apenas para novas instalações)."""
    try:
        queue = load_media_queue()
        
        # Se já tem mídias na fila, não precisa recarregar
        if queue:
            logging.info(f"📊 Fila existente carregada: {len(queue)} mídias")
            return
        
        logging.info("🔍 Tentando carregar mídias existentes...")
        
        # Esta é uma abordagem limitada - funciona apenas para mensagens recentes
        # Em produção, você precisaria de uma forma mais robusta
        
        # Vamos tentar acessar algumas mensagens recentes
        for offset in range(1, 100):  # Tenta IDs de 1 a 100
            try:
                message = await bot.get_message(
                    chat_id=SOURCE_CHANNEL_ID,
                    message_id=offset
                )
                
                if (message.photo or message.video or message.audio or 
                    message.document or message.animation or message.sticker):
                    
                    queue.append({
                        'message_id': message.message_id,
                        'chat_id': message.chat.id,
                        'timestamp': message.date.isoformat() if message.date else None
                    })
                    logging.info(f"✅ Mídia existente encontrada: ID {message.message_id}")
                    
            except Exception:
                # Mensagem não existe, continua para a próxima
                continue
        
        if queue:
            save_media_queue(queue)
            logging.info(f"📥 {len(queue)} mídias existentes adicionadas à fila")
        else:
            logging.info("📝 Aguardando novas mídias...")
            
    except Exception as e:
        logging.error(f"❌ Erro ao carregar mídias existentes: {e}")

async def main():
    """Função principal."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    # Cria a aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Configura o handler para novas mensagens
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=SOURCE_CHANNEL_ID) & 
            (filters.PHOTO | filters.VIDEO | filters.AUDIO | 
             filters.Document.ALL | filters.ANIMATION | filters.VOICE | 
             filters.STICKER),
            handle_new_message
        )
    )
    
    # Agenda o envio automático
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(
            send_from_queue,
            interval=INTERVAL_HOURS * 3600,
            first=10  # Primeira execução em 10 segundos
        )
    
    # Inicializa o bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Tenta carregar mídias existentes
    await initialize_existing_media(application.bot)
    
    logging.info("🤖 BOT INICIADO - TOTALMENTE AUTOMATIZADO!")
    logging.info(f"📥 Monitorando: {SOURCE_CHANNEL_ID}")
    logging.info(f"📤 Enviando para: {DESTINATION_CHANNEL_ID}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
    logging.info("🎯 Modo: Captura automática + encaminhamento")
    
    # Mantém o bot rodando
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
