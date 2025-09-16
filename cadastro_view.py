from flask import jsonify, request
from main import app, con, senha_secreta
import re
from flask_bcrypt import generate_password_hash
import jwt

# Validar senha
def validar_senha(senha):
    if len(senha) < 8:
        return "A senha deve ter pelo menos 8 caracteres."

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "A senha deve conter pelo menos um símbolo especial (!@#$%^&*...)."

    if not re.search(r"[A-Z]", senha):
        return "A senha deve conter pelo menos uma letra maiúscula."

    if not re.search(r"[0-9]", senha):
        return "A senha deve conter pelo menos um número."

    return True

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

@app.route('/cadastro', methods=['POST'])
def cadastro_post():
    # Obtém o token
    token = request.headers.get('Authorization')

    # Retorna caso não tenha token
    if not token:
        return jsonify({'error': 'Token de autenticação necessário'}), 401

    try:
        cursor = con.cursor()

        # Remove o bearer
        token = remover_bearer(token)

        # Valida o token
        token_valido, payload = validar_token(token)

        # Retorna caso token inválido
        if not token_valido:
            return jsonify({
                'error': payload
            }), 401

        # Obtém o id_usuario
        id_usuario = payload['id_usuario']

        # Obtém o tipo do usuário
        cursor.execute('''
            SELECT TIPO_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        ''', (id_usuario,))

        tipo_usuario = cursor.fetchone()[0]

        # Usuário não for ADM, retorna
        if str(tipo_usuario) != '1':
            return jsonify({
                'error': 'Usuário não autorizado.'
            }), 401

        # Obtém os dados
        data = request.get_json()

        nome = data.get('nome')
        email = data.get('email')
        cpf = data.get('cpf')
        coren_crm_sus = data.get('coren_crm_sus')
        telefone = data.get('telefone')
        sexo = data.get('sexo')
        nascimento = data.get('nascimento')
        tipo_usuario = data.get('tipo_usuario')

        # Retorna caso dados incompletos
        if not nome or not email or not cpf or not coren_crm_sus or not telefone or not sexo or not nascimento or not tipo_usuario:
            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

        # Verifica se os dados já estão cadastrados
        cursor.execute('''
            SELECT 1 
            FROM USUARIO
            WHERE CPF = ? OR EMAIL = ? OR TELEFONE = ? OR COREN_CRM_SUS = ?
        ''', (cpf, email, telefone, coren_crm_sus))

        # Caso os dados já existam, retorna
        user_exists = cursor.fetchone()

        if user_exists:
            cursor.close()
            return jsonify({
                'error': 'Dados já cadastrados.'
            }), 401

        # Gera a senha criptografada usando o documento como padrão
        senha_hash = generate_password_hash(coren_crm_sus)

        # Cadastro o usuário no banco
        cursor.execute('''
            INSERT INTO USUARIO
            (NOME, EMAIL, CPF, COREN_CRM_SUS, TELEFONE, SEXO, DATA_NASCIMENTO, TIPO_USUARIO, SENHA)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, email, cpf, coren_crm_sus, telefone, sexo, nascimento, tipo_usuario, senha_hash))

        # Salva as mudanças
        con.commit()

        # Retorna sucesso
        return jsonify({
            'success': 'Usuário cadastrado com sucesso!'
        }), 200

    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()

