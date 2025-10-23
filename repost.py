import asyncio
import os
import random
import logging
import json
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
from telethon import TelegramClient, errors
from asyncio import sleep
from datetime import datetime, timedelta
import pytz

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('repost_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecureDataManager:
    def __init__(self):
        self.encryption_key = self._derive_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _derive_key(self):
        """Deriva uma chave de criptografia a partir da ENCRYPTION_KEY"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY não encontrada no .env")
        
        # Usa PBKDF2 para derivar uma chave segura
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'secure_repost_bot_salt',  # Salt fixo para este aplicativo
            iterations=100000,
        )
        key = kdf.derive(encryption_key.encode())
        return b64encode(key)
    
    def encrypt(self, data):
        """Criptografa dados sensíveis"""
        if isinstance(data, str):
            data = data.encode()
        encrypted = self.fernet.encrypt(data)
        return b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data):
        """Descriptografa dados sensíveis"""
        try:
            decrypted = self.fernet.decrypt(b64decode(encrypted_data))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Erro ao descriptografar: {e}")
            return None

class SecureConfig:
    def __init__(self):
        self.data_manager = SecureDataManager()
        self.load_config()
    
    def load_config(self):
        """Carrega e valida configurações de forma segura"""
        try:
            # Telegram API
            self.api_id = int(os.getenv('API_ID'))
            self.api_hash = os.getenv('API_HASH')
            self.phone_number = os.getenv('PHONE_NUMBER')
            self.two_fa_password = os.getenv('TWO_FA_PASSWORD')
            
            # Bot Settings
            self.session_name = os.getenv('SESSION_NAME', 'telegram_session')
            self.min_interval = int(os.getenv('MIN_INTERVAL', 1800))
            self.max_interval = int(os.getenv('MAX_INTERVAL', 7200))
            
            # Channel pairs
            pairs_str = os.getenv('CHANNEL_PAIRS', '')
            self.donor_recipient_pairs = self._parse_channel_pairs(pairs_str)
            
            # Timezone
            self.timezone = pytz.timezone('America/Sao_Paulo')
            
            self._validate_config()
            logger.info("✅ Configurações carregadas com sucesso")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
            raise
    
    def _parse_channel_pairs(self, pairs_str):
        """Analisa os pares de canais do formato string"""
        pairs = {}
        if pairs_str:
            for pair in pairs_str.split(','):
                if ':' in pair:
                    donor, recipient = pair.split(':')
                    pairs[int(donor)] = int(recipient)
        return pairs
    
    def _validate_config(self):
        """Valida se todas as configurações necessárias estão presentes"""
        required_vars = {
            'API_ID': self.api_id,
            'API_HASH': self.api_hash,
            'PHONE_NUMBER': self.phone_number,
            'TWO_FA_PASSWORD': self.two_fa_password,
        }
        
        missing = [var for var, value in required_vars.items() if not value]
        if missing:
            raise ValueError(f"Variáveis de ambiente faltando: {', '.join(missing)}")
        
        if not self.donor_recipient_pairs:
            raise ValueError("Nenhum par de canais configurado em CHANNEL_PAIRS")

class SecureRepostBot:
    def __init__(self):
        self.config = SecureConfig()
        self.data_manager = self.config.data_manager
        self.client = TelegramClient(self.config.session_name, self.config.api_id, self.config.api_hash)
        
        # Arquivos seguros
        self.sent_messages_file = 'sent_messages.enc'
        self.cycle_state_file = 'cycle_state.enc'
        
        # Estado
        self.sent_message_hashes = self.load_sent_messages_secure()
        self.cycle_state = self.load_cycle_state_secure()
        self.donor_messages = {}
        self.available_messages = {}
        self.current_cycle = self.cycle_state.get('current_cycle', 1)

    # ===== MÉTODOS DE CRIPTOGRAFIA DE ARQUIVOS =====
    
    def load_sent_messages_secure(self):
        """Carrega mensagens enviadas de forma criptografada"""
        try:
            if os.path.exists(self.sent_messages_file):
                with open(self.sent_messages_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                    decrypted_data = self.data_manager.decrypt(encrypted_data)
                    if decrypted_data:
                        return set(decrypted_data.split('\n'))
            return set()
        except Exception as e:
            logger.error(f"Erro ao carregar mensagens enviadas criptografadas: {e}")
            return set()

    def save_sent_messages_secure(self):
        """Salva mensagens enviadas de forma criptografada"""
        try:
            data = '\n'.join(self.sent_message_hashes)
            encrypted_data = self.data_manager.encrypt(data)
            with open(self.sent_messages_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Erro ao salvar mensagens enviadas criptografadas: {e}")

    def load_cycle_state_secure(self):
        """Carrega estado do ciclo de forma criptografada"""
        try:
            if os.path.exists(self.cycle_state_file):
                with open(self.cycle_state_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read()
                    decrypted_data = self.data_manager.decrypt(encrypted_data)
                    if decrypted_data:
                        return json.loads(decrypted_data)
            return {'current_cycle': 1, 'cycles_completed': 0}
        except Exception as e:
            logger.error(f"Erro ao carregar estado do ciclo criptografado: {e}")
            return {'current_cycle': 1, 'cycles_completed': 0}

    def save_cycle_state_secure(self):
        """Salva estado do ciclo de forma criptografada"""
        try:
            data = json.dumps(self.cycle_state)
            encrypted_data = self.data_manager.encrypt(data)
            with open(self.cycle_state_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Erro ao salvar estado do ciclo criptografado: {e}")

    # ===== MÉTODOS PRINCIPAIS DO BOT =====
    
    def generate_message_hash(self, message, cycle_number=1):
        """Gera hash único para mensagem com criptografia"""
        import hashlib
        content = f"{message.id}_{message.peer_id.channel_id if message.peer_id else ''}_cycle{cycle_number}"
        if message.text:
            content += message.text
        if message.media:
            if hasattr(message.media, 'document'):
                content += str(message.media.document.id)
            elif hasattr(message.media, 'photo'):
                content += str(message.media.photo.id)
        return hashlib.sha256(content.encode()).hexdigest()

    async def connect_client(self):
        """Conecta o cliente com segurança máxima"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Log seguro (não mostra dados sensíveis)
                logger.info(f"🔐 Conectando... Tentativa {attempt + 1}/{max_retries}")
                await self.client.start(
                    phone=self.config.phone_number,
                    password=self.config.two_fa_password
                )
                logger.info("✅ Conexão segura estabelecida!")
                return True
                
            except errors.SessionPasswordNeededError:
                logger.error("❌ Senha 2FA necessária. Verifique TWO_FA_PASSWORD.")
                return False
            except errors.PhoneNumberInvalidError:
                logger.error("❌ Número de telefone inválido.")
                return False
            except Exception as e:
                logger.warning(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt < max_retries - 1:
                    await sleep(10 * (attempt + 1))
        
        logger.error("🚫 Não foi possível conectar após várias tentativas.")
        return False

    async def get_all_messages(self, donor_id):
        """Coleta mensagens de forma segura"""
        try:
            messages = []
            async for message in self.client.iter_messages(donor_id, limit=None):
                if message:
                    messages.append(message)
            
            logger.info(f"📥 Coletadas {len(messages)} mensagens do doador {donor_id}")
            return messages
        except Exception as e:
            logger.error(f"❌ Erro ao coletar mensagens do doador {donor_id}: {e}")
            return []

    def is_message_sent_in_current_cycle(self, message):
        """Verifica se mensagem foi enviada no ciclo atual"""
        message_hash = self.generate_message_hash(message, self.current_cycle)
        return message_hash in self.sent_message_hashes

    def mark_message_as_sent(self, message):
        """Marca mensagem como enviada com segurança"""
        message_hash = self.generate_message_hash(message, self.current_cycle)
        self.sent_message_hashes.add(message_hash)
        self.save_sent_messages_secure()

    async def refresh_messages_for_cycle(self):
        """Atualiza mensagens para o ciclo atual"""
        logger.info(f"🔄 Atualizando mensagens para o ciclo {self.current_cycle}...")
        
        for donor_id in self.config.donor_recipient_pairs.keys():
            all_messages = await self.get_all_messages(donor_id)
            self.donor_messages[donor_id] = all_messages
            
            available_indices = [
                idx for idx, msg in enumerate(all_messages)
                if not self.is_message_sent_in_current_cycle(msg)
            ]
            self.available_messages[donor_id] = available_indices
        
        total_messages = sum(len(messages) for messages in self.donor_messages.values())
        total_available = sum(len(indices) for indices in self.available_messages.values())
        
        logger.info(f"📊 Ciclo {self.current_cycle} - {total_messages} total, {total_available} disponíveis")
        
        return total_available > 0

    def start_new_cycle(self):
        """Inicia novo ciclo com segurança"""
        self.current_cycle += 1
        self.cycle_state['current_cycle'] = self.current_cycle
        self.cycle_state['cycles_completed'] = self.cycle_state.get('cycles_completed', 0) + 1
        self.save_cycle_state_secure()
        
        self.available_messages = {}
        
        logger.info(f"🎉 NOVO CICLO {self.current_cycle} iniciado!")
        logger.info(f"🏆 Total de ciclos completados: {self.cycle_state['cycles_completed']}")

    async def send_random_message(self, donor_id, recipient_id):
        """Envia mensagem aleatória com tratamento seguro de erros"""
        if donor_id not in self.available_messages or not self.available_messages[donor_id]:
            return False

        available_indices = self.available_messages[donor_id]
        selected_index = random.choice(available_indices)
        original_message = self.donor_messages[donor_id][selected_index]

        # Processa álbuns
        if original_message.grouped_id:
            grouped_messages = [
                msg for msg in self.donor_messages[donor_id]
                if msg.grouped_id == original_message.grouped_id
            ]
            grouped_indices = [
                idx for idx, msg in enumerate(self.donor_messages[donor_id])
                if msg.grouped_id == original_message.grouped_id
                and idx in available_indices
            ]
        else:
            grouped_messages = [original_message]
            grouped_indices = [selected_index]

        # Remove do disponível
        for idx in grouped_indices:
            if idx in self.available_messages[donor_id]:
                self.available_messages[donor_id].remove(idx)

        # Envio seguro
        for attempt in range(3):
            try:
                await self.client.forward_messages(
                    recipient_id,
                    grouped_messages,
                    from_peer=grouped_messages[0].peer_id
                )
                
                for msg in grouped_messages:
                    self.mark_message_as_sent(msg)
                
                remaining = len(self.available_messages[donor_id])
                logger.info(f"✅ Mensagem enviada | Restantes: {remaining}")
                return True

            except errors.FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"⏳ Flood wait: {wait_time}s")
                await sleep(wait_time)
            except Exception as e:
                logger.error(f"❌ Tentativa {attempt + 1} falhou: {e}")
                if attempt < 2:
                    await sleep(5)

        logger.error("🚫 Falha ao enviar após 3 tentativas")
        return False

    async def check_and_manage_cycle(self):
        """Gerencia transição entre ciclos"""
        total_available = sum(len(indices) for indices in self.available_messages.values())
        
        if total_available == 0:
            logger.info("🎯 Todas as mídias enviadas! Iniciando novo ciclo...")
            await sleep(10)
            self.start_new_cycle()
            await self.refresh_messages_for_cycle()
            return True
        return False

    async def schedule_messages(self):
        """Agendamento principal com segurança"""
        await self.refresh_messages_for_cycle()

        while True:
            try:
                if await self.check_and_manage_cycle():
                    continue

                messages_sent = 0
                for donor_id, recipient_id in self.config.donor_recipient_pairs.items():
                    if self.available_messages.get(donor_id):
                        if await self.send_random_message(donor_id, recipient_id):
                            messages_sent += 1

                if messages_sent == 0:
                    logger.warning("⚠️ Nenhuma mensagem enviada. Verificando estado...")
                    await self.check_and_manage_cycle()

                next_interval = random.randint(self.config.min_interval, self.config.max_interval)
                next_time = datetime.now(self.config.timezone) + timedelta(seconds=next_interval)
                
                total_messages = sum(len(messages) for messages in self.donor_messages.values())
                total_available = sum(len(indices) for indices in self.available_messages.values())
                progress = ((total_messages - total_available) / total_messages * 100) if total_messages > 0 else 0
                
                logger.info(f"📈 Progresso: {progress:.1f}% | Próximo: {next_interval/60:.1f}min ({next_time.strftime('%H:%M')})")
                await sleep(next_interval)

            except Exception as e:
                logger.error(f"💥 Erro no agendamento: {e}")
                await sleep(300)

    async def run(self):
        """Execução principal segura"""
        logger.info("🚀 Iniciando Bot Seguro de Repostagem...")
        
        if not await self.connect_client():
            return

        try:
            await self.schedule_messages()
        except KeyboardInterrupt:
            logger.info("⏹️ Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"💥 Erro fatal: {e}")
        finally:
            await self.client.disconnect()
            logger.info("🔚 Bot finalizado com segurança")

# Função principal com reinício seguro
async def main():
    max_restarts = 10
    restart_delay = 60
    
    for restart_count in range(max_restarts):
        try:
            bot = SecureRepostBot()
            await bot.run()
        except Exception as e:
            logger.error(f"🔁 Bot crashou (tentativa {restart_count + 1}/{max_restarts}): {e}")
            if restart_count < max_restarts - 1:
                logger.info(f"Reiniciando em {restart_delay}s...")
                await sleep(restart_delay)
                restart_delay *= 2
            else:
                logger.error("🚫 Máximo de reinicializações atingido")
                break

if __name__ == "__main__":
    asyncio.run(main())
