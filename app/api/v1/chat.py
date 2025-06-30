from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from app.models.schemas import ChatRequest, ChatResponse, MemoryContext
from app.services.memory_service_graphiti import memory_service_graphiti as memory_service
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
            additional_context=request.additional_context,
            chatflow_id=request.chatflow_id
        )
        
        if not flowise_response:
            raise HTTPException(status_code=502, detail="Falha na comunicação com o Flowise")
        
        # 3. Tenta atualizar memória imediatamente (para debug)
        memory_updated = False
        try:
            # Para debug, vamos tentar direto sem background task
            memory_success = await memory_service.add_user_memory(
                user_id=request.user_id,
                question=request.question,
                answer=flowise_response.text,
                context={"company_id": request.company_id, "session_id": request.session_id}
            )
            memory_updated = memory_success
            logger.info(f"Memory update direct: {memory_success}")
        except Exception as e:
            logger.error(f"Failed to update memory directly: {e}")
            # Como backup, agenda background task
            try:
                task_id = update_memory_sync(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    company_id=request.company_id,
                    question=request.question,
                    answer=flowise_response.text
                )
                logger.info(f"Memory update task queued as backup: {task_id}")
            except Exception as backup_error:
                logger.error(f"Failed to queue backup memory task: {backup_error}")
        
        # 4. Prepara resposta padronizada
        response = ChatResponse(
            text=flowise_response.text,
            execution_id=flowise_response.executionId,
            session_id=request.session_id,
            user_id=request.user_id,
            company_id=request.company_id,
            timestamp=datetime.now(),
            memory_updated=memory_updated
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


@router.get("/graph/query/{user_id}")
async def query_knowledge_graph(
    user_id: str,
    question: str,
    api_key: str = Depends(get_api_key)
):
    """
    Consulta direta ao grafo de conhecimento usando linguagem natural
    """
    try:
        result = await memory_service.query_graph(
            user_id=user_id,
            question=question
        )
        
        if not result:
            return {
                "user_id": user_id,
                "question": question,
                "message": "Nenhum resultado encontrado ou query não pode ser gerada",
                "timestamp": datetime.now()
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Error querying knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao consultar grafo: {str(e)}")


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


@router.get("/debug/neo4j-test")
async def test_neo4j_connection(api_key: str = Depends(get_api_key)):
    """
    Testa conexão e inicialização do Neo4j
    """
    try:
        await memory_service.ensure_initialized()
        
        # Testa conexão básica
        async with memory_service.driver.session() as session:
            # Conta nós existentes
            result = await session.run("MATCH (n) RETURN count(n) as total")
            record = await result.single()
            node_count = record["total"]
            
            # Lista labels existentes
            result = await session.run("CALL db.labels()")
            labels = [record["label"] async for record in result]
            
            # Lista tipos de relacionamento
            result = await session.run("CALL db.relationshipTypes()")
            relationships = [record["relationshipType"] async for record in result]
            
            return {
                "neo4j_connected": True,
                "total_nodes": node_count,
                "existing_labels": labels,
                "existing_relationships": relationships,
                "is_empty": node_count == 0,
                "timestamp": datetime.now()
            }
            
    except Exception as e:
        logger.error(f"Neo4j connection test failed: {e}")
        return {
            "neo4j_connected": False,
            "error": str(e),
            "timestamp": datetime.now()
        }


@router.post("/debug/create-test-data")
async def create_test_data(api_key: str = Depends(get_api_key)):
    """
    Cria dados de teste no Neo4j para verificar se tudo funciona
    """
    try:
        await memory_service.ensure_initialized()
        
        # Cria dados de teste diretamente
        async with memory_service.driver.session() as session:
            # Cria um nó de teste
            await session.run("""
                CREATE (m:UserMemory:Memory {
                    id: 'test_memory_001',
                    user_id: 'test_user_001',
                    question: 'Qual é o meu nome?',
                    answer: 'Seu nome é João Silva.',
                    summary: 'Usuário perguntou sobre seu nome',
                    timestamp: datetime()
                })
            """)
            
            # Cria uma entidade de teste
            await session.run("""
                CREATE (e:UserEntity:Entity {
                    id: 'test_entity_001',
                    user_id: 'test_user_001',
                    name: 'João Silva',
                    type: 'PERSON',
                    description: 'Usuário do sistema',
                    created_at: datetime(),
                    updated_at: datetime()
                })
            """)
            
            # Verifica se criou
            result = await session.run("MATCH (n) RETURN count(n) as total")
            record = await result.single()
            total_nodes = record["total"]
            
            return {
                "success": True,
                "message": "Dados de teste criados",
                "total_nodes_after": total_nodes,
                "timestamp": datetime.now()
            }
            
    except Exception as e:
        logger.error(f"Failed to create test data: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar dados de teste: {str(e)}")


@router.post("/debug/test-memory")
async def test_memory_direct(
    request: ChatRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Endpoint de debug para testar memória diretamente (sem Celery)
    """
    try:
        logger.info(f"🧪 Testing memory directly for user {request.user_id}")
        
        # Testa memória diretamente sem background task
        success = await memory_service.add_user_memory(
            user_id=request.user_id,
            question=request.question,
            answer="Resposta de teste para debug",
            context={"debug": True, "company_id": request.company_id}
        )
        
        return {
            "success": success,
            "message": "Teste de memória executado",
            "user_id": request.user_id,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Debug test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no teste: {str(e)}")


@router.post("/debug/init-schema")
async def init_neo4j_schema(api_key: str = Depends(get_api_key)):
    """Inicializa schema completo do Neo4j"""
    try:
        await memory_service.ensure_initialized()
        
        # Cria constraints e índices
        schema_queries = [
            # Constraints
            "CREATE CONSTRAINT user_memory_id IF NOT EXISTS FOR (m:UserMemory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT session_memory_id IF NOT EXISTS FOR (m:SessionMemory) REQUIRE m.id IS UNIQUE", 
            "CREATE CONSTRAINT company_memory_id IF NOT EXISTS FOR (m:CompanyMemory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT user_entity_id IF NOT EXISTS FOR (e:UserEntity) REQUIRE e.id IS UNIQUE",
            
            # Adiciona dados com propriedades completas
            """
            MERGE (um:UserMemory:Memory {
                id: "sample_user_memory",
                user_id: "sample_user",
                question: "Exemplo de pergunta",
                answer: "Exemplo de resposta", 
                summary: "Resumo exemplo",
                timestamp: datetime(),
                embedding: [0.1, 0.2, 0.3, 0.4, 0.5]
            })
            """,
            
            """
            MERGE (cm:CompanyMemory:Memory {
                id: "sample_company_memory",
                company_id: "sample_company",
                context: "Contexto da empresa exemplo",
                description: "Descrição exemplo",
                timestamp: datetime()
            })
            """,
            
            """
            MERGE (ue:UserEntity:Entity {
                id: "sample_entity",
                user_id: "sample_user",
                name: "Entidade Exemplo",
                type: "example",
                description: "Entidade de exemplo"
            })
            """,
            
            # Cria relacionamento
            """
            MATCH (ue:UserEntity {id: "sample_entity"})
            MATCH (um:UserMemory {id: "sample_user_memory"})
            MERGE (ue)-[:EXTRACTED_ENTITY]->(um)
            """
        ]
        
        results = []
        async with memory_service.driver.session() as session:
            for query in schema_queries:
                try:
                    await session.run(query)
                    results.append(f"✓ Executado: {query[:50]}...")
                except Exception as e:
                    results.append(f"✗ Erro: {query[:50]}... | {str(e)}")
        
        return {
            "success": True,
            "message": "Schema Neo4j inicializado",
            "results": results,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao inicializar schema: {str(e)}")


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
