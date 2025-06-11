from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserInDB(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True # Habilita compatibilidade com ORM (Tortoise-ORM neste caso)
