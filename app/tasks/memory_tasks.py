from celery import shared_task
from app.services.memory_service import memory_service
import structlog
import asyncio

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=3)
def update_memory_task(self, user_id: str, session_id: str, company_id: str, question: str, answer: str):
    """
    Task assíncrona para atualizar a memória após uma conversa
    """
    try:
        logger.info(f"Starting memory update for user {user_id}, session {session_id}")
        
        # Executa as operações de memória de forma assíncrona
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Garante que o serviço de memória está inicializado
            loop.run_until_complete(memory_service.ensure_initialized())
            
            # Adiciona memória do usuário (persistente)
            user_memory_success = loop.run_until_complete(
                memory_service.add_user_memory(
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    context={"company_id": company_id, "session_id": session_id}
                )
            )
            
            # Adiciona memória da sessão
            session_memory_success = loop.run_until_complete(
                memory_service.add_session_memory(
                    session_id=session_id,
                    user_id=user_id,
                    question=question,
                    answer=answer
                )
            )
            
            if user_memory_success and session_memory_success:
                logger.info(f"Memory updated successfully for user {user_id}, session {session_id}")
                return {"status": "success", "user_id": user_id, "session_id": session_id}
            else:
                raise Exception("Failed to update one or more memory types")
                
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Memory update failed: {exc}")
        
        # Retry lógico
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying memory update task (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        else:
            logger.error(f"Memory update failed permanently for user {user_id}, session {session_id}")
            return {"status": "failed", "error": str(exc), "user_id": user_id, "session_id": session_id}


@shared_task
def cleanup_old_sessions():
    """
    Task para limpeza de sessões antigas (executada periodicamente)
    """
    try:
        logger.info("Starting cleanup of old sessions")
        
        # Implementação da limpeza seria feita aqui
        # Por exemplo, remover sessões inativas há mais de X dias
        
        # Por enquanto, apenas log
        logger.info("Session cleanup completed")
        return {"status": "success", "message": "Session cleanup completed"}
        
    except Exception as exc:
        logger.error(f"Session cleanup failed: {exc}")
        return {"status": "failed", "error": str(exc)}


def update_memory_sync(user_id: str, session_id: str, company_id: str, question: str, answer: str):
    """
    Versão síncrona da atualização de memória (para uso em background tasks do FastAPI)
    """
    try:
        # Executa a task do Celery de forma assíncrona
        result = update_memory_task.delay(user_id, session_id, company_id, question, answer)
        logger.info(f"Memory update task queued with ID: {result.id}")
        return result.id
    except Exception as e:
        logger.error(f"Failed to queue memory update task: {e}")
        return None
