#!/usr/bin/env python3
"""
Script para gerar API Keys para desenvolvimento
"""

import hashlib
import secrets
import os
import sys

def generate_secret_key():
    """Gera uma secret key segura"""
    return secrets.token_urlsafe(32)

def generate_api_key(secret_key):
    """Gera uma API key padrão"""
    return hashlib.sha256(secret_key.encode()).hexdigest()

def generate_admin_api_key(secret_key):
    """Gera uma API key de administrador"""
    return hashlib.sha256(f"admin_{secret_key}".encode()).hexdigest()

def main():
    print("🔐 Gerador de API Keys - NeuroFlow")
    print("=" * 50)
    
    # Verifica se já existe um .env
    env_exists = os.path.exists('.env')
    
    if env_exists:
        print("⚠️  Arquivo .env já existe!")
        response = input("Deseja gerar novas keys? (s/N): ").lower()
        if response not in ['s', 'sim', 'y', 'yes']:
            print("Operação cancelada.")
            return
    
    # Gera secret key
    if not env_exists:
        secret_key = generate_secret_key()
        print(f"✅ Secret Key gerada: {secret_key}")
    else:
        # Lê a secret key existente do .env
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('SECRET_KEY='):
                        secret_key = line.split('=', 1)[1].strip()
                        break
                else:
                    secret_key = generate_secret_key()
                    print(f"✅ Nova Secret Key gerada: {secret_key}")
        except:
            secret_key = generate_secret_key()
            print(f"✅ Nova Secret Key gerada: {secret_key}")
    
    # Gera API keys
    api_key = generate_api_key(secret_key)
    admin_key = generate_admin_api_key(secret_key)
    
    print("\n📋 Suas API Keys:")
    print("-" * 30)
    print(f"🔑 API Key Normal:")
    print(f"   {api_key}")
    print(f"\n🛡️  API Key Admin:")
    print(f"   {admin_key}")
    
    print("\n💡 Como usar:")
    print("1. Copie a API Key Normal para requests de chat")
    print("2. Use a API Key Admin para endpoints administrativos")
    print("3. Inclua no header: Authorization: Bearer <sua-api-key>")
    
    print("\n📄 Exemplo de uso:")
    print(f"curl -H 'Authorization: Bearer {api_key}' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"question\":\"Olá\",\"session_id\":\"test\",\"user_id\":\"user1\",\"company_id\":\"comp1\"}' \\")
    print("     http://localhost:8000/api/v1/chat")
    
    # Oferece para salvar no .env
    if not env_exists:
        save_env = input("\n💾 Deseja criar arquivo .env com essas configurações? (S/n): ").lower()
        if save_env not in ['n', 'no', 'nao', 'não']:
            create_env_file(secret_key)
            print("✅ Arquivo .env criado!")
    else:
        print(f"\n📝 Para atualizar, edite o arquivo .env:")
        print(f"   SECRET_KEY={secret_key}")

def create_env_file(secret_key):
    """Cria um arquivo .env básico"""
    env_content = f"""# Configurações da aplicação
APP_NAME=NeuroFlow
APP_VERSION=0.1.0
DEBUG=true
LOG_LEVEL=INFO

# Configurações do servidor
HOST=0.0.0.0
PORT=8000

# Configurações de autenticação
SECRET_KEY={secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Configurações do PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_memory_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-password

# Configurações do Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Configurações do Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-this-password

# Configurações do Flowise
FLOWISE_API_URL=http://localhost:3000
FLOWISE_API_KEY=your-flowise-api-key
FLOWISE_CHATFLOW_ID=your-chatflow-id-here

# Configurações do Graphiti
GRAPHITI_LLM_MODEL=gpt-4
GRAPHITI_EMBEDDING_MODEL=text-embedding-ada-002
OPENAI_API_KEY=your-openai-api-key

# Configurações do Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Configurações de produção (opcional)
DOMAIN=localhost
ACME_EMAIL=admin@example.com
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)

if __name__ == "__main__":
    main()
