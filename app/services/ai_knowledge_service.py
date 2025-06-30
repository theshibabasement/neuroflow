import openai
import structlog
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from app.config import settings

logger = structlog.get_logger()


class Entity(BaseModel):
    """Entidade extraída do texto"""
    name: str
    type: str  # PERSON, ORGANIZATION, LOCATION, CONCEPT, etc.
    description: str
    attributes: Dict[str, Any] = {}


class Relationship(BaseModel):
    """Relacionamento entre entidades"""
    source_entity: str
    target_entity: str
    relationship_type: str
    description: str
    strength: float = 0.5  # 0.0 a 1.0


class KnowledgeExtraction(BaseModel):
    """Resultado da extração de conhecimento"""
    entities: List[Entity]
    relationships: List[Relationship]
    summary: str
    key_facts: List[str]


class AIKnowledgeService:
    """Serviço de IA para extração de conhecimento e criação de grafos"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Modelo mais econômico para extração
        self.embedding_model = "text-embedding-3-small"  # Modelo de embeddings
    
    async def extract_knowledge(
        self, 
        question: str, 
        answer: str, 
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> KnowledgeExtraction:
        """
        Extrai entidades, relacionamentos e fatos do diálogo
        """
        try:
            # Monta o prompt para extração estruturada
            system_prompt = self._get_extraction_system_prompt()
            user_prompt = self._build_extraction_prompt(question, answer, user_id, context)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse da resposta JSON
            result_json = json.loads(response.choices[0].message.content)
            
            # Converte para objetos Pydantic
            entities = [Entity(**entity) for entity in result_json.get("entities", [])]
            relationships = [Relationship(**rel) for rel in result_json.get("relationships", [])]
            
            extraction = KnowledgeExtraction(
                entities=entities,
                relationships=relationships,
                summary=result_json.get("summary", ""),
                key_facts=result_json.get("key_facts", [])
            )
            
            logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
            return extraction
            
        except Exception as e:
            logger.error(f"Failed to extract knowledge: {e}")
            # Retorna extração vazia em caso de erro
            return KnowledgeExtraction(
                entities=[],
                relationships=[],
                summary=f"Q: {question}\nA: {answer}",
                key_facts=[]
            )
    
    def _get_extraction_system_prompt(self) -> str:
        """Prompt do sistema para extração de conhecimento"""
        return """Você é um especialista em extração de conhecimento e criação de grafos semânticos.

Sua tarefa é analisar conversas entre usuários e assistentes de IA para extrair:
1. Entidades (pessoas, organizações, conceitos, locais, etc.)
2. Relacionamentos entre essas entidades
3. Fatos importantes para memória

DIRETRIZES:
- Foque em informações pessoais do usuário (nome, trabalho, preferências)
- Identifique conceitos e temas importantes da conversa
- Crie relacionamentos que conectem as entidades de forma lógica
- Use tipos de entidade padrão: PERSON, ORGANIZATION, LOCATION, CONCEPT, SKILL, INTEREST, etc.
- Use relacionamentos descritivos: WORKS_AT, LIKES, KNOWS, LOCATED_IN, etc.

FORMATO DE SAÍDA:
Responda APENAS com JSON válido no seguinte formato:

{
  "entities": [
    {
      "name": "Nome da entidade",
      "type": "TIPO_ENTIDADE", 
      "description": "Descrição clara da entidade",
      "attributes": {"key": "value"}
    }
  ],
  "relationships": [
    {
      "source_entity": "Entidade origem",
      "target_entity": "Entidade destino", 
      "relationship_type": "TIPO_RELACIONAMENTO",
      "description": "Descrição do relacionamento",
      "strength": 0.8
    }
  ],
  "summary": "Resumo conciso da conversa",
  "key_facts": ["Fato importante 1", "Fato importante 2"]
}"""

    def _build_extraction_prompt(
        self, 
        question: str, 
        answer: str, 
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Constrói o prompt específico para a conversa"""
        
        context_info = ""
        if context:
            context_info = f"\nContexto adicional: {json.dumps(context, ensure_ascii=False)}"
        
        return f"""CONVERSA PARA ANÁLISE:

Usuário ID: {user_id}
Pergunta: {question}
Resposta: {answer}{context_info}

INSTRUÇÃO:
Extraia entidades, relacionamentos e fatos importantes desta conversa.
Foque especialmente em informações sobre o usuário (nome, trabalho, interesses, etc.).

Responda com JSON válido conforme o formato especificado."""

    async def generate_contextual_search(
        self, 
        query: str, 
        context_type: str = "user"
    ) -> List[str]:
        """
        Gera termos de busca semântica baseados na query
        """
        try:
            system_prompt = f"""Você é um especialista em busca semântica.
            
Para a query fornecida, gere uma lista de termos e conceitos relacionados
que podem estar armazenados em um grafo de conhecimento de memória {context_type}.

Inclua:
- Sinônimos e variações
- Conceitos relacionados  
- Termos técnicos relevantes
- Contextos associados

Responda apenas com JSON: {{"terms": ["termo1", "termo2", ...]}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("terms", [query])
            
        except Exception as e:
            logger.error(f"Failed to generate search terms: {e}")
            return [query]

    async def synthesize_context(
        self, 
        memories: List[Dict[str, Any]], 
        query: str,
        max_length: int = 500
    ) -> str:
        """
        Sintetiza múltiplas memórias em um contexto coerente
        """
        try:
            if not memories:
                return ""
            
            # Prepara as memórias para síntese
            memory_texts = []
            for memory in memories[:10]:  # Limita a 10 memórias
                if 'question' in memory and 'answer' in memory:
                    memory_texts.append(f"Q: {memory['question']}\nA: {memory['answer']}")
                elif 'context' in memory:
                    memory_texts.append(memory['context'])
            
            if not memory_texts:
                return ""
            
            system_prompt = f"""Você é um especialista em síntese de informações.

Sintetize as memórias fornecidas em um contexto coerente e relevante 
para responder à query: "{query}"

DIRETRIZES:
- Priorize informações mais relevantes para a query
- Mantenha o contexto conciso (máximo {max_length} caracteres)
- Organize as informações de forma lógica
- Remova redundâncias
- Preserve fatos importantes

Responda apenas com o contexto sintetizado, sem explicações adicionais."""

            memories_text = "\n\n---\n\n".join(memory_texts)
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"MEMÓRIAS:\n{memories_text}"}
                ],
                temperature=0.2,
                max_tokens=max_length // 3  # Aproximadamente
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to synthesize context: {e}")
            # Fallback simples
            if memories:
                return f"Contexto relacionado à query '{query}' encontrado."
            return ""

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Gera embedding vetorial para um texto
        """
        try:
            # Limita o texto para evitar erro de tamanho
            max_length = 8000  # Limite seguro para embeddings
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    async def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """
        Gera embedding para uma query de busca
        """
        return await self.generate_embedding(query)

    async def generate_memory_embedding(self, question: str, answer: str, summary: str = "") -> Optional[List[float]]:
        """
        Gera embedding para uma memória (combina pergunta, resposta e resumo)
        """
        # Combina os textos em um formato estruturado
        memory_text = f"Pergunta: {question}\nResposta: {answer}"
        if summary:
            memory_text += f"\nResumo: {summary}"
        
        return await self.generate_embedding(memory_text)

    def calculate_cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcula similaridade de cosseno entre dois embeddings
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calcula similaridade de cosseno
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0


# Instância global do serviço
ai_knowledge_service = AIKnowledgeService()
