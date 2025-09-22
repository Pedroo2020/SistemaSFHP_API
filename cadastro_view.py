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

def validar_cpf(cpf: str) -> bool:
    if not isinstance(cpf, str):
        return False

    # Remove tudo que não for dígito
    num = re.sub(r'\D', '', cpf)

    # Deve ter 11 dígitos
    if len(num) != 11:
        return False

    # Não pode ser sequência de mesmo dígito (ex: '00000000000', '11111111111', ...)
    if num == num[0] * 11:
        return False

    # Calcula o primeiro dígito verificador
    def calc_dig(slice_digits, multipliers):
        s = sum(int(d) * m for d, m in zip(slice_digits, multipliers))
        r = s % 11
        return '0' if r < 2 else str(11 - r)

    # primeiros 9 dígitos
    d1 = calc_dig(num[:9], range(10, 1, -1))
    # primeiros 9 + d1 -> primeiros 10 para calcular d2
    d2 = calc_dig(num[:9] + d1, range(11, 1, -1))

    return num[-2:] == (d1 + d2)

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

        tipo_usuario_token = cursor.fetchone()[0]

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

        # Usuário não for ADM, retorna
        if tipo_usuario_token != 1:

            if tipo_usuario_token != 4:
                return jsonify({
                    'error': 'Usuário não autorizado.'
                }), 401

            elif tipo_usuario != 5:
                return jsonify({
                    'error': 'Cadastro de tipo de usuário não autorizado.'
                }), 401

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
            (NOME, EMAIL, CPF, COREN_CRM_SUS, TELEFONE, SEXO, DATA_NASCIMENTO, TIPO_USUARIO, SENHA, TENTATIVA_ERRO, ATIVO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
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

@app.route('/cadastro', methods=['GET'])
def get_cadastro():
    # Obtém o token
    token = request.headers.get('Authorization')

    # Obtém o CPF do usuário
    cpf_param = request.args.get('cpf')

    # Retorna caso não tenha token
    if not token and not cpf_param:
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

        # Caso tenha passado o parâmetro cpf
        if cpf_param:

            cpf_valido = validar_cpf(cpf_param)

            if not cpf_valido:
                return jsonify({
                    'error': 'CPF inválido.'
                }), 401

            # Verifica o tipo do usuário
            cursor.execute('''
                SELECT TIPO_USUARIO
                FROM USUARIO
                WHERE ID_USUARIO = ?
            ''', (id_usuario,))

            tipo_user_token = cursor.fetchone()[0]

            # Caso não seja funcionário, retorna
            if tipo_user_token not in [1, 2, 3, 4]:
                return jsonify({
                    'error': 'Busca não autorizada.'
                }), 405

            # Obtém os dados do CPF
            cursor.execute('''
                SELECT NOME, EMAIL, CPF, TELEFONE, DATA_NASCIMENTO, SEXO, TIPO_USUARIO, COREN_CRM_SUS
                FROM USUARIO
                WHERE cpf = ?
            ''', (cpf_param,))

        else:

            # Obtém pelo id do usuário
            cursor.execute('''
                SELECT NOME, EMAIL, CPF, TELEFONE, DATA_NASCIMENTO, SEXO, TIPO_USUARIO, COREN_CRM_SUS
                FROM USUARIO
                WHERE ID_USUARIO = ?
            ''', (id_usuario,))

        data = cursor.fetchone()

        if not data:
            return jsonify({
                'error': 'Usuário não encontrado.',
                'userNotFound': True
            }), 404

        nome = data[0]
        email = data[1]
        cpf = data[2]
        telefone = data[3]
        data_nascimento = data[4]
        sexo = data[5]
        tipo_usuario = data[6]
        coren_crm_sus = data[7]

        return jsonify({
            "user": {
                "nome": nome,
                "email": email,
                "cpf": cpf,
                "telefone": telefone,
                "data_nascimento": data_nascimento,
                "sexo": sexo,
                "tipo_usuario": tipo_usuario,
                "coren_crm_sus": coren_crm_sus
            }
        }), 200
    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()