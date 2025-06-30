from neo4j import AsyncGraphDatabase
from typing import Optional, Dict, Any, List
import asyncio
import structlog
from datetime import datetime
import uuid
import json
from app.config import settings
from app.services.ai_knowledge_service import ai_knowledge_service

logger = structlog.get_logger()


class MemoryService:
    """Serviço para gerenciar memória usando Neo4j diretamente"""
    
    def __init__(self):
        self.driver = None
        self._initialized = False
    
    async def initialize(self):
        """Inicializa o cliente Neo4j"""
        if self._initialized:
            return
        
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password)
            )
            
            # Testa a conexão
            async with self.driver.session() as session:
                await session.run("RETURN 1")
            
            # Cria índices necessários
            await self._create_indices()
            
            self._initialized = True
            logger.info("Neo4j client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j client: {e}")
            raise
    
    async def _create_indices(self):
        """Cria índices necessários no Neo4j"""
        indices = [
            "CREATE INDEX user_memory_idx IF NOT EXISTS FOR (n:UserMemory) ON (n.user_id)",
            "CREATE INDEX session_memory_idx IF NOT EXISTS FOR (n:SessionMemory) ON (n.session_id)",
            "CREATE INDEX company_memory_idx IF NOT EXISTS FOR (n:CompanyMemory) ON (n.company_id)",
            "CREATE INDEX memory_timestamp_idx IF NOT EXISTS FOR (n:Memory) ON (n.timestamp)",
            "CREATE CONSTRAINT user_memory_unique IF NOT EXISTS FOR (n:UserMemory) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT session_memory_unique IF NOT EXISTS FOR (n:SessionMemory) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT company_memory_unique IF NOT EXISTS FOR (n:CompanyMemory) REQUIRE n.id IS UNIQUE"
        ]
        
        async with self.driver.session() as session:
            for index_query in indices:
                try:
                    await session.run(index_query)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
    
    async def close(self):
        """Fecha a conexão com o Neo4j"""
        if self.driver:
            await self.driver.close()
    
    async def ensure_initialized(self):
        """Garante que o cliente está inicializado"""
        if not self._initialized:
            await self.initialize()
    
    async def add_user_memory(self, user_id: str, question: str, answer: str, context: Optional[Dict[str, Any]] = None):
        """Adiciona memória persistente do usuário com extração de conhecimento por IA"""
        await self.ensure_initialized()
        
        logger.info(f"🧠 Starting memory addition for user {user_id}")
        
        try:
            # 1. Extrai conhecimento usando IA
            knowledge = await ai_knowledge_service.extract_knowledge(
                question=question,
                answer=answer,
                user_id=user_id,
                context=context
            )
            
            # 2. Gera embedding da memória
            embedding = await ai_knowledge_service.generate_memory_embedding(
                question=question,
                answer=answer,
                summary=knowledge.summary
            )
            
            # 3. Salva a memória básica
            memory_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            async with self.driver.session() as session:
                # Salva a conversa original com embedding
                await session.run("""
                    CREATE (m:UserMemory:Memory {
                        id: $memory_id,
                        user_id: $user_id,
                        question: $question,
                        answer: $answer,
                        context: $context,
                        summary: $summary,
                        embedding: $embedding,
                        timestamp: $timestamp
                    })
                """, 
                    memory_id=memory_id,
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    context=json.dumps(context) if context else None,
                    summary=knowledge.summary,
                    embedding=embedding,
                    timestamp=timestamp
                )
                
                # 3. Cria entidades extraídas
                for entity in knowledge.entities:
                    entity_id = f"{user_id}_{entity.name}_{entity.type}".lower().replace(" ", "_")
                    await session.run("""
                        MERGE (e:Entity:UserEntity {
                            id: $entity_id,
                            user_id: $user_id,
                            name: $name,
                            type: $type
                        })
                        ON CREATE SET 
                            e.description = $description,
                            e.attributes = $attributes,
                            e.created_at = $timestamp,
                            e.updated_at = $timestamp
                        ON MATCH SET
                            e.updated_at = $timestamp,
                            e.description = CASE 
                                WHEN e.description <> $description THEN $description 
                                ELSE e.description 
                            END
                        
                        // Conecta entidade à memória
                        WITH e
                        MATCH (m:UserMemory {id: $memory_id})
                        MERGE (m)-[:EXTRACTED_ENTITY]->(e)
                    """,
                        entity_id=entity_id,
                        user_id=user_id,
                        name=entity.name,
                        type=entity.type,
                        description=entity.description,
                        attributes=json.dumps(entity.attributes),
                        timestamp=timestamp,
                        memory_id=memory_id
                    )
                
                # 4. Cria relacionamentos extraídos
                for rel in knowledge.relationships:
                    source_id = f"{user_id}_{rel.source_entity}".lower().replace(" ", "_")
                    target_id = f"{user_id}_{rel.target_entity}".lower().replace(" ", "_")
                    
                    await session.run("""
                        MATCH (source:Entity {user_id: $user_id})
                        WHERE toLower(source.name) CONTAINS toLower($source_entity)
                        MATCH (target:Entity {user_id: $user_id})
                        WHERE toLower(target.name) CONTAINS toLower($target_entity)
                        
                        MERGE (source)-[r:RELATED {
                            type: $rel_type,
                            user_id: $user_id
                        }]->(target)
                        ON CREATE SET
                            r.description = $description,
                            r.strength = $strength,
                            r.created_at = $timestamp,
                            r.updated_at = $timestamp
                        ON MATCH SET
                            r.updated_at = $timestamp,
                            r.strength = ($strength + r.strength) / 2
                    """,
                        user_id=user_id,
                        source_entity=rel.source_entity,
                        target_entity=rel.target_entity,
                        rel_type=rel.relationship_type,
                        description=rel.description,
                        strength=rel.strength,
                        timestamp=timestamp
                    )
            
            logger.info(f"Added user memory with {len(knowledge.entities)} entities and {len(knowledge.relationships)} relationships for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user memory: {e}")
            return False
    
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
    
    async def get_user_context(self, user_id: str, query: str, limit: int = 5) -> Optional[str]:
        """Recupera contexto relevante do usuário usando busca semântica inteligente"""
        await self.ensure_initialized()
        
        try:
            # 1. Gera embedding da query para busca semântica
            query_embedding = await ai_knowledge_service.generate_query_embedding(query)
            
            # 2. Busca por similaridade de embeddings (se disponível)
            vector_memories = []
            if query_embedding:
                vector_query = """
                MATCH (m:UserMemory)
                WHERE m.user_id = $user_id AND m.embedding IS NOT NULL
                RETURN m.question as question, m.answer as answer, 
                       m.summary as summary, m.timestamp as timestamp,
                       m.embedding as embedding,
                       null as entity_name, null as entity_type
                ORDER BY m.timestamp DESC
                LIMIT $limit_extended
                """
                
                async with self.driver.session() as session:
                    result = await session.run(
                        vector_query,
                        user_id=user_id,
                        limit_extended=limit * 3  # Busca mais para ranquear
                    )
                    records = await result.data()
                
                # Calcula similaridades e ranqueia
                for record in records:
                    if record['embedding']:
                        similarity = ai_knowledge_service.calculate_cosine_similarity(
                            query_embedding, record['embedding']
                        )
                        if similarity > 0.7:  # Threshold de similaridade
                            record['similarity_score'] = similarity
                            vector_memories.append(record)
                
                # Ordena por similaridade
                vector_memories.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
                vector_memories = vector_memories[:limit]
            
            # 3. Gera termos de busca semântica usando IA
            search_terms = await ai_knowledge_service.generate_contextual_search(query, "user")
            
            # 4. Busca por entidades relacionadas
            entity_memories = []
            for term in search_terms[:3]:  # Limita a 3 termos principais
                entity_query = """
                MATCH (e:UserEntity)-[:EXTRACTED_ENTITY]-(m:UserMemory)
                WHERE e.user_id = $user_id
                AND (toLower(e.name) CONTAINS toLower($term) 
                     OR toLower(e.description) CONTAINS toLower($term)
                     OR toLower(e.type) CONTAINS toLower($term))
                RETURN DISTINCT m.question as question, m.answer as answer, 
                       m.summary as summary, m.timestamp as timestamp,
                       e.name as entity_name, e.type as entity_type
                ORDER BY m.timestamp DESC
                LIMIT $limit
                """
                
                async with self.driver.session() as session:
                    result = await session.run(
                        entity_query,
                        user_id=user_id,
                        term=term,
                        limit=limit
                    )
                    records = await result.data()
                    entity_memories.extend(records)
            
            # 5. Busca textual tradicional como fallback
            text_query = """
            MATCH (m:UserMemory)
            WHERE m.user_id = $user_id
            AND (toLower(m.question) CONTAINS toLower($search_query) 
                 OR toLower(m.answer) CONTAINS toLower($search_query)
                 OR toLower(m.summary) CONTAINS toLower($search_query))
            RETURN m.question as question, m.answer as answer, 
                   m.summary as summary, m.timestamp as timestamp,
                   null as entity_name, null as entity_type
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    text_query,
                    user_id=user_id,
                    search_query=query,
                    limit=limit
                )
                text_memories = await result.data()
            
            # 6. Combina e deduplica resultados (prioriza busca vetorial)
            all_memories = vector_memories + entity_memories + text_memories
            seen_ids = set()
            unique_memories = []
            
            for memory in all_memories:
                memory_key = f"{memory['timestamp']}_{memory['question'][:50]}"
                if memory_key not in seen_ids:
                    seen_ids.add(memory_key)
                    unique_memories.append(memory)
            
            # Ordena por timestamp e limita
            unique_memories.sort(key=lambda x: x['timestamp'], reverse=True)
            unique_memories = unique_memories[:limit]
            
            if not unique_memories:
                return None
            
            # 7. Sintetiza contexto usando IA
            context = await ai_knowledge_service.synthesize_context(
                memories=unique_memories,
                query=query,
                max_length=800
            )
            
            if context:
                return f"Contexto do usuário:\n{context}"
            
            # Fallback para formato simples
            context_parts = []
            for record in unique_memories:
                if record.get('entity_name'):
                    context_parts.append(f"- [{record['entity_type']}] {record['entity_name']}: Q: {record['question']} A: {record['answer']}")
                else:
                    context_parts.append(f"- Q: {record['question']} A: {record['answer']}")
            
            return "Contexto do usuário:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return None
    
    async def get_session_context(self, session_id: str, query: str, limit: int = 10) -> Optional[str]:
        """Recupera contexto da sessão"""
        await self.ensure_initialized()
        
        try:
            search_query = """
            MATCH (m:SessionMemory)
            WHERE m.session_id = $session_id
            AND (toLower(m.question) CONTAINS toLower($search_query) 
                 OR toLower(m.answer) CONTAINS toLower($search_query))
            RETURN m.question as question, m.answer as answer, m.timestamp as timestamp
            ORDER BY m.timestamp DESC
            LIMIT $limit
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    search_query,
                    session_id=session_id,
                    search_query=query,
                    limit=limit
                )
                
                records = await result.data()
            
            if not records:
                return None
            
            context_parts = []
            for record in records:
                context_parts.append(f"- Q: {record['question']} A: {record['answer']}")
            
            return "Contexto da sessão:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return None
    
    async def get_company_context(self, company_id: str) -> Optional[str]:
        """Recupera contexto da empresa (read-only)"""
        await self.ensure_initialized()
        
        try:
            search_query = """
            MATCH (m:CompanyMemory)
            WHERE m.company_id = $company_id
            RETURN m.context as context, m.description as description, m.timestamp as timestamp
            ORDER BY m.timestamp DESC
            LIMIT 20
            """
            
            async with self.driver.session() as session:
                result = await session.run(
                    search_query,
                    company_id=company_id
                )
                
                records = await result.data()
            
            if not records:
                return None
            
            context_parts = []
            for record in records:
                context_parts.append(f"- {record['context']}")
            
            return "Contexto da empresa:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get company context: {e}")
            return None
    
    async def add_company_context(self, company_id: str, context_text: str, description: str = "Company context"):
        """Adiciona contexto da empresa (uso administrativo)"""
        await self.ensure_initialized()
        
        try:
            memory_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            query = """
            CREATE (m:CompanyMemory:Memory {
                id: $memory_id,
                company_id: $company_id,
                context: $context_text,
                description: $description,
                timestamp: $timestamp
            })
            """
            
            async with self.driver.session() as session:
                await session.run(
                    query,
                    memory_id=memory_id,
                    company_id=company_id,
                    context_text=context_text,
                    description=description,
                    timestamp=timestamp
                )
            
            logger.info(f"Added company context for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add company context: {e}")
            return False
    
    async def clear_session_memory(self, session_id: str):
        """Limpa memória da sessão"""
        await self.ensure_initialized()
        
        try:
            query = """
            MATCH (m:SessionMemory)
            WHERE m.session_id = $session_id
            DELETE m
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, session_id=session_id)
                summary = await result.consume()
                
                logger.info(f"Session memory cleared for session {session_id}, deleted {summary.counters.nodes_deleted} nodes")
                return True
            
        except Exception as e:
            logger.error(f"Failed to clear session memory: {e}")
            return False


# Instância global do serviço
memory_service = MemoryService()
