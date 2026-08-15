"""
Database configuration module.

Note: This module is deprecated. Use config/settings.py for all configurations instead.
"""

from __future__ import annotations

import os
from typing import Optional

from config.settings import settings


def _get_port_from_env() -> Optional[int]:
    """
    Get database port from the environment variable.
    
    Returns:
        Port number or None if not set
    """
    port_str = settings.db_port
    if port_str is not None:
        return int(port_str)
    return None


class DatabaseConfig:
    """
    Database configuration class.

    """

    def __init__(self):
        """Initialize database config."""
        pass

    HOST: Optional[str] = settings.db_host
    PORT: Optional[int] = settings.db_port
    USER: Optional[str] = settings.db_user
    PASSWORD: Optional[str] = settings.db_password
    DATABASE: Optional[str] = settings.db_name

    @classmethod
    def db_con_as_string(cls) -> str:
        """
        Get database connection string (synchronous).
        
        Returns:
            PostgreSQL connection string
            
        Raises:
            ValueError: If the required database configuration is missing
        """
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

    @classmethod
    def async_db_con_as_string(cls) -> str:
        """
        Get async database connection string.
        
        Returns:
            PostgreSQL asyncpg connection string
            
        Raises:
            ValueError: If the required database configuration is missing
        """
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql+asyncpg://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

    @classmethod
    def psycopg_db_con_as_string(cls) -> str:
        """
        Get psycopg database connection string.

        Returns:
            PostgreSQL psycopg connection string

        Raises:
            ValueError: If the required database configuration is missing
        """
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql+psycopg://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"

    @classmethod
    def psycopg2_db_con_as_string(cls) -> str:
        """
        Get psycopg2 database connection string.

        Returns:
            PostgreSQL psycopg2 connection string

        Raises:
            ValueError: If the required database configuration is missing
        """
        if cls.USER is None or cls.PASSWORD is None or cls.HOST is None or cls.PORT is None or cls.DATABASE is None:
            raise ValueError("Missing required database configuration")
        return f"postgresql+psycopg2://{cls.USER}:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DATABASE}"
