#!/usr/bin/env python3
"""
Script para testar o endpoint de chat do AI Memory Service
"""

import httpx
import asyncio
import json
import sys
from datetime import datetime
import uuid

class ChatTester:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.api_key = api_key
        self.session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.company_id = f"test_company_{uuid.uuid4().hex[:8]}"
    
    def get_headers(self):
        """Retorna headers para as requests"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def test_chat_endpoint(self, question="Olá, como você está?"):
        """Testa o endpoint de chat"""
        print(f"🧪 Testando endpoint de chat...")
        print(f"📝 Pergunta: {question}")
        print(f"👤 User ID: {self.user_id}")
        print(f"💬 Session ID: {self.session_id}")
        print(f"🏢 Company ID: {self.company_id}")
        print()
        
        payload = {
            "question": question,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "additional_context": {
                "test_mode": True,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print("📤 Enviando request...")
                
                response = await client.post(
                    f"{self.base_url}/api/v1/chat",
                    headers=self.get_headers(),
                    json=payload
                )
                
                print(f"📥 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Sucesso!")
                    print(f"💬 Resposta: {data.get('text', 'N/A')}")
                    print(f"🔄 Execution ID: {data.get('execution_id', 'N/A')}")
                    print(f"⏰ Timestamp: {data.get('timestamp', 'N/A')}")
                    print(f"🧠 Memória atualizada: {data.get('memory_updated', False)}")
                    return True, data
                else:
                    print("❌ Erro!")
                    try:
                        error_data = response.json()
                        print(f"📋 Detalhes: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
                    except:
                        print(f"📋 Resposta: {response.text}")
                    return False, None
                    
        except Exception as e:
            print(f"❌ Erro na request: {e}")
            return False, None
    
    async def test_memory_endpoints(self):
        """Testa endpoints de memória"""
        print("\n🧠 Testando endpoints de memória...")
        
        # Testa recuperação de memória do usuário
        print("\n1️⃣ Testando memória do usuário...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/memory/user/{self.user_id}",
                    headers=self.get_headers(),
                    params={"query": "test", "limit": 5}
                )
                
                if response.status_code == 200:
                    print("✅ Memória do usuário recuperada com sucesso")
                    data = response.json()
                    context = data.get('context')
                    if context:
                        print(f"📝 Contexto encontrado: {context[:100]}...")
                    else:
                        print("📝 Nenhum contexto encontrado (normal para novos usuários)")
                else:
                    print(f"❌ Erro ao recuperar memória do usuário: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Erro: {e}")
        
        # Testa recuperação de memória da sessão
        print("\n2️⃣ Testando memória da sessão...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/memory/session/{self.session_id}",
                    headers=self.get_headers(),
                    params={"query": "test", "limit": 10}
                )
                
                if response.status_code == 200:
                    print("✅ Memória da sessão recuperada com sucesso")
                    data = response.json()
                    context = data.get('context')
                    if context:
                        print(f"📝 Contexto encontrado: {context[:100]}...")
                    else:
                        print("📝 Nenhum contexto encontrado (normal para novas sessões)")
                else:
                    print(f"❌ Erro ao recuperar memória da sessão: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    async def test_conversation_flow(self):
        """Testa um fluxo de conversa completo"""
        print("\n🔄 Testando fluxo de conversa...")
        
        questions = [
            "Olá! Meu nome é João Silva.",
            "Trabalho como desenvolvedor de software.",
            "Qual é o meu nome?",
            "Em que eu trabalho?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n{i}️⃣ Pergunta {i}: {question}")
            success, response = await test_chat_endpoint(question)
            
            if success:
                print(f"✅ Resposta: {response.get('text', 'N/A')[:100]}...")
                await asyncio.sleep(1)  # Pausa entre perguntas
            else:
                print("❌ Falha na pergunta, interrompendo teste")
                break
    
    async def cleanup_session(self):
        """Limpa a sessão de teste"""
        print(f"\n🧹 Limpando sessão de teste {self.session_id}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/api/v1/memory/session/{self.session_id}",
                    headers=self.get_headers()
                )
                
                if response.status_code == 200:
                    print("✅ Sessão limpa com sucesso")
                else:
                    print(f"⚠️ Aviso: Não foi possível limpar a sessão ({response.status_code})")
                    
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao limpar sessão: {e}")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Teste do endpoint de chat")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base do serviço")
    parser.add_argument("--api-key", required=True, help="API Key para autenticação")
    parser.add_argument("--question", default="Olá, como você está?", help="Pergunta para teste")
    parser.add_argument("--full-test", action="store_true", help="Executa teste completo")
    parser.add_argument("--no-cleanup", action="store_true", help="Não limpa a sessão ao final")
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("❌ Erro: API Key é obrigatória")
        print("💡 Dica: Execute scripts/generate_keys.py para gerar uma API Key")
        sys.exit(1)
    
    tester = ChatTester(args.url, args.api_key)
    
    print("🚀 NeuroFlow - Teste de Chat")
    print("=" * 50)
    print(f"🌐 URL: {args.url}")
    print(f"🔑 API Key: {args.api_key[:20]}...")
    print()
    
    try:
        if args.full_test:
            # Teste completo
            print("🔄 Executando teste completo...")
            
            # Teste básico
            success, _ = await tester.test_chat_endpoint(args.question)
            
            if success:
                # Testa endpoints de memória
                await tester.test_memory_endpoints()
                
                # Testa fluxo de conversa
                await tester.test_conversation_flow()
            
        else:
            # Teste simples
            success, _ = await tester.test_chat_endpoint(args.question)
        
        # Cleanup
        if not args.no_cleanup:
            await tester.cleanup_session()
        
        print("\n" + "=" * 50)
        if success:
            print("✅ Teste concluído com sucesso!")
        else:
            print("❌ Teste falhou!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
        if not args.no_cleanup:
            await tester.cleanup_session()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
