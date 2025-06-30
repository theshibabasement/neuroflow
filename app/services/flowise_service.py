import httpx
import structlog
from typing import Optional, Dict, Any
from app.config import settings
from app.models.schemas import FlowiseRequest, FlowiseResponse, MemoryContext

logger = structlog.get_logger()


class FlowiseService:
    """Serviço para comunicação com o Flowise"""
    
    def __init__(self):
        self.base_url = settings.flowise_api_url
        self.api_key = settings.flowise_api_key
        self.timeout = 60.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers para requests ao Flowise"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def _build_override_config(
        self,
        session_id: str,
        user_id: str,
        company_id: str,
        memory_context: Optional[MemoryContext] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Constrói a configuração de override para o Flowise"""
        config = {
            "sessionId": session_id,
            "userId": user_id,
            "companyId": company_id
        }
        
        # Adiciona contextos de memória se disponíveis
        if memory_context:
            if memory_context.user_context:
                config["userContext"] = memory_context.user_context
            if memory_context.session_context:
                config["sessionContext"] = memory_context.session_context
            if memory_context.company_context:
                config["companyContext"] = memory_context.company_context
        
        # Adiciona contexto adicional se fornecido
        if additional_context:
            config.update(additional_context)
        
        return config
    
    async def send_prediction(
        self,
        question: str,
        session_id: str,
        user_id: str,
        company_id: str,
        memory_context: Optional[MemoryContext] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        chatflow_id: Optional[str] = None
    ) -> Optional[FlowiseResponse]:
        """Envia uma prediction para o Flowise"""
        
        try:
            override_config = self._build_override_config(
                session_id=session_id,
                user_id=user_id,
                company_id=company_id,
                memory_context=memory_context,
                additional_context=additional_context
            )
            
            flowise_request = FlowiseRequest(
                question=question,
                overrideConfig=override_config
            )
            
            # Determina a URL do endpoint
            if chatflow_id:
                url = f"{self.base_url}/api/v1/prediction/{chatflow_id}"
            else:
                # Usa o chatflow configurado nas variáveis de ambiente
                url = f"{self.base_url}/api/v1/prediction/{settings.flowise_chatflow_id}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Sending prediction to Flowise: {url}")
                
                response = await client.post(
                    url=url,
                    json=flowise_request.model_dump(),
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"Received response from Flowise: {response_data.get('executionId', 'unknown')}")
                    
                    # Filtra apenas os campos necessários da resposta
                    filtered_response = {
                        "text": response_data.get("text", ""),
                        "question": response_data.get("question", question),
                        "chatId": response_data.get("chatId", ""),
                        "chatMessageId": response_data.get("chatMessageId", ""),
                        "executionId": response_data.get("executionId", "")
                        # Omitimos agentFlowExecutedData por ser desnecessário
                    }
                    
                    return FlowiseResponse(**filtered_response)
                else:
                    logger.error(f"Flowise API error: {response.status_code} - {response.text}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Timeout when calling Flowise API")
            return None
        except Exception as e:
            logger.error(f"Error calling Flowise API: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Verifica se o Flowise está funcionando"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/chatflows",
                    headers=self._get_headers()
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Flowise health check failed: {e}")
            return False


# Instância global do serviço
flowise_service = FlowiseService()
