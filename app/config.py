from decouple import config
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Configurações da aplicação
    app_name: str = config("APP_NAME", default="NeuroFlow")
    app_version: str = config("APP_VERSION", default="0.1.0")
    debug: bool = config("DEBUG", default=False, cast=bool)
    log_level: str = config("LOG_LEVEL", default="INFO")
    
    # Configurações do servidor
    host: str = config("HOST", default="0.0.0.0")
    port: int = config("PORT", default=8000, cast=int)
    
    # Configurações de autenticação
    secret_key: str = config("SECRET_KEY")
    algorithm: str = config("ALGORITHM", default="HS256")
    access_token_expire_minutes: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    
    # Configurações do PostgreSQL
    postgres_host: str = config("POSTGRES_HOST", default="localhost")
    postgres_port: int = config("POSTGRES_PORT", default=5432, cast=int)
    postgres_db: str = config("POSTGRES_DB", default="ai_memory_db")
    postgres_user: str = config("POSTGRES_USER", default="postgres")
    postgres_password: str = config("POSTGRES_PASSWORD", default="postgres")
    
    # Configurações do Redis
    redis_host: str = config("REDIS_HOST", default="localhost")
    redis_port: int = config("REDIS_PORT", default=6379, cast=int)
    redis_db: int = config("REDIS_DB", default=0, cast=int)
    redis_password: Optional[str] = config("REDIS_PASSWORD", default=None)
    
    # Configurações do Neo4j
    neo4j_uri: str = config("NEO4J_URI", default="bolt://localhost:7687")
    neo4j_user: str = config("NEO4J_USER", default="neo4j")
    neo4j_password: str = config("NEO4J_PASSWORD", default="neo4j123")
    
    # Configurações do Flowise
    flowise_api_url: str = config("FLOWISE_API_URL", default="http://localhost:3000")
    flowise_api_key: Optional[str] = config("FLOWISE_API_KEY", default=None)
    
    # Configurações do Graphiti
    graphiti_llm_model: str = config("GRAPHITI_LLM_MODEL", default="gpt-4")
    graphiti_embedding_model: str = config("GRAPHITI_EMBEDDING_MODEL", default="text-embedding-ada-002")
    openai_api_key: str = config("OPENAI_API_KEY")
    
    # Configurações do Celery
    celery_broker_url: str = config("CELERY_BROKER_URL", default="redis://localhost:6379/1")
    celery_result_backend: str = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    class Config:
        env_file = ".env"


settings = Settings()
