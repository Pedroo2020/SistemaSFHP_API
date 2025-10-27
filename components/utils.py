import jwt
from main import senha_secreta, con

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

# Função para ver se o valor é nulo
def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())

def getTempoMedio():
    try:
        cursor = con.cursor()

        cursor.execute('''
            SELECT
        ''')

        return 'oi'
    except Exception as e:
        return str(e)
    finally:
        cursor.close()