import asyncio
import os
import json
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

# =================== ARMAZENAMENTO ===================
MEDIA_IDS_FILE = "media_ids.json"
SENT_IDS_FILE = "sent_ids.json"

def load_json_file(filename):
    """Carrega dados de arquivo JSON."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"❌ Erro ao carregar {filename}: {e}")
    return []

def save_json_file(filename, data):
    """Salva dados em arquivo JSON."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logging.error(f"❌ Erro ao salvar {filename}: {e}")

# =================== FUNÇÕES PRINCIPAIS ===================

async def discover_media_messages(bot):
    """Descobre automaticamente mensagens com mídia no canal."""
    logging.info("🔍 Iniciando busca automática por mídias...")
    
    media_ids = []
    found_count = 0
    
    # Estratégia: testar um grande range de IDs
    ranges_to_test = [
        (1, 300),      # Primeiras mensagens
        (301, 600),    # Mensagens do meio
        (601, 900),    # Últimas mensagens
    ]
    
    for start, end in ranges_to_test:
        logging.info(f"📡 Verificando IDs {start} a {end}...")
        
        for msg_id in range(start, end + 1):
            try:
                message = await bot.get_message(SOURCE_CHANNEL_ID, msg_id)
                
                if (message.photo or message.video or message.audio or 
                    message.document or message.animation or message.sticker or
                    message.voice):
                    media_ids.append(msg_id)
                    found_count += 1
                    logging.info(f"✅ Mídia {found_count}: ID {msg_id}")
                
            except Exception:
                # Mensagem não existe ou não pode ser acessada
                continue
            
            # Pequena pausa para não sobrecarregar a API
            await asyncio.sleep(0.1)
    
    # Remove duplicatas e ordena
    media_ids = sorted(list(set(media_ids)))
    
    # Salva os IDs encontrados
    save_json_file(MEDIA_IDS_FILE, media_ids)
    
    logging.info(f"🎯 BUSCA CONCLUÍDA: {len(media_ids)} mídias encontradas!")
    return media_ids

async def send_media_message(bot, msg_id):
    """Envia uma mensagem de mídia."""
    try:
        await bot.forward_message(
            chat_id=DESTINATION_CHANNEL_ID,
            from_chat_id=SOURCE_CHANNEL_ID,
            message_id=msg_id
        )
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao enviar {msg_id}: {e}")
        return False

async def main_loop():
    """Loop principal do bot."""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN não configurado")
        return
    
    bot = Bot(token=BOT_TOKEN)
    
    # Verifica acesso aos canais
    try:
        source_chat = await bot.get_chat(SOURCE_CHANNEL_ID)
        dest_chat = await bot.get_chat(DESTINATION_CHANNEL_ID)
        logging.info(f"✅ Acesso confirmado: {source_chat.title} → {dest_chat.title}")
    except Exception as e:
        logging.error(f"❌ Erro de acesso: {e}")
        return
    
    # Carrega ou descobre mídias
    media_ids = load_json_file(MEDIA_IDS_FILE)
    
    if not media_ids:
        logging.info("🔄 Nenhuma mídia salva. Iniciando busca automática...")
        media_ids = await discover_media_messages(bot)
    
    if not media_ids:
        logging.error("❌ Nenhuma mídia encontrada no canal")
        return
    
    # Carrega IDs já enviados
    sent_ids = set(load_json_file(SENT_IDS_FILE))
    
    logging.info("🤖 BOT INICIADO NO RAILWAY!")
    logging.info(f"📊 Mídias disponíveis: {len(media_ids)}")
    logging.info(f"📤 Já enviadas: {len(sent_ids)}")
    logging.info(f"⏱️ Intervalo: {INTERVAL_HOURS} horas")
    logging.info("🔄 Executando 24/7...")
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            logging.info(f"🔄 Ciclo #{cycle_count}")
            
            # Filtra mídias não enviadas
            available_ids = [msg_id for msg_id in media_ids if msg_id not in sent_ids]
            
            if not available_ids:
                logging.info("🎉 TODAS as mídias foram enviadas! Reiniciando ciclo...")
                sent_ids.clear()
                save_json_file(SENT_IDS_FILE, [])
                available_ids = media_ids
            
            # Seleção aleatória
            selected_id = random.choice(available_ids)
            logging.info(f"🎲 Selecionada mídia ID {selected_id}")
            
            # Envio
            success = await send_media_message(bot, selected_id)
            
            if success:
                sent_ids.add(selected_id)
                save_json_file(SENT_IDS_FILE, list(sent_ids))
                logging.info(f"📈 Progresso: {len(sent_ids)}/{len(media_ids)}")
                
                # Log de estatísticas
                progress = (len(sent_ids) / len(media_ids)) * 100
                logging.info(f"📊 Conclusão: {progress:.1f}%")
            
            # Próximo horário
            next_time = datetime.now(TIMEZONE) + asyncio.timeout(INTERVAL_HOURS * 3600)
            logging.info(f"⏰ Próximo envio: {next_time.strftime('%d/%m %H:%M')}")
            logging.info(f"💤 Aguardando {INTERVAL_HOURS} horas...")
            
            await asyncio.sleep(INTERVAL_HOURS * 3600)
            
        except Exception as e:
            logging.error(f"💥 Erro no ciclo {cycle_count}: {e}")
            logging.info("🔄 Tentando novamente em 10 minutos...")
            await asyncio.sleep(600)

# =================== EXECUÇÃO ===================

if __name__ == "__main__":
    logging.info("🚀 Iniciando Bot no Railway...")
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("🛑 Bot interrompido manualmente")
    except Exception as e:
        logging.error(f"💥 Erro fatal: {e}")
        logging.info("🔄 Reiniciando em 30 segundos...")
        asyncio.sleep(30)
        asyncio.run(main_loop())
