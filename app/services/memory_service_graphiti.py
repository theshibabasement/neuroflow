import asyncio
import structlog
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from neo4j import AsyncGraphDatabase
from app.config import settings
from app.services.ai_knowledge_service import ai_knowledge_service

logger = structlog.get_logger()


class MemoryServiceGraphiti:
    """Serviço de memória usando abordagem Graphiti para estruturação de grafos"""
    
    def __init__(self):
        self.driver = None
        self._initialized = False
    
    async def ensure_initialized(self):
        """Garante que o driver está inicializado"""
        if not self._initialized:
            await self.initialize()
    
    async def initialize(self):
        """Inicializa conexão com Neo4j"""
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # Testa conexão
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            
            self._initialized = True
            logger.info(f"Neo4j connection initialized: {settings.neo4j_uri}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {e}")
            raise
    
    async def close(self):
        """Fecha conexão com Neo4j"""
        if self.driver:
            await self.driver.close()
            self._initialized = False
    
    async def add_user_memory(self, user_id: str, question: str, answer: str, context: Optional[Dict[str, Any]] = None):
        """Adiciona memória do usuário com extração inteligente de conhecimento usando abordagem Graphiti"""
        await self.ensure_initialized()
        
        try:
            current_date = datetime.now().isoformat()
            
            # 1. Gera queries Cypher estruturadas usando abordagem Graphiti
            cypher_queries = await ai_knowledge_service.generate_cypher_for_interaction(
                question=question,
                answer=answer,
                user_id=user_id,
                current_date=current_date
            )
            
            if not cypher_queries:
                logger.info(f"No structured knowledge extracted for user {user_id}")
                # Fallback: salva como memória básica
                return await self._add_basic_memory(user_id, question, answer)
            
            # 2. Executa as queries Cypher geradas
            async with self.driver.session() as session:
                for query in cypher_queries:
                    try:
                        await session.run(query)
                        logger.debug(f"Executed query: {query[:100]}...")
                    except Exception as e:
                        logger.error(f"Failed to execute query '{query[:100]}...': {e}")
                        continue
            
            # 3. Adiciona memória básica para recuperação
            await self._add_basic_memory(user_id, question, answer)
            
            logger.info(f"Added structured user memory with {len(cypher_queries)} queries for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user memory: {e}")
            return False
    
    async def _add_basic_memory(self, user_id: str, question: str, answer: str):
        """Adiciona memória básica para recuperação"""
        try:
            # Gera embedding da pergunta para busca semântica
            embedding = await ai_knowledge_service.generate_query_embedding(question)
            
            memory_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            async with self.driver.session() as session:
                await session.run("""
                    CREATE (m:UserMemory:Memory {
                        id: $memory_id,
                        user_id: $user_id,
                        question: $question,
                        answer: $answer,
                        timestamp: $timestamp,
                        embedding: $embedding
                    })
                """,
                    memory_id=memory_id,
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    timestamp=timestamp,
                    embedding=embedding
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add basic memory: {e}")
            return False
    
    async def get_user_context(self, user_id: str, query: str, limit: int = 5) -> Optional[str]:
        """Recupera contexto relevante do usuário usando busca no grafo estruturado"""
        await self.ensure_initialized()
        
        try:
            # 1. Tenta gerar uma query Cypher específica para a pergunta
            cypher_query = await ai_knowledge_service.generate_query_cypher(query, user_id)
            
            context_parts = []
            
            if cypher_query:
                # Executa a query específica gerada pela IA
                try:
                    async with self.driver.session() as session:
                        result = await session.run(cypher_query)
                        records = []
                        async for record in result:
                            records.append(dict(record))
                        
                        if records:
                            context_parts.append("## Resposta Específica:")
                            for record in records:
                                for key, value in record.items():
                                    if value:
                                        context_parts.append(f"- {key}: {value}")
                            
                except Exception as e:
                    logger.error(f"Failed to execute generated query: {e}")
            
            # 2. Busca entidades relacionadas ao usuário (fallback/complemento)
            async with self.driver.session() as session:
                entity_query = """
                MATCH (p:Person {userID: $user_id})-[*1..2]-(related)
                WHERE toLower(related.name) CONTAINS toLower($search_term)
                   OR toLower(related.description) CONTAINS toLower($search_term)
                   OR toLower(related.type) CONTAINS toLower($search_term)
                RETURN DISTINCT related.name as name, 
                       related.type as type,
                       related.description as description,
                       labels(related) as labels
                LIMIT $limit
                """
                
                result = await session.run(entity_query, 
                    user_id=user_id, 
                    search_term=query, 
                    limit=limit
                )
                
                entities = []
                async for record in result:
                    if record["name"]:
                        entities.append({
                            "name": record["name"],
                            "type": record["type"],
                            "description": record["description"],
                            "labels": record["labels"]
                        })
                
                # 3. Busca memórias básicas como fallback
                memory_query = """
                MATCH (m:UserMemory {user_id: $user_id})
                WHERE toLower(m.question) CONTAINS toLower($search_term)
                   OR toLower(m.answer) CONTAINS toLower($search_term)
                RETURN m.question as question, m.answer as answer, m.timestamp as timestamp
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """
                
                result = await session.run(memory_query,
                    user_id=user_id,
                    search_term=query,
                    limit=limit
                )
                
                memories = []
                async for record in result:
                    memories.append({
                        "question": record["question"],
                        "answer": record["answer"],
                        "timestamp": record["timestamp"]
                    })
                
                # 4. Adiciona entidades relacionadas se encontradas
                if entities and not context_parts:  # Só adiciona se não teve resposta específica
                    context_parts.append("## Entidades Relacionadas:")
                    for entity in entities:
                        context_parts.append(f"- {entity['name']} ({entity['type']}): {entity['description']}")
                
                # 5. Adiciona memórias como contexto adicional
                if memories and len(context_parts) < 2:  # Limita contexto para não ficar muito longo
                    context_parts.append("## Conversas Anteriores:")
                    for memory in memories[:2]:  # Máximo 2 memórias
                        context_parts.append(f"P: {memory['question']}")
                        context_parts.append(f"R: {memory['answer']}")
                        context_parts.append("---")
                
                return "\n".join(context_parts) if context_parts else None
                
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return None
    
    async def query_graph(self, user_id: str, question: str) -> Optional[Dict[str, Any]]:
        """
        Executa uma consulta específica no grafo e retorna resposta estruturada
        """
        await self.ensure_initialized()
        
        try:
            # Gera query Cypher específica
            cypher_query = await ai_knowledge_service.generate_query_cypher(question, user_id)
            
            if not cypher_query:
                return None
            
            async with self.driver.session() as session:
                result = await session.run(cypher_query)
                records = []
                async for record in result:
                    records.append(dict(record))
                
                return {
                    "question": question,
                    "cypher_query": cypher_query,
                    "results": records,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to query graph: {e}")
            return None
    
    async def add_session_memory(self, session_id: str, user_id: str, question: str, answer: str):
        """Adiciona memória da sessão"""
        await self.ensure_initialized()
        
        try:
            memory_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            query = """
            CREATE (m:SessionMemory:Memory {
                id: $memory_id,
                session_id: $session_id,
                user_id: $user_id,
                question: $question,
                answer: $answer,
                timestamp: $timestamp
            })
            """
            
            async with self.driver.session() as session:
                await session.run(
                    query,
                    memory_id=memory_id,
                    session_id=session_id,
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    timestamp=timestamp
                )
            
            logger.info(f"Added session memory for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add session memory: {e}")
            return False
    
    async def get_session_context(self, session_id: str, query: str, limit: int = 5) -> Optional[str]:
        """Recupera contexto da sessão"""
        await self.ensure_initialized()
        
        try:
            async with self.driver.session() as session:
                memory_query = """
                MATCH (m:SessionMemory {session_id: $session_id})
                WHERE toLower(m.question) CONTAINS toLower($search_term)
                   OR toLower(m.answer) CONTAINS toLower($search_term)
                RETURN m.question as question, m.answer as answer, m.timestamp as timestamp
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """
                
                result = await session.run(memory_query,
                    session_id=session_id,
                    search_term=query,
                    limit=limit
                )
                
                memories = []
                async for record in result:
                    memories.append({
                        "question": record["question"],
                        "answer": record["answer"],
                        "timestamp": record["timestamp"]
                    })
                
                if memories:
                    context_parts = ["## Conversas da Sessão:"]
                    for memory in memories:
                        context_parts.append(f"P: {memory['question']}")
                        context_parts.append(f"R: {memory['answer']}")
                        context_parts.append("---")
                    return "\n".join(context_parts)
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return None

    async def add_company_memory(self, company_id: str, context: str, description: str):
        """Adiciona memória da empresa"""
        await self.ensure_initialized()
        
        try:
            memory_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            query = """
            CREATE (m:CompanyMemory:Memory {
                id: $memory_id,
                company_id: $company_id,
                context: $context,
                description: $description,
                timestamp: $timestamp
            })
            """
            
            async with self.driver.session() as session:
                await session.run(
                    query,
                    memory_id=memory_id,
                    company_id=company_id,
                    context=context,
                    description=description,
                    timestamp=timestamp
                )
            
            logger.info(f"Added company memory for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add company memory: {e}")
            return False


# Instância global do serviço
memory_service_graphiti = MemoryServiceGraphiti()
