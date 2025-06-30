from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import structlog
import uvicorn
from contextlib import asynccontextmanager

from app.config import settings
from app.api.v1 import chat, admin
from app.core.database import init_database, close_database
from app.services.memory_service_graphiti import memory_service_graphiti as memory_service
from app.core.neo4j_init import initialize_neo4j_schema


# Configuração do logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação
    """
    # Startup
    logger.info("Starting NeuroFlow - AI Memory Service")
    
    try:
        # Inicializa o banco de dados
        await init_database()
        logger.info("Database initialized")
        
        # Inicializa schema do Neo4j automaticamente
        await initialize_neo4j_schema()
        logger.info("Neo4j schema initialized")
        
        # Inicializa o serviço de memória
        await memory_service.initialize()
        logger.info("Memory service initialized")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down NeuroFlow")
        await close_database()
        logger.info("Database connection closed")


# Criação da aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="🧠 NeuroFlow - Microserviço inteligente com memória de grafos para potencializar agentes de IA",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure conforme necessário em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging de todas as requests
    """
    start_time = structlog.get_logger().info
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code
    )
    
    return response


# Inclusão das rotas
app.include_router(
    chat.router,
    prefix="/api/v1",
    tags=["Chat"]
)

app.include_router(
    admin.router,
    prefix="/api/v1/admin",
    tags=["Admin"]
)


@app.get("/")
async def root():
    """
    Redireciona para a documentação
    """
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    """
    Endpoint básico de health check
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
