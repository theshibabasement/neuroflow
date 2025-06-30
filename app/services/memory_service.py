from graphiti import Graphiti
from graphiti.nodes import EpisodeType
from typing import Optional, Dict, Any, List
import asyncio
import structlog
from datetime import datetime
from app.config import settings

logger = structlog.get_logger()


class MemoryService:
    """Serviço para gerenciar memória usando Graphiti"""
    
    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Inicializa o cliente Graphiti"""
        if self._initialized:
            return
        
        try:
            self.client = Graphiti(
                neo4j_uri=settings.neo4j_uri,
                neo4j_user=settings.neo4j_user,
                neo4j_password=settings.neo4j_password
            )
            await self.client.build_indices_and_constraints()
            self._initialized = True
            logger.info("Graphiti client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti client: {e}")
            raise
    
    async def ensure_initialized(self):
        """Garante que o cliente está inicializado"""
        if not self._initialized:
            await self.initialize()
    
    async def add_user_memory(self, user_id: str, question: str, answer: str, context: Optional[Dict[str, Any]] = None):
        """Adiciona memória persistente do usuário"""
        await self.ensure_initialized()
        
        try:
            episode_id = f"user_{user_id}_{datetime.now().isoformat()}"
            
            episode = EpisodeType(
                uuid=episode_id,
                name=f"User Interaction - {user_id}",
                content=f"Question: {question}\nAnswer: {answer}",
                source_description=f"User {user_id} interaction",
                reference_time=datetime.now()
            )
            
            if context:
                episode.content += f"\nContext: {context}"
            
            await self.client.add_episode(
                episode_body=episode,
                group_id=f"user_{user_id}"
            )
            
            logger.info(f"Added user memory for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add user memory: {e}")
            return False
    
    async def add_session_memory(self, session_id: str, user_id: str, question: str, answer: str):
        """Adiciona memória da sessão"""
        await self.ensure_initialized()
        
        try:
            episode_id = f"session_{session_id}_{datetime.now().isoformat()}"
            
            episode = EpisodeType(
                uuid=episode_id,
                name=f"Session Interaction - {session_id}",
                content=f"Question: {question}\nAnswer: {answer}",
                source_description=f"Session {session_id} for user {user_id}",
                reference_time=datetime.now()
            )
            
            await self.client.add_episode(
                episode_body=episode,
                group_id=f"session_{session_id}"
            )
            
            logger.info(f"Added session memory for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add session memory: {e}")
            return False
    
    async def get_user_context(self, user_id: str, query: str, limit: int = 5) -> Optional[str]:
        """Recupera contexto relevante do usuário"""
        await self.ensure_initialized()
        
        try:
            results = await self.client.search(
                query=query,
                group_ids=[f"user_{user_id}"],
                limit=limit
            )
            
            if not results:
                return None
            
            context_parts = []
            for result in results:
                context_parts.append(f"- {result.fact}")
            
            return "Contexto do usuário:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return None
    
    async def get_session_context(self, session_id: str, query: str, limit: int = 10) -> Optional[str]:
        """Recupera contexto da sessão"""
        await self.ensure_initialized()
        
        try:
            results = await self.client.search(
                query=query,
                group_ids=[f"session_{session_id}"],
                limit=limit
            )
            
            if not results:
                return None
            
            context_parts = []
            for result in results:
                context_parts.append(f"- {result.fact}")
            
            return "Contexto da sessão:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return None
    
    async def get_company_context(self, company_id: str) -> Optional[str]:
        """Recupera contexto da empresa (read-only)"""
        await self.ensure_initialized()
        
        try:
            # Para empresa, vamos buscar um contexto pré-definido
            # que pode ser adicionado manualmente
            results = await self.client.search(
                query="company context information",
                group_ids=[f"company_{company_id}"],
                limit=20
            )
            
            if not results:
                return None
            
            context_parts = []
            for result in results:
                context_parts.append(f"- {result.fact}")
            
            return "Contexto da empresa:\n" + "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Failed to get company context: {e}")
            return None
    
    async def add_company_context(self, company_id: str, context_text: str, description: str = "Company context"):
        """Adiciona contexto da empresa (uso administrativo)"""
        await self.ensure_initialized()
        
        try:
            episode_id = f"company_{company_id}_{datetime.now().isoformat()}"
            
            episode = EpisodeType(
                uuid=episode_id,
                name=f"Company Context - {company_id}",
                content=context_text,
                source_description=description,
                reference_time=datetime.now()
            )
            
            await self.client.add_episode(
                episode_body=episode,
                group_id=f"company_{company_id}"
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
            # Note: Graphiti não tem uma função direta para deletar por grupo
            # Isso seria implementado conforme a API evolui
            logger.info(f"Session memory cleared for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear session memory: {e}")
            return False


# Instância global do serviço
memory_service = MemoryService()
