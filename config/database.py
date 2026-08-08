import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

def _get_port_from_env() -> Optional[int]:
    port_str = os.getenv("PORT")
    if port_str is not None:
        return int(port_str)
    return None

class DatabaseConfig:
    def __init__(self):
        pass

    HOST: Optional[str] = os.getenv("HOST")
    PORT: Optional[int] = _get_port_from_env()
    USER: Optional[str] = os.getenv("USER")
    PASSWORD: Optional[str] = os.getenv("PASSWORD")
    DATABASE: Optional[str] = os.getenv("DATABASE")

    @classmethod
    def db_con_as_string(cls) -> str:
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

    @classmethod
    def async_db_con_as_string(cls) -> str:
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql+asyncpg://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

