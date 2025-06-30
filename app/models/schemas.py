from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatRequest(BaseModel):
    """Schema padronizado para requests de chat"""
    question: str = Field(..., description="Pergunta do usuário")
    session_id: str = Field(..., description="ID da sessão")
    user_id: str = Field(..., description="ID do usuário")
    company_id: str = Field(..., description="ID da empresa")
    additional_context: Optional[Dict[str, Any]] = Field(default=None, description="Contexto adicional")
    chatflow_id: Optional[str] = Field(default=None, description="ID do chatflow específico (opcional)")


class ChatResponse(BaseModel):
    """Schema padronizado para responses de chat"""
    text: str = Field(..., description="Resposta do agente")
    execution_id: str = Field(..., description="ID da execução")
    session_id: str = Field(..., description="ID da sessão")
    user_id: str = Field(..., description="ID do usuário")
    company_id: str = Field(..., description="ID da empresa")
    timestamp: datetime = Field(..., description="Timestamp da resposta")
    memory_updated: bool = Field(default=False, description="Se a memória foi atualizada")


class MemoryContext(BaseModel):
    """Contexto de memória a ser enviado para o Flowise"""
    user_context: Optional[str] = Field(default=None, description="Contexto do usuário")
    session_context: Optional[str] = Field(default=None, description="Contexto da sessão")
    company_context: Optional[str] = Field(default=None, description="Contexto da empresa")


class UserMemory(BaseModel):
    """Schema para memória do usuário"""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    interests: Optional[list[str]] = None
    created_at: datetime
    updated_at: datetime


class CompanyMemory(BaseModel):
    """Schema para memória da empresa"""
    company_id: str
    name: str
    context: str
    created_at: datetime
    updated_at: datetime


class SessionMemory(BaseModel):
    """Schema para memória da sessão"""
    session_id: str
    user_id: str
    company_id: str
    context: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FlowiseRequest(BaseModel):
    """Schema para requests para o Flowise"""
    question: str
    overrideConfig: Dict[str, Any]


class FlowiseResponse(BaseModel):
    """Schema para responses do Flowise"""
    text: str
    question: str
    chatId: str
    chatMessageId: str
    executionId: str
    agentFlowExecutedData: Optional[list] = None
