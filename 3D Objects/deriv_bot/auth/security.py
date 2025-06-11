from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from core.config import settings # Importa as configurações, incluindo ENCRYPTION_KEY
from cryptography.fernet import Fernet
import base64

# Contexto para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Inicializa o Fernet para criptografia
# A chave deve ser base64-encoded e ter 32 bytes de comprimento.
# É crucial que settings.ENCRYPTION_KEY seja uma chave segura e gerada corretamente.
try:
    fernet = Fernet(settings.ENCRYPTION_KEY.encode('utf-8'))
except Exception as e:
    # Em um ambiente real, você pode querer logar isso e sair,
    # ou ter um fallback mais robusto.
    print(f"ERRO: Chave de criptografia inválida ou ausente em settings.ENCRYPTION_KEY. {e}")
    # Para desenvolvimento, pode-se usar uma chave de fallback INSEGURA, mas NUNCA em produção.
    # fernet = Fernet(Fernet.generate_key()) # NÃO FAÇA ISSO EM PRODUÇÃO!
    fernet = None # Marcar como None para indicar falha na inicialização

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se uma senha em texto simples corresponde a uma senha hash.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Gera o hash de uma senha em texto simples.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Cria um token de acesso JWT com base nos dados fornecidos e um tempo de expiração.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def encrypt_data(data: str) -> str | None:
    """
    Criptografa uma string usando Fernet.
    Retorna a string criptografada em base64.
    Retorna None se Fernet não foi inicializado corretamente.
    """
    if fernet is None:
        print("ERRO: Fernet não inicializado. Não é possível criptografar.")
        return None
    try:
        encrypted_bytes = fernet.encrypt(data.encode('utf-8'))
        return encrypted_bytes.decode('utf-8') # Retorna como string base64
    except Exception as e:
        print(f"ERRO ao criptografar dados: {e}")
        return None

def decrypt_data(encrypted_data: str) -> str | None:
    """
    Descriptografa uma string criptografada usando Fernet.
    Retorna a string descriptografada.
    Retorna None se Fernet não foi inicializado corretamente ou se a descriptografia falhar.
    """
    if fernet is None:
        print("ERRO: Fernet não inicializado. Não é possível descriptografar.")
        return None
    try:
        decrypted_bytes = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        print(f"ERRO ao descriptografar dados: {e}. Verifique a chave de criptografia ou os dados.")
        return None

