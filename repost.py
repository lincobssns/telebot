import asyncio
import os
import random
import logging
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv
from telethon import TelegramClient, errors
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
        """Deriva uma chave de criptografia com fallback"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        
        # Se não encontrar, gera uma chave temporária e loga alerta
        if not encryption_key:
            logger.warning("⚠️ ENCRYPTION_KEY não encontrada. Gerando chave temporária...")
            temporary_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            logger.warning(f"⚠️ Use esta chave como ENCRYPTION_KEY no Railway: {temporary_key}")
            encryption_key = temporary_key
        
        # Usa PBKDF2 para derivar uma chave segura
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'secure_repost_bot_salt',
            iterations=100000,
        )
        key = kdf.derive(encryption_key.encode())
        return base64.urlsafe_b64encode(key)
    
    def encrypt(self, data):
        """Criptografa dados sensíveis"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        try:
            encrypted = self.fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Erro ao criptografar: {e}")
            return data.decode('utf-8') if isinstance(data, bytes) else data
    
    def decrypt(self, encrypted_data):
        """Descriptografa dados sensíveis"""
        try:
            decrypted = self.fernet.decrypt(base64.urlsafe_b64decode(encrypted_data))
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Erro ao descriptografar: {e}")
            return encrypted_data

class SecureConfig:
    def __init__(self):
        self.data_manager = SecureDataManager()
        self.load_config()
    
    def load_config(self):
        """Carrega e valida configurações com fallbacks"""
        try:
            # Telegram API (com valores padrão)
            self.api_id = int(os.getenv('API_ID', '28881388'))
            self.api_hash = os.getenv('API_HASH', 'd9e8b04bb4a85f373cc9ba4692dd6cf4')
            self.phone_number = os.getenv('PHONE_NUMBER', '+5541988405232')
            self.two_fa_password = os.getenv('TWO_FA_PASSWORD', '529702')
            
            # Bot Settings
            self.session_name = os.getenv('SESSION_NAME', 'telegram_session')
            self.min_interval = int(os.getenv('MIN_INTERVAL', '1800'))
            self.max_interval = int(os.getenv('MAX_INTERVAL', '7200'))
            
            # Channel pairs
            pairs_str = os.getenv('CHANNEL_PAIRS', '-1002877945842:-1002760356238')
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
                    pairs[int(donor.strip())] = int(recipient.strip())
        
        # Fallback se não encontrar pares
        if not pairs:
            pairs = {-1002877945842: -1002760356238}
            logger.warning("⚠️ Usando pares de canal padrão")
        
        return pairs
    
    def _validate_config(self):
        """Valida configurações essenciais"""
        if not self.api_id or not self.api_hash:
            raise ValueError("API_ID e API_HASH são obrigatórios")
        
        if not self.phone_number:
            raise ValueError("PHONE_NUMBER é obrigatório")

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
            logger.error(f"❌ Erro ao carregar mensagens: {e}")
            return set()

    def save_sent_messages_secure(self):
        """Salva mensagens enviadas de forma criptografada"""
        try:
            data = '\n'.join(self.sent_message_hashes)
            encrypted_data = self.data_manager.encrypt(data)
            with open(self.sent_messages_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagens: {e}")

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
            logger.error(f"❌ Erro ao carregar ciclo: {e}")
            return {'current_cycle': 1, 'cycles_completed': 0}

    def save_cycle_state_secure(self):
        """Salva estado do ciclo de forma criptografada"""
        try:
            data = json.dumps(self.cycle_state)
            encrypted_data = self.data_manager.encrypt(data)
            with open(self.cycle_state_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar ciclo: {e}")

    def generate_message_hash(self, message, cycle_number=1):
        """Gera hash único para mensagem"""
        import hashlib
        content = f"{message.id}_{message.chat_id}_cycle{cycle_number}"
        if message.text:
            content += message.text
        if message.media:
            content += str(getattr(message.media, 'id', ''))
        return hashlib.sha256(content.encode()).hexdigest()

    async def connect_client(self):
        """Conecta o cliente com segurança máxima"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"🔐 Conectando... Tentativa {attempt + 1}/{max_retries}")
                await self.client.start(
                    phone=self.config.phone_number,
                    password=self.config.two_fa_password
                )
                logger.info("✅ Conexão estabelecida!")
                return True
                
            except errors.SessionPasswordNeededError:
                logger.error("❌ Senha 2FA necessária.")
                return False
            except Exception as e:
                logger.warning(f"⚠️ Tentativa {attempt + 1} falhou: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(10 * (attempt + 1))
        
        logger.error("🚫 Não foi possível conectar.")
        return False

    async def get_all_messages(self, donor_id):
        """Coleta mensagens do canal doador"""
        try:
            messages = []
            async for message in self.client.iter_messages(donor_id, limit=500):
                if message:
                    messages.append(message)
            
            logger.info(f"📥 {len(messages)} mensagens de {donor_id}")
            return messages
        except Exception as e:
            logger.error(f"❌ Erro ao coletar mensagens: {e}")
            return []

    def is_message_sent_in_current_cycle(self, message):
        """Verifica se mensagem foi enviada no ciclo atual"""
        message_hash = self.generate_message_hash(message, self.current_cycle)
        return message_hash in self.sent_message_hashes

    def mark_message_as_sent(self, message):
        """Marca mensagem como enviada"""
        message_hash = self.generate_message_hash(message, self.current_cycle)
        self.sent_message_hashes.add(message_hash)
        self.save_sent_messages_secure()

    async def refresh_messages_for_cycle(self):
        """Atualiza mensagens para o ciclo atual"""
        logger.info(f"🔄 Ciclo {self.current_cycle}")
        
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
        
        logger.info(f"📊 {total_messages} total, {total_available} disponíveis")
        
        return total_available > 0

    def start_new_cycle(self):
        """Inicia novo ciclo"""
        self.current_cycle += 1
        self.cycle_state['current_cycle'] = self.current_cycle
        self.cycle_state['cycles_completed'] = self.cycle_state.get('cycles_completed', 0) + 1
        self.save_cycle_state_secure()
        
        self.available_messages = {}
        
        logger.info(f"🎉 NOVO CICLO {self.current_cycle}!")
        logger.info(f"🏆 Ciclos completados: {self.cycle_state['cycles_completed']}")

    async def send_random_message(self, donor_id, recipient_id):
        """Envia mensagem aleatória"""
        if donor_id not in self.available_messages or not self.available_messages[donor_id]:
            return False

        available_indices = self.available_messages[donor_id]
        selected_index = random.choice(available_indices)
        original_message = self.donor_messages[donor_id][selected_index]

        grouped_messages = [original_message]
        grouped_indices = [selected_index]

        # Remove do disponível
        for idx in grouped_indices:
            if idx in self.available_messages[donor_id]:
                self.available_messages[donor_id].remove(idx)

        # Envio
        for attempt in range(3):
            try:
                await self.client.forward_messages(recipient_id, grouped_messages)
                
                for msg in grouped_messages:
                    self.mark_message_as_sent(msg)
                
                remaining = len(self.available_messages[donor_id])
                logger.info(f"✅ Mensagem enviada | Restantes: {remaining}")
                return True

            except errors.FloodWaitError as e:
                wait_time = e.seconds
                logger.warning(f"⏳ Flood wait: {wait_time}s")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"❌ Tentativa {attempt + 1} falhou: {e}")
                if attempt < 2:
                    await asyncio.sleep(5)

        logger.error("🚫 Falha ao enviar")
        return False

    async def check_and_manage_cycle(self):
        """Gerencia transição entre ciclos"""
        total_available = sum(len(indices) for indices in self.available_messages.values())
        
        if total_available == 0:
            logger.info("🎯 Todas as mídias enviadas! Novo ciclo...")
            await asyncio.sleep(10)
            self.start_new_cycle()
            await self.refresh_messages_for_cycle()
            return True
        return False

    async def schedule_messages(self):
        """Agendamento principal"""
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
                    await self.check_and_manage_cycle()

                next_interval = random.randint(self.config.min_interval, self.config.max_interval)
                next_time = datetime.now(self.config.timezone) + timedelta(seconds=next_interval)
                
                total_messages = sum(len(messages) for messages in self.donor_messages.values())
                total_available = sum(len(indices) for indices in self.available_messages.values())
                progress = ((total_messages - total_available) / total_messages * 100) if total_messages > 0 else 0
                
                logger.info(f"📈 Progresso: {progress:.1f}% | Próximo: {next_interval/60:.1f}min")
                await asyncio.sleep(next_interval)

            except Exception as e:
                logger.error(f"💥 Erro: {e}")
                await asyncio.sleep(300)

    async def run(self):
        """Execução principal"""
        logger.info("🚀 Iniciando Bot...")
        
        if not await self.connect_client():
            return

        try:
            await self.schedule_messages()
        except KeyboardInterrupt:
            logger.info("⏹️ Bot interrompido")
        except Exception as e:
            logger.error(f"💥 Erro fatal: {e}")
        finally:
            await self.client.disconnect()
            logger.info("🔚 Bot finalizado")

async def main():
    max_restarts = 10
    restart_delay = 60
    
    for restart_count in range(max_restarts):
        try:
            bot = SecureRepostBot()
            await bot.run()
        except Exception as e:
            logger.error(f"🔁 Crash {restart_count + 1}/{max_restarts}: {e}")
            if restart_count < max_restarts - 1:
                logger.info(f"Reiniciando em {restart_delay}s...")
                await asyncio.sleep(restart_delay)
                restart_delay *= 2
            else:
                logger.error("🚫 Máximo de reinicializações")
                break

if __name__ == "__main__":
    asyncio.run(main())
