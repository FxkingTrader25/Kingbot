from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    """
    Configurações do sistema, carregadas de variáveis de ambiente ou do arquivo .env.
    """
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./kingbot.db") # Alterado para um nome mais específico

    # CHAVE SECRETA PARA JWT: MUDE ISTO EM PRODUÇÃO!
    # É crucial que esta chave seja uma string longa e aleatória e armazenada de forma segura (ex: variável de ambiente).
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "uma_chave_muito_secreta_e_aleatoria_para_jwt_nao_use_esta_em_producao_por_favor")
    
    ALGORITHM: str = os.environ.get("ALGORITHM", "HS256") # Algoritmo para JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24)) # Tempo de expiração do token JWT (padrão: 1 dia)

    # CHAVE PARA CRIPTOGRAFIA DE DADOS SENSÍVEIS (EX: DERIV_TOKEN)
    # ESTA É UMA CHAVE DE EXEMPLO INSEGURA. VOCÊ DEVE GERAR A SUA PRÓPRIA!
    # Gere uma com `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`
    ENCRYPTION_KEY: str = os.environ.get("ENCRYPTION_KEY", "KgyuTCGK5JgLH-nnxilwiqxXni2rlUJ6Zpv5_fMYJng=") # Substitua por uma chave real

    # Deriv API Configurações
    DERIV_APP_ID: int = int(os.environ.get("DERIV_APP_ID", 1089)) # Exemplo de ID de APP, use o seu
    DERIV_WEBSOCKET_URL: str = os.environ.get("DERIV_WEBSOCKET_URL", "wss://ws.binaryws.com/websockets/v3")

    class Config:
        """
        Configurações para Pydantic Settings.
        Carrega variáveis de ambiente de um arquivo .env.
        """
        env_file = ".env"
        # Permite que as variáveis de ambiente sobrescrevam as
        # configurações padrão ou as carregadas do .env
        env_file_encoding = 'utf-8'

settings = Settings()
