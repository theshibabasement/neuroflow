# 🤝 Contribuindo para o NeuroFlow

Obrigado por seu interesse em contribuir para o NeuroFlow! Este documento fornece diretrizes para contribuições.

## 📋 Como Contribuir

### 1. 🍴 Fork do Repositório

1. Faça um fork do repositório
2. Clone seu fork localmente:
   ```bash
   git clone https://github.com/theshibabasement/neuroflow.git
   cd neuroflow
   ```

### 2. 🌿 Crie uma Branch

Crie uma branch para sua feature ou correção:

```bash
git checkout -b feature/nome-da-sua-feature
# ou
git checkout -b fix/nome-do-bug-corrigido
```

### 3. 🛠️ Desenvolva

1. **Configure o ambiente de desenvolvimento:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate  # Windows
   
   pip install -r requirements.txt
   ```

2. **Execute os testes:**
   ```bash
   pytest
   ```

3. **Formate o código:**
   ```bash
   black app/
   flake8 app/
   ```

### 4. 📝 Commit suas Mudanças

Use mensagens de commit claras e descritivas:

```bash
git commit -m "feat: adiciona nova funcionalidade X"
git commit -m "fix: corrige bug na validação Y"
git commit -m "docs: atualiza documentação do endpoint Z"
```

**Convenções de commit:**
- `feat:` para novas funcionalidades
- `fix:` para correção de bugs
- `docs:` para mudanças na documentação
- `style:` para mudanças de formatação
- `refactor:` para refatoração de código
- `test:` para adição/correção de testes

### 5. 📤 Envie um Pull Request

1. Push para sua branch:
   ```bash
   git push origin feature/nome-da-sua-feature
   ```

2. Abra um Pull Request no GitHub
3. Descreva suas mudanças claramente
4. Aguarde o review

## 🎯 Tipos de Contribuições

### 🐛 Reportar Bugs

- Use o template de issue para bugs
- Inclua informações detalhadas sobre o ambiente
- Forneça passos para reproduzir o problema

### ✨ Sugerir Funcionalidades

- Use o template de issue para features
- Explique o caso de uso
- Descreva a solução proposta

### 📚 Melhorar Documentação

- Documentação é sempre bem-vinda!
- Corrija typos, melhore explicações
- Adicione exemplos práticos

### 🧪 Escrever Testes

- Adicione testes para novas funcionalidades
- Melhore a cobertura de testes existentes
- Teste cenários de erro

## 🏗️ Diretrizes de Desenvolvimento

### Estrutura do Código

```
app/
├── api/           # Endpoints da API
├── core/          # Configurações centrais  
├── models/        # Schemas e modelos
├── services/      # Lógica de negócio
└── tasks/         # Tarefas assíncronas
```

### Padrões de Código

1. **Python:**
   - Siga PEP 8
   - Use type hints
   - Docstrings em funções públicas

2. **FastAPI:**
   - Use Pydantic para validação
   - Implemente tratamento de erros
   - Documente endpoints com OpenAPI

3. **Async/Await:**
   - Use async/await consistentemente
   - Gerencie conexões adequadamente

### Testes

- Escreva testes unitários para service classes
- Teste endpoints com TestClient
- Mock dependências externas
- Mantenha cobertura > 80%

## 🔍 Processo de Review

### O que verificamos:

1. **Funcionalidade:**
   - O código faz o que deveria fazer?
   - Está bem testado?

2. **Qualidade:**
   - Segue os padrões de código?
   - É legível e mantível?

3. **Documentação:**
   - Está bem documentado?
   - README atualizado se necessário?

4. **Performance:**
   - Não introduz regressões de performance?
   - Usa recursos eficientemente?

### Critérios de Aprovação:

- ✅ Todos os testes passam
- ✅ Código formatado corretamente
- ✅ Documentação atualizada
- ✅ Review aprovado por um maintainer

## 🎨 Estilo de Código

### Python

```python
# ✅ Bom
async def get_user_memory(user_id: str, query: str) -> Optional[str]:
    """
    Recupera memória do usuário para uma query específica.
    
    Args:
        user_id: ID do usuário
        query: Texto para busca
        
    Returns:
        Contexto encontrado ou None
    """
    try:
        results = await memory_service.search(user_id, query)
        return format_context(results)
    except Exception as e:
        logger.error(f"Error getting user memory: {e}")
        return None

# ❌ Ruim
def getUserMemory(userId, query):
    results = memory_service.search(userId, query)
    return results
```

### Documentação de API

```python
@router.post("/chat", response_model=ChatResponse)
async def chat_prediction(
    request: ChatRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Endpoint principal para chat com integração de memória.
    
    - **question**: Pergunta do usuário
    - **session_id**: ID da sessão
    - **user_id**: ID do usuário
    - **company_id**: ID da empresa
    
    Returns resposta do agente com contexto de memória.
    """
```

## 🐛 Debugging

### Logs Estruturados

```python
import structlog

logger = structlog.get_logger()

# ✅ Bom
logger.info(
    "Processing chat request",
    user_id=user_id,
    session_id=session_id,
    question_length=len(question)
)

# ❌ Ruim
print(f"Processing chat for {user_id}")
```

### Tratamento de Erros

```python
# ✅ Bom
try:
    result = await external_service.call()
    return result
except httpx.TimeoutException:
    logger.error("External service timeout")
    raise HTTPException(status_code=504, detail="Service timeout")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

# ❌ Ruim
try:
    result = await external_service.call()
    return result
except:
    return None
```

## 🤔 Dúvidas?

- 📧 Email: [limemarketingbr@gmail.com](mailto:limemarketingbr@gmail.com)
- 💬 Abra uma [Discussion no GitHub](https://github.com/theshibabasement/neuroflow/discussions)
- 🐛 Para bugs, abra uma [Issue](https://github.com/theshibabasement/neuroflow/issues)

## 📜 Código de Conduta

Este projeto segue um código de conduta baseado no [Contributor Covenant](https://www.contributor-covenant.org/). Seja respeitoso e inclusivo em todas as interações.

---

**Obrigado por contribuir para o NeuroFlow! 🧠✨**

*Desenvolvido com ❤️ por [João Santos](mailto:limemarketingbr@gmail.com)*
