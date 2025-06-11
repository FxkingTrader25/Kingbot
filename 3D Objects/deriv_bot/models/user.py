# models/user.py

from tortoise.models import Model
from tortoise import fields
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from core.config import settings # Garante que settings.ENCRYPTION_KEY é acessível
from datetime import datetime, timezone, timedelta

# Contexto para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# A chave de criptografia Fernet deve ser a mesma para todos os usuários ou derivada de forma segura.
# Usaremos a chave global das settings, que é mais prática para este contexto.
# É importante que settings.ENCRYPTION_KEY seja bytes (b'...')
try:
    # Garante que a chave Fernet é um bytes-like object
    cipher_suite = Fernet(settings.ENCRYPTION_KEY.encode('utf-8'))
except Exception as e:
    print(f"Erro ao inicializar Fernet no models/user.py: {e}")
    print("Certifique-se de que ENCRYPTION_KEY é uma chave Fernet válida e codificada em UTF-8.")
    cipher_suite = Fernet(Fernet.generate_key()) # fallback inseguro para dev

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    hashed_password = fields.CharField(max_length=128)
    
    # Token da Deriv encriptado
    deriv_token_encrypted = fields.TextField(null=True)

    # Configurações de Trading
    stake = fields.FloatField(default=1.0) # Stake (valor em USD para a aposta)
    duration = fields.IntField(default=60) # Duração para CALL/PUT em segundos
    candle_granularity = fields.IntField(default=60) # Granularidade da vela em segundos
    logica_estrategia = fields.CharField(max_length=10, default="OR") # Lógica de combinação de estratégias

    # Configurações de TP/SL para Call/Put (contagem de vitórias/derrotas)
    take_profit = fields.IntField(null=True, default=None) # Número de vitórias para TP
    stop_loss = fields.IntField(null=True, default=None)   # Número de derrotas para SL

    # Parâmetros para Acumuladores
    accumulator_growth_rate = fields.FloatField(default=0.01) # Taxa de crescimento
    # Adicionado como campos diretos, permitindo serem nulos
    take_profit_accumulator = fields.FloatField(null=True, default=None) # Valor em USD para TP do Acumulador
    stop_loss_accumulator = fields.FloatField(null=True, default=None)   # Valor em USD para SL do Acumulador (fixo)

    # Parâmetros para Multiplicadores
    multiplier_value = fields.IntField(default=100) # Valor do multiplicador
    take_profit_multiplier = fields.FloatField(null=True, default=None) # Valor em USD para TP do Multiplicador
    stop_loss_multiplier = fields.FloatField(null=True, default=None)   # Valor em USD para SL do Multiplicador

    # Tipo de contrato a operar
    contract_type_to_trade = fields.CharField(max_length=20, default="CALLPUT") # CALLPUT, ACCUMULATOR, MULTIPLIER
    
    # Estratégias (armazenadas como JSON para flexibilidade)
    estrategias_config_json = fields.JSONField(default=dict) # Default para um dicionário vazio

    # Gestão de Plano e Acesso
    is_admin = fields.BooleanField(default=False)
    plan_type = fields.CharField(max_length=20, default="free")
    premium_trial_end_date = fields.DatetimeField(null=True) # Data de fim do trial premium
    
    class Meta:
        table = "users" # Nome da tabela na base de dados

    # Métodos para encriptação/desencriptação do token Deriv
    # Use a propriedade @deriv_token.setter para definir e @property para obter
    def set_deriv_token(self, token: str | None):
        """Encripta e armazena o token da Deriv. Se token for None, limpa o campo."""
        if token:
            try:
                self.deriv_token_encrypted = cipher_suite.encrypt(token.encode()).decode()
            except Exception as e:
                print(f"Erro ao encriptar token: {e}")
                self.deriv_token_encrypted = None 
        else:
            self.deriv_token_encrypted = None 

    def get_deriv_token(self) -> str | None:
        """Desencripta e retorna o token da Deriv."""
        if not self.deriv_token_encrypted:
            return None
        try:
            return cipher_suite.decrypt(self.deriv_token_encrypted.encode()).decode()
        except Exception as e:
            print(f"Erro ao desencriptar token: {e}")
            return None 

    # Métodos de autenticação e plano
    def verify_password(self, plain_password):
        """Verifica a senha plain_password contra a senha hash armazenada."""
        return pwd_context.verify(plain_password, self.hashed_password)

    def is_premium_active(self) -> bool:
        """Verifica se o utilizador tem plano premium ou trial ativo."""
        if self.plan_type == "premium":
            return True
        if self.premium_trial_end_date and self.premium_trial_end_date > datetime.now(timezone.utc):
            return True
        return False

    def is_trial_active(self) -> bool:
        """Verifica se o utilizador está em trial."""
        return self.premium_trial_end_date and self.premium_trial_end_date > datetime.now(timezone.utc)

    def get_strategy_config(self) -> dict:
        """Retorna as configurações de estratégia, garantindo que é um dicionário."""
        return self.estrategias_config_json if isinstance(self.estrategias_config_json, dict) else {}

