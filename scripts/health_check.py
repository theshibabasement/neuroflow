#!/usr/bin/env python3
"""
Script para verificar a saúde do AI Memory Service
"""

import httpx
import asyncio
import sys
import json
from datetime import datetime

class HealthChecker:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    async def check_basic_health(self):
        """Verifica endpoint básico de health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                self.results["basic_health"] = {
                    "status": "✅ OK" if response.status_code == 200 else "❌ ERRO",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
        except Exception as e:
            self.results["basic_health"] = {
                "status": "❌ ERRO",
                "error": str(e)
            }
    
    async def check_chat_health(self, api_key=None):
        """Verifica endpoint de chat com dependências"""
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/health",
                    headers=headers
                )
                self.results["chat_health"] = {
                    "status": "✅ OK" if response.status_code == 200 else "❌ ERRO",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
        except Exception as e:
            self.results["chat_health"] = {
                "status": "❌ ERRO",
                "error": str(e)
            }
    
    async def check_api_endpoints(self, api_key=None):
        """Verifica se os endpoints principais estão acessíveis"""
        endpoints = [
            ("/docs", "GET"),
            ("/api/v1/chat", "POST"),
        ]
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        endpoint_results = {}
        
        async with httpx.AsyncClient() as client:
            for endpoint, method in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.base_url}{endpoint}")
                    else:
                        # Para POST, apenas verifica se retorna erro de método não permitido ou validação
                        response = await client.post(
                            f"{self.base_url}{endpoint}",
                            headers=headers,
                            json={}
                        )
                    
                    # Para endpoints protegidos, 401/403 é esperado sem API key
                    if endpoint == "/api/v1/chat" and response.status_code in [401, 403, 422]:
                        status = "✅ OK (Protegido)"
                    elif response.status_code in [200, 422]:  # 422 para validação de dados
                        status = "✅ OK"
                    else:
                        status = "⚠️  AVISO"
                    
                    endpoint_results[endpoint] = {
                        "status": status,
                        "status_code": response.status_code,
                        "method": method
                    }
                    
                except Exception as e:
                    endpoint_results[endpoint] = {
                        "status": "❌ ERRO",
                        "error": str(e),
                        "method": method
                    }
        
        self.results["endpoints"] = endpoint_results
    
    async def check_dependencies(self):
        """Verifica dependências externas"""
        dependencies = {
            "PostgreSQL": "postgresql://localhost:5432",
            "Redis": "redis://localhost:6379",
            "Neo4j": "bolt://localhost:7687"
        }
        
        dep_results = {}
        
        for name, url in dependencies.items():
            try:
                if name == "PostgreSQL":
                    # Verifica se a porta está aberta
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex(("localhost", 5432))
                    sock.close()
                    status = "✅ OK" if result == 0 else "❌ ERRO"
                
                elif name == "Redis":
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex(("localhost", 6379))
                    sock.close()
                    status = "✅ OK" if result == 0 else "❌ ERRO"
                
                elif name == "Neo4j":
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex(("localhost", 7687))
                    sock.close()
                    status = "✅ OK" if result == 0 else "❌ ERRO"
                
                dep_results[name] = {
                    "status": status,
                    "url": url
                }
                
            except Exception as e:
                dep_results[name] = {
                    "status": "❌ ERRO",
                    "error": str(e),
                    "url": url
                }
        
        self.results["dependencies"] = dep_results
    
    def print_results(self):
        """Imprime os resultados do health check"""
        print("🏥 AI Memory Service - Health Check")
        print("=" * 50)
        print(f"⏰ Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 URL Base: {self.base_url}")
        print()
        
        # Health básico
        if "basic_health" in self.results:
            result = self.results["basic_health"]
            print(f"🔍 Health Básico: {result['status']}")
            if "error" in result:
                print(f"   Erro: {result['error']}")
            print()
        
        # Health do chat
        if "chat_health" in self.results:
            result = self.results["chat_health"]
            print(f"💬 Health Chat: {result['status']}")
            if "response" in result:
                response = result["response"]
                if isinstance(response, dict):
                    print(f"   Status: {response.get('status', 'N/A')}")
                    if "services" in response:
                        for service, status in response["services"].items():
                            emoji = "✅" if status == "healthy" else "❌"
                            print(f"   {service.title()}: {emoji} {status}")
            print()
        
        # Endpoints
        if "endpoints" in self.results:
            print("🛣️  Endpoints:")
            for endpoint, result in self.results["endpoints"].items():
                print(f"   {result['method']} {endpoint}: {result['status']}")
                if "error" in result:
                    print(f"      Erro: {result['error']}")
            print()
        
        # Dependências
        if "dependencies" in self.results:
            print("🔗 Dependências:")
            for name, result in self.results["dependencies"].items():
                print(f"   {name}: {result['status']}")
                if "error" in result:
                    print(f"      Erro: {result['error']}")
            print()
    
    def get_overall_status(self):
        """Retorna o status geral do sistema"""
        all_ok = True
        
        for category, results in self.results.items():
            if category == "basic_health" or category == "chat_health":
                if "❌" in results.get("status", ""):
                    all_ok = False
            elif category == "endpoints":
                for endpoint, result in results.items():
                    if "❌" in result.get("status", ""):
                        all_ok = False
            elif category == "dependencies":
                for dep, result in results.items():
                    if "❌" in result.get("status", ""):
                        all_ok = False
        
        return "✅ SISTEMA SAUDÁVEL" if all_ok else "⚠️ SISTEMA COM PROBLEMAS"

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Health Check do AI Memory Service")
    parser.add_argument("--url", default="http://localhost:8000", help="URL base do serviço")
    parser.add_argument("--api-key", help="API Key para endpoints protegidos")
    parser.add_argument("--json", action="store_true", help="Saída em formato JSON")
    parser.add_argument("--no-deps", action="store_true", help="Não verificar dependências")
    
    args = parser.parse_args()
    
    checker = HealthChecker(args.url)
    
    # Executa todos os checks
    await checker.check_basic_health()
    await checker.check_chat_health(args.api_key)
    await checker.check_api_endpoints(args.api_key)
    
    if not args.no_deps:
        await checker.check_dependencies()
    
    if args.json:
        # Saída em JSON
        output = {
            "timestamp": datetime.now().isoformat(),
            "base_url": args.url,
            "overall_status": checker.get_overall_status(),
            "results": checker.results
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Saída formatada
        checker.print_results()
        print(f"📊 Status Geral: {checker.get_overall_status()}")
    
    # Exit code baseado no status
    overall_ok = "✅" in checker.get_overall_status()
    sys.exit(0 if overall_ok else 1)

if __name__ == "__main__":
    asyncio.run(main())
