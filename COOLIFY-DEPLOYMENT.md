# 🚀 Deploy no Coolify - NeuroFlow

Guia para deploy do NeuroFlow usando Coolify.

## 📋 Pré-requisitos

### Serviços Externos Necessários

Como o Neo4j e Traefik são removidos do template do Coolify, você precisa configurar:

1. **Neo4j Database** (uma das opções):
   - Neo4j AuraDB (cloud)
   - Neo4j self-hosted em outro servidor
   - Neo4j em outro projeto Coolify

2. **Reverse Proxy**:
   - Coolify gerencia automaticamente (Traefik interno)

## 🔧 Configuração

### 1. Variáveis de Ambiente Obrigatórias

Configure essas variáveis no Coolify:

```env
# Segurança
SECRET_KEY=seu-secret-key-super-seguro

# Banco de Dados (interno)
POSTGRES_DB=ai_memory_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua-senha-postgres-segura

# Neo4j (externo)
NEO4J_URI=bolt://seu-neo4j-host:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=sua-senha-neo4j

# OpenAI (essencial para IA)
OPENAI_API_KEY=sk-sua-openai-api-key

# Flowise
FLOWISE_API_URL=https://seu-flowise-url.com
FLOWISE_API_KEY=sua-flowise-api-key
FLOWISE_CHATFLOW_ID=seu-chatflow-id-do-flowise

# Opcional
DEBUG=false
PORT=8000
```

### 2. Deploy no Coolify

1. **Crie um novo projeto** no Coolify

2. **Configure o repositório**:
   - Repository: `https://github.com/theshibabasement/neuroflow.git`
   - Branch: `main`
   - Build Pack: `Docker Compose`

3. **Selecione o arquivo compose**:
   - Use: `docker-compose.coolify-template.yml`

4. **Configure as variáveis de ambiente** (listadas acima)

5. **Deploy!** 🚀

## 🤖 Configuração do Flowise

### Como obter o Chatflow ID

O **Chatflow ID** é essencial para o NeuroFlow se comunicar com o Flowise:

#### 1. **No Flowise Dashboard**
1. Acesse seu Flowise: `https://seu-flowise.com`
2. Vá para **"Chatflows"**
3. Selecione ou crie o chatflow que deseja usar
4. O **Chatflow ID** aparece na URL: 
   ```
   https://seu-flowise.com/chatflow/a1b2c3d4-e5f6-7890-abcd-ef1234567890
                                 ↑ Este é o Chatflow ID
   ```

#### 2. **Via API** (alternativo)
```bash
curl -X GET "https://seu-flowise.com/api/v1/chatflows" \
  -H "Authorization: Bearer sua-api-key"
```

#### 3. **Exemplo de configuração**
```env
FLOWISE_API_URL=https://seu-flowise.com
FLOWISE_API_KEY=flowise_abc123def456
FLOWISE_CHATFLOW_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

⚠️ **Importante**: Cada chatflow tem um ID único. Use o ID do chatflow que contém sua lógica de conversação.

## 🗄️ Configuração do Neo4j

### Opção 1: Neo4j AuraDB (Recomendado)

1. Acesse [Neo4j Aura](https://console.neo4j.io/)
2. Crie uma instância gratuita
3. Anote as credenciais:
   ```env
   NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=senha-gerada
   ```

### Opção 2: Neo4j Self-Hosted

Se você tem um servidor separado:

```bash
# Docker simples
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/sua-senha \
  neo4j:5.26
```

### Opção 3: Neo4j no Coolify (Projeto Separado)

1. Crie um **novo projeto** no Coolify para Neo4j
2. Use a imagem: `neo4j:5.26`
3. Configure:
   ```env
   NEO4J_AUTH=neo4j/sua-senha
   ```
4. Exponha as portas 7474 e 7687
5. Use o URL interno no NeuroFlow

## ⚙️ Configurações Avançadas

### Recursos Recomendados

Para o **NeuroFlow**:
- **CPU**: 1-2 cores
- **RAM**: 1-2 GB
- **Storage**: 10 GB

Para o **Worker Celery**:
- **CPU**: 1 core
- **RAM**: 512 MB - 1 GB

### Escalabilidade

Para alto volume, no Coolify você pode:

1. **Escalar workers**:
   - Aumente réplicas do `celery-worker`
   - Configure `--concurrency=4` no comando

2. **Escalar aplicação**:
   - Aumente réplicas do `neuroflow`
   - Configure load balancer

### Monitoramento

O Coolify fornece:
- ✅ Logs centralizados
- ✅ Métricas de recursos
- ✅ Health checks automáticos
- ✅ Alertas de deploy

## 🔍 Troubleshooting

### 1. Erro de Conexão Neo4j

```bash
# Teste a conexão
curl -u neo4j:senha http://seu-neo4j:7474/db/data/
```

**Soluções**:
- Verifique NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- Confirme que Neo4j está acessível
- Teste conectividade de rede

### 2. Tasks Celery Não Executam

**Soluções**:
- Verifique logs do celery-worker
- Confirme conexão Redis
- Reinicie worker: `docker-compose restart celery-worker`

### 3. OpenAI API Errors

**Soluções**:
- Verifique OPENAI_API_KEY
- Confirme créditos na conta OpenAI
- Verifique rate limits

### 4. Logs Úteis

```bash
# Aplicação principal
docker logs neuroflow-neuroflow-1

# Worker Celery
docker logs neuroflow-celery-worker-1

# Base de dados
docker logs neuroflow-postgres-1
```

## 🚦 Health Check

Após o deploy, verifique:

1. **Status da aplicação**:
   ```
   GET https://seu-neuroflow.coolify.io/health
   ```

2. **Health completo**:
   ```
   GET https://seu-neuroflow.coolify.io/api/v1/health
   ```

3. **Documentação**:
   ```
   https://seu-neuroflow.coolify.io/docs
   ```

## 📈 Próximos Passos

Após o deploy bem-sucedido:

1. **Gere API Keys**:
   ```bash
   docker exec -it neuroflow-neuroflow-1 python scripts/generate_keys.py
   ```

2. **Teste o chat**:
   ```bash
   docker exec -it neuroflow-neuroflow-1 python scripts/test_chat.py --api-key SUA_API_KEY
   ```

3. **Configure monitoramento** (opcional)
4. **Configure backup** do PostgreSQL
5. **Configure SSL** (Coolify faz automaticamente)

## 🆘 Suporte

- 📧 **Email**: [limemarketingbr@gmail.com](mailto:limemarketingbr@gmail.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/theshibabasement/neuroflow/issues)
- 📚 **Docs**: [README principal](README.md)

---

*Template otimizado para Coolify - NeuroFlow by João Santos*
