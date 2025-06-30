from fastapi import APIRouter, HTTPException, Depends
from app.services.memory_service import memory_service
from app.core.auth import get_admin_api_key
from app.models.schemas import CompanyMemory
import structlog
from datetime import datetime
from typing import Optional

logger = structlog.get_logger()
router = APIRouter()


@router.post("/company/{company_id}/context")
async def add_company_context(
    company_id: str,
    context_text: str,
    description: Optional[str] = "Company context",
    api_key: str = Depends(get_admin_api_key)
):
    """
    Adiciona contexto da empresa (apenas administradores)
    """
    try:
        success = await memory_service.add_company_context(
            company_id=company_id,
            context_text=context_text,
            description=description
        )
        
        if success:
            return {
                "message": f"Contexto da empresa {company_id} adicionado com sucesso",
                "company_id": company_id,
                "description": description,
                "timestamp": datetime.now()
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao adicionar contexto da empresa")
            
    except Exception as e:
        logger.error(f"Error adding company context: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar contexto da empresa: {str(e)}")


@router.get("/company/{company_id}/context")
async def get_company_context(
    company_id: str,
    api_key: str = Depends(get_admin_api_key)
):
    """
    Recupera contexto da empresa (apenas administradores)
    """
    try:
        context = await memory_service.get_company_context(company_id)
        
        return {
            "company_id": company_id,
            "context": context,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting company context: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recuperar contexto da empresa: {str(e)}")


@router.post("/memory/rebuild-indices")
async def rebuild_memory_indices(
    api_key: str = Depends(get_admin_api_key)
):
    """
    Reconstrói índices da memória (apenas administradores)
    """
    try:
        await memory_service.client.build_indices_and_constraints()
        
        return {
            "message": "Índices da memória reconstruídos com sucesso",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error rebuilding memory indices: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao reconstruir índices: {str(e)}")


@router.get("/stats/memory")
async def get_memory_stats(
    api_key: str = Depends(get_admin_api_key)
):
    """
    Estatísticas da memória (apenas administradores)
    """
    try:
        # Esta implementação depende das funcionalidades específicas do Graphiti
        # Por enquanto, retornamos um placeholder
        return {
            "message": "Estatísticas da memória",
            "note": "Implementação específica depende da API do Graphiti",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")
