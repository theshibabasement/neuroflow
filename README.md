# 🧠 NeuroFlow

**Microserviço inteligente com memória de grafos para potencializar agentes de IA**

*Desenvolvido por [João Santos](mailto:limemarketingbr@gmail.com)*

## 📋 Visão Geral

Este serviço atua como uma camada intermediária entre seu API Gateway (Gravitee) e o Flowise, adicionando:

- **Memória robusta com grafos de conhecimento** usando Neo4j + IA
- **Extração inteligente de entidades e relacionamentos** via OpenAI
- **Três tipos de memória**: usuário, sessão e empresa
- **Busca semântica avançada** com síntese de contexto
- **Padronização de requests/responses**
- **Sistema de filas com Redis**
- **Autenticação por API Key**
- **Arquitetura pronta para produção**

## 🏗️ Arquitetura

```
Frontend → Gravitee → NeuroFlow → Flowise
                            ↓
                  🧠 IA Knowledge Engine
                       (OpenAI + Neo4j)
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
   git clone https://github.com/theshibabasement/neuroflow.git
   cd neuroflow
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
   OPENAI_API_KEY=your-openai-api-key  # 🔑 ESSENCIAL para IA
   FLOWISE_API_URL=http://your-flowise-url:3000
   FLOWISE_API_KEY=your-flowise-api-key
   FLOWISE_CHATFLOW_ID=your-chatflow-id  # 🔑 ID do seu chatflow
   ```

4. **Execute com Docker Compose:**
   ```bash
   docker-compose up -d
   ```

### 🤖 Como obter o Chatflow ID do Flowise

**O Chatflow ID é obrigatório** para o NeuroFlow funcionar:

1. **Acesse seu Flowise Dashboard**
2. **Vá para "Chatflows"** 
3. **Abra o chatflow** que deseja usar
4. **Copie o ID da URL**:
   ```
   https://seu-flowise.com/chatflow/a1b2c3d4-e5f6-7890-abcd-ef1234567890
                                   ↑ Este é o Chatflow ID
   ```

5. **Configure no .env**:
   ```env
   FLOWISE_CHATFLOW_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
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

#### GET `/api/v1/knowledge-graph/user/{user_id}`

Recupera o grafo de conhecimento do usuário com entidades e relacionamentos extraídos por IA.

**Parâmetros:**
- `user_id`: ID do usuário
- `limit`: Número máximo de entidades/relacionamentos (padrão: 50)

**Response:**
```json
{
  "user_id": "user_789",
  "entities": [
    {
      "name": "João Silva",
      "type": "PERSON",
      "description": "Usuário do sistema",
      "attributes": {"role": "developer"},
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ],
  "relationships": [
    {
      "source": "João Silva",
      "target": "Python",
      "relationship_type": "KNOWS",
      "description": "Tem conhecimento em Python",
      "strength": 0.8
    }
  ],
  "stats": {
    "total_entities": 5,
    "total_relationships": 3
  }
}
```

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

## 🤖 Como a IA Funciona

### Extração Inteligente de Conhecimento

O **NeuroFlow** usa OpenAI GPT-4 para automaticamente extrair e estruturar conhecimento das conversas:

#### 1. **Análise de Conversas**
```
Usuário: "Meu nome é João e trabalho como desenvolvedor Python"
Assistente: "Olá João! Que legal, Python é uma linguagem excelente..."
```

#### 2. **Extração de Entidades**
- 🧑 **PERSON**: "João" (usuário do sistema)
- 💼 **SKILL**: "Python" (linguagem de programação)
- 🏢 **ROLE**: "Desenvolvedor" (profissão)

#### 3. **Criação de Relacionamentos**
- João **WORKS_AS** Desenvolvedor
- João **KNOWS** Python
- Desenvolvedor **USES** Python

#### 4. **Busca Semântica Inteligente**
```
Query: "linguagens que o usuário conhece"
→ Gera embedding vetorial da query
→ Busca por similaridade semântica (cosseno)
→ IA expande: ["Python", "programação", "desenvolvimento", "linguagem"]
→ Busca entidades e relacionamentos relevantes  
→ Sintetiza contexto personalizado
```

#### 5. **Busca Vetorial + Textual**
- 🎯 **Embeddings**: `text-embedding-3-small` para busca semântica
- 🔍 **Similaridade**: Cosseno > 0.7 para relevância
- 📊 **Ranking**: Combina busca vetorial + textual + entidades

### Vantagens da Abordagem IA

✅ **Memória Contextual**: Lembra não apenas o que foi dito, mas o significado  
✅ **Busca Inteligente**: Encontra informações relacionadas mesmo com palavras diferentes  
✅ **Busca Vetorial**: Similaridade semântica com embeddings OpenAI  
✅ **Evolução Contínua**: Relacionamentos se fortalecem com mais interações  
✅ **Síntese Automática**: Combina múltiplas memórias em contexto coerente  
✅ **Ranking Inteligente**: Prioriza resultados mais relevantes semanticamente  

## 🔧 Configuração Avançada

### Configurações de IA

```env
OPENAI_API_KEY=your-openai-api-key  # Obrigatório para extração de conhecimento
GRAPHITI_LLM_MODEL=gpt-4o-mini      # Modelo para extração (mais econômico)
GRAPHITI_EMBEDDING_MODEL=text-embedding-ada-002  # Para embeddings futuras
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

### Com Coolify (Mais Fácil) 🚀

Para deploy no **Coolify**, use o template otimizado:

```bash
# Use o arquivo específico para Coolify
docker-compose -f docker-compose.coolify-template.yml up -d
```

📖 **Guia completo**: [COOLIFY-DEPLOYMENT.md](COOLIFY-DEPLOYMENT.md)

### Com Traefik (Manual)

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
docker-compose logs -f neuroflow

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
   docker-compose logs neuroflow
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
   neuroflow:
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

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Autor

**João Santos**  
📧 Email: [limemarketingbr@gmail.com](mailto:limemarketingbr@gmail.com)  
🌐 GitHub: [@theshibabasement](https://github.com/theshibabasement)

## 🆘 Suporte

Para suporte e dúvidas:

- 🐛 Abra uma [issue no GitHub](https://github.com/theshibabasement/neuroflow/issues)
- 📧 Entre em contato via [email](mailto:limemarketingbr@gmail.com)
- 📚 Consulte a documentação do Graphiti: https://help.getzep.com/graphiti/

---

*NeuroFlow é um projeto open-source desenvolvido com ❤️ por João Santos*
