from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.models.schemas import ChatRequest, ChatResponse, MemoryContext
from app.services.memory_service import memory_service
from app.services.flowise_service import flowise_service
from app.core.auth import get_api_key
from app.core.database import get_session
from app.tasks.memory_tasks import update_memory_sync
import structlog
from datetime import datetime
import uuid

logger = structlog.get_logger()
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_prediction(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key),
    db_session = Depends(get_session)
):
    """
    Endpoint principal para chat com integração de memória
    """
    try:
        logger.info(f"Received chat request for user {request.user_id}, session {request.session_id}")
        
        # 1. Recupera contextos de memória
        memory_context = MemoryContext()
        
        # Contexto do usuário (persistente)
        user_context = await memory_service.get_user_context(
            user_id=request.user_id,
            query=request.question,
            limit=5
        )
        if user_context:
            memory_context.user_context = user_context
        
        # Contexto da sessão
        session_context = await memory_service.get_session_context(
            session_id=request.session_id,
            query=request.question,
            limit=10
        )
        if session_context:
            memory_context.session_context = session_context
        
        # Contexto da empresa (read-only)
        company_context = await memory_service.get_company_context(
            company_id=request.company_id
        )
        if company_context:
            memory_context.company_context = company_context
        
        # 2. Envia request para o Flowise
        flowise_response = await flowise_service.send_prediction(
            question=request.question,
            session_id=request.session_id,
            user_id=request.user_id,
            company_id=request.company_id,
            memory_context=memory_context,
            additional_context=request.additional_context
        )
        
        if not flowise_response:
            raise HTTPException(status_code=502, detail="Falha na comunicação com o Flowise")
        
        # 3. Programa atualização da memória em background
        task_id = update_memory_sync(
            user_id=request.user_id,
            session_id=request.session_id,
            company_id=request.company_id,
            question=request.question,
            answer=flowise_response.text
        )
        
        # 4. Prepara resposta padronizada
        response = ChatResponse(
            text=flowise_response.text,
            execution_id=flowise_response.executionId,
            session_id=request.session_id,
            user_id=request.user_id,
            company_id=request.company_id,
            timestamp=datetime.now(),
            memory_updated=False  # Será atualizado em background
        )
        
        logger.info(f"Chat response sent for execution {flowise_response.executionId}")
        return response
        
    except Exception as e:
        logger.error(f"Error in chat prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@router.get("/memory/user/{user_id}")
async def get_user_memory(
    user_id: str,
    query: str,
    limit: int = 10,
    api_key: str = Depends(get_api_key)
):
    """
    Recupera memória do usuário para uma query específica
    """
    try:
        context = await memory_service.get_user_context(
            user_id=user_id,
            query=query,
            limit=limit
        )
        
        return {
            "user_id": user_id,
            "query": query,
            "context": context,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting user memory: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar memória do usuário: {str(e)}")


@router.get("/memory/session/{session_id}")
async def get_session_memory(
    session_id: str,
    query: str,
    limit: int = 20,
    api_key: str = Depends(get_api_key)
):
    """
    Recupera memória da sessão para uma query específica
    """
    try:
        context = await memory_service.get_session_context(
            session_id=session_id,
            query=query,
            limit=limit
        )
        
        return {
            "session_id": session_id,
            "query": query,
            "context": context,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting session memory: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar memória da sessão: {str(e)}")


@router.delete("/memory/session/{session_id}")
async def clear_session_memory(
    session_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Limpa memória da sessão
    """
    try:
        success = await memory_service.clear_session_memory(session_id)
        
        if success:
            return {
                "message": f"Memória da sessão {session_id} limpa com sucesso",
                "timestamp": datetime.now()
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao limpar memória da sessão")
            
    except Exception as e:
        logger.error(f"Error clearing session memory: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar memória da sessão: {str(e)}")


@router.get("/knowledge-graph/user/{user_id}")
async def get_user_knowledge_graph(
    user_id: str,
    limit: int = 50,
    api_key: str = Depends(get_api_key)
):
    """
    Recupera o grafo de conhecimento do usuário (entidades e relacionamentos)
    """
    try:
        async with memory_service.driver.session() as session:
            # Busca entidades do usuário
            entities_result = await session.run("""
                MATCH (e:UserEntity)
                WHERE e.user_id = $user_id
                RETURN e.name as name, e.type as type, e.description as description,
                       e.attributes as attributes, e.updated_at as updated_at
                ORDER BY e.updated_at DESC
                LIMIT $limit
            """, user_id=user_id, limit=limit)
            
            entities = await entities_result.data()
            
            # Busca relacionamentos
            relationships_result = await session.run("""
                MATCH (source:UserEntity)-[r:RELATED]->(target:UserEntity)
                WHERE source.user_id = $user_id AND target.user_id = $user_id
                RETURN source.name as source, target.name as target,
                       r.type as relationship_type, r.description as description,
                       r.strength as strength, r.updated_at as updated_at
                ORDER BY r.updated_at DESC
                LIMIT $limit
            """, user_id=user_id, limit=limit)
            
            relationships = await relationships_result.data()
        
        return {
            "user_id": user_id,
            "entities": entities,
            "relationships": relationships,
            "stats": {
                "total_entities": len(entities),
                "total_relationships": len(relationships)
            },
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar grafo de conhecimento: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Endpoint de health check
    """
    try:
        # Verifica conexão com Flowise
        flowise_healthy = await flowise_service.health_check()
        
        # Verifica conexão com Neo4j (memória)
        memory_healthy = memory_service._initialized
        
        return {
            "status": "healthy" if flowise_healthy and memory_healthy else "degraded",
            "services": {
                "flowise": "healthy" if flowise_healthy else "unhealthy",
                "memory": "healthy" if memory_healthy else "unhealthy"
            },
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now()
        }
