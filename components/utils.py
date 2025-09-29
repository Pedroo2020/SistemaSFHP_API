import jwt
from main import senha_secreta

# Remover bearer
def remover_bearer(token):
    if token.startswith('Bearer '):
        return token[len('Bearer '):]
    else:
        return token

# Validar token
def validar_token(token):
    try:
        payload = jwt.decode(token, senha_secreta, algorithms=['HS256'])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, 'Token expirado.'
    except jwt.InvalidTokenError:
        return False, 'Token inválido.'