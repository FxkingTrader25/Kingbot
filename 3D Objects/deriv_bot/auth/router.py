# auth/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

# Importa o modelo User E o pwd_context diretamente
from models.user import User, pwd_context # Importa pwd_context aqui
from core.config import settings # Importa as configurações do sistema

# Cria uma instância do APIRouter para as rotas de autenticação
router = APIRouter()

# Schema para criação de usuário (registro)
class UserCreate(BaseModel):
    username: str
    password: str

# Rota para registro de novos usuários
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserCreate)
async def register_user(user_data: UserCreate):
    # Verifica se o usuário já existe
    existing_user = await User.get_or_none(username=user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já registrado"
        )
    
    # Cria o novo usuário com a senha hasheada
    # Agora usa pwd_context diretamente, pois foi importado
    user = await User.create(
        username=user_data.username,
        hashed_password=pwd_context.hash(user_data.password) 
    )
    
    # Define um trial premium para novos usuários (exemplo: 7 dias)
    user.premium_trial_end_date = datetime.now(timezone.utc) + timedelta(days=7)
    await user.save()

    print(f"DEBUG: Usuário {user.username} registrado com sucesso com trial até {user.premium_trial_end_date}.")
    return user_data # Retorna os dados do usuário (sem a senha hasheada)

# Helper para criar tokens de acesso JWT
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Use a timezone aware datetime for expiration
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# Rota para login e obtenção de token de acesso
@router.post("/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Tenta obter o usuário pelo username
    user = await User.get_or_none(username=form_data.username)
    
    # Verifica se o usuário existe e se a senha está correta
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria o token de acesso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    print(f"INFO: Usuário {user.username} logado com sucesso.")
    return {"access_token": access_token, "token_type": "bearer"}

