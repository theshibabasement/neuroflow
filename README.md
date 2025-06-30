# AI Memory Service

Microserviço intermediário entre API Gateway e Flowise com memória robusta usando Graphiti.

## 📋 Visão Geral

Este serviço atua como uma camada intermediária entre seu API Gateway (Gravitee) e o Flowise, adicionando:

- **Memória robusta com grafos** usando Graphiti
- **Três tipos de memória**: usuário, sessão e empresa
- **Padronização de requests/responses**
- **Sistema de filas com Redis**
- **Autenticação por API Key**
- **Arquitetura pronta para produção**

## 🏗️ Arquitetura

```
Frontend → Gravitee → AI Memory Service → Flowise
                            ↓
                      Graphiti (Neo4j)
                            ↓
                    PostgreSQL + Redis
```

### Tipos de Memória

1. **Memória de Usuário** (Persistente)
   - Dados pessoais do usuário (nome, email, preferências)
   - Interesses e contexto pessoal
   - Mantida entre sessões

2. **Memória de Sessão** (Temporária)
   - Contexto específico da conversa atual
   - Zerada a cada nova sessão
   - Auxilia no contexto da janela de conversa

3. **Memória de Empresa** (Read-Only)
   - Contexto corporativo compartilhado
   - Disponível para todos os usuários da empresa
   - Atualizada apenas manualmente

## 🚀 Instalação e Configuração

### Pré-requisitos

- Docker e Docker Compose
- Python 3.11+ (para desenvolvimento local)
- OpenAI API Key (para Graphiti)

### Configuração Rápida com Docker

1. **Clone o repositório:**
   ```bash
   git clone <repository-url>
   cd ai-memory-service
   ```

2. **Configure as variáveis de ambiente:**
   ```bash
   cp .env.example .env
   # Edite o arquivo .env com suas configurações
   ```

3. **Variáveis obrigatórias no .env:**
   ```env
   SECRET_KEY=your-super-secret-key-here
   POSTGRES_PASSWORD=your-postgres-password
   NEO4J_PASSWORD=your-neo4j-password
   OPENAI_API_KEY=your-openai-api-key
   FLOWISE_API_URL=http://your-flowise-url:3000
   FLOWISE_API_KEY=your-flowise-api-key
   ```

4. **Execute com Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### Desenvolvimento Local

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure o banco de dados:**
   ```bash
   alembic upgrade head
   ```

3. **Execute a aplicação:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

4. **Execute o worker Celery (em outro terminal):**
   ```bash
   celery -A app.tasks.celery_app worker --loglevel=info
   ```

## 📚 Documentação da API

### Autenticação

Todas as requests requerem autenticação via Bearer Token no header `Authorization`:

```bash
Authorization: Bearer <sua-api-key>
```

#### Gerando API Keys

```python
from app.core.auth import generate_api_key, generate_admin_api_key

# API Key normal
api_key = generate_api_key()
print(f"API Key: {api_key}")

# API Key de administrador
admin_key = generate_admin_api_key()
print(f"Admin API Key: {admin_key}")
```

### Endpoints Principais

#### POST `/api/v1/chat`

Endpoint principal para chat com integração de memória.

**Request:**
```json
{
  "question": "Qual é o meu nome?",
  "session_id": "sess_123456",
  "user_id": "user_789",
  "company_id": "company_abc",
  "additional_context": {
    "custom_data": "valor"
  }
}
```

**Response:**
```json
{
  "text": "Seu nome é João Silva.",
  "execution_id": "exec_123456",
  "session_id": "sess_123456",
  "user_id": "user_789",
  "company_id": "company_abc",
  "timestamp": "2024-01-01T10:00:00Z",
  "memory_updated": false
}
```

#### GET `/api/v1/memory/user/{user_id}`

Recupera memória do usuário.

**Parâmetros:**
- `user_id`: ID do usuário
- `query`: Texto para busca na memória
- `limit`: Número máximo de resultados (padrão: 10)

#### GET `/api/v1/memory/session/{session_id}`

Recupera memória da sessão.

#### DELETE `/api/v1/memory/session/{session_id}`

Limpa memória da sessão.

### Endpoints Administrativos

#### POST `/api/v1/admin/company/{company_id}/context`

Adiciona contexto da empresa (requer API Key de admin).

**Request:**
```json
{
  "context_text": "Esta empresa atua no setor de tecnologia...",
  "description": "Contexto corporativo"
}
```

#### GET `/api/v1/admin/company/{company_id}/context`

Recupera contexto da empresa.

## 🔧 Configuração Avançada

### Configurações do Graphiti

```env
GRAPHITI_LLM_MODEL=gpt-4
GRAPHITI_EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_API_KEY=your-openai-api-key
```

### Configurações do Celery

```env
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

### Configurações do Traefik (Produção)

```env
DOMAIN=your-domain.com
ACME_EMAIL=admin@your-domain.com
```

## 🐳 Deploy em Produção

### Com Traefik (Recomendado)

1. **Configure seu domínio no .env:**
   ```env
   DOMAIN=api.suaempresa.com
   ACME_EMAIL=admin@suaempresa.com
   ```

2. **Execute:**
   ```bash
   docker-compose up -d
   ```

O Traefik irá automaticamente:
- Configurar HTTPS com Let's Encrypt
- Fazer load balancing
- Fornecer dashboard em `:8080`

### Sem Traefik

Remova o serviço `traefik` do `docker-compose.yml` e exponha diretamente a porta da aplicação.

## 🔍 Monitoramento

### Health Checks

- **Aplicação:** `GET /health`
- **Chat com dependências:** `GET /api/v1/health`

### Logs

Os logs são estruturados em JSON e salvos em `./logs/`:

```bash
# Visualizar logs da aplicação
docker-compose logs -f ai-memory-service

# Visualizar logs do worker
docker-compose logs -f celery-worker
```

### Dashboard do Celery

Para monitorar as tarefas do Celery:

```bash
pip install flower
celery -A app.tasks.celery_app flower
```

Acesse em `http://localhost:5555`

## 🛠️ Desenvolvimento

### Estrutura do Projeto

```
app/
├── api/v1/           # Endpoints da API
├── core/             # Configurações centrais
├── models/           # Schemas e modelos
├── services/         # Lógica de negócio
├── tasks/            # Tarefas assíncronas
└── main.py           # Aplicação principal
```

### Adicionando Novos Endpoints

1. Crie o arquivo em `app/api/v1/`
2. Adicione as rotas no `app/main.py`
3. Implemente a lógica em `app/services/`

### Executando Testes

```bash
pytest
```

### Formatação de Código

```bash
black app/
flake8 app/
```

## 🔧 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com Neo4j:**
   ```bash
   # Verifique se o Neo4j está rodando
   docker-compose logs neo4j
   
   # Acesse o browser em http://localhost:7474
   ```

2. **Graphiti não inicializa:**
   ```bash
   # Verifique sua OpenAI API Key
   echo $OPENAI_API_KEY
   
   # Verifique os logs
   docker-compose logs ai-memory-service
   ```

3. **Tasks do Celery não executam:**
   ```bash
   # Verifique se o Redis está rodando
   docker-compose logs redis
   
   # Verifique o worker
   docker-compose logs celery-worker
   ```

### Reset Completo

```bash
# Para reset completo (CUIDADO: apaga todos os dados)
docker-compose down -v
docker-compose up -d
```

## 📈 Performance

### Otimizações Recomendadas

1. **Para produção com alto volume:**
   - Ajuste o número de workers Celery
   - Configure sharding do Redis
   - Use múltiplas instâncias da aplicação

2. **Configuração de recursos:**
   ```yaml
   # No docker-compose.yml
   ai-memory-service:
     deploy:
       replicas: 3
       resources:
         limits:
           memory: 1G
         reservations:
           memory: 512M
   ```

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature
3. Commit suas mudanças
4. Abra um Pull Request

## 📄 Licença

[Incluir informações da licença]

## 🆘 Suporte

Para suporte e dúvidas:

- Abra uma issue no GitHub
- Entre em contato via [email]
- Consulte a documentação do Graphiti: https://help.getzep.com/graphiti/
