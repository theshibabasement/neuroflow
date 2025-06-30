from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
import hashlib
import hmac

security = HTTPBearer()


def verify_api_key(token: str) -> bool:
    """
    Verifica se a API key é válida
    """
    # Por simplicidade, usando uma verificação básica
    # Em produção, você verificaria contra o banco de dados
    expected_token = hashlib.sha256(settings.secret_key.encode()).hexdigest()
    return hmac.compare_digest(token, expected_token)


def get_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Extrai e valida a API key do header Authorization
    """
    token = credentials.credentials
    
    if not verify_api_key(token):
        raise HTTPException(
            status_code=401,
            detail="API key inválida",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


def get_admin_api_key(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Extrai e valida a API key de administrador
    """
    token = credentials.credentials
    
    # Para admin, usa uma verificação mais restritiva
    admin_token = hashlib.sha256(f"admin_{settings.secret_key}".encode()).hexdigest()
    
    if not hmac.compare_digest(token, admin_token):
        raise HTTPException(
            status_code=403,
            detail="Acesso de administrador necessário",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token


# Funcções auxiliares para gerar tokens (para desenvolvimento)
def generate_api_key() -> str:
    """Gera uma API key padrão"""
    return hashlib.sha256(settings.secret_key.encode()).hexdigest()


def generate_admin_api_key() -> str:
    """Gera uma API key de administrador"""
    return hashlib.sha256(f"admin_{settings.secret_key}".encode()).hexdigest()
