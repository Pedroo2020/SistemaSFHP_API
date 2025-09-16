from flask import request, jsonify
import jwt
from flask_bcrypt import check_password_hash
from main import app, con, senha_secreta

def generate_token(user_id, cpf):
    payload = {'id_usuario': user_id, 'cpf': cpf}
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    return token

@app.route('/login', methods=['POST'])
def login():
    # Obtém os dados
    data = request.get_json()

    cpf = data.get('cpf')
    senha = data.get('senha')

    # Retorna caso dados incompletos
    if not cpf or not senha:
        return jsonify({
            'error': 'Dados incompletos.'
        }), 401

    try:
        # Abre o cursor
        cursor = con.cursor()

        # Obtém a senha criptografada e o id_usuario
        cursor.execute('''
            SELECT SENHA, ID_USUARIO
            FROM USUARIO
            WHERE CPF = ?
        ''', (cpf,))

        # Caso usuário não exista, retorna
        user_exist = cursor.fetchone()

        if not user_exist:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        senha_hash = user_exist[0]
        id_usuario = user_exist[1]

        # Verifica se a senha inserida é igual a criptografada
        senha_check = check_password_hash(senha_hash, senha)

        # Caso sejam diferentes, retorna
        if not senha_check:
            return jsonify({
                'error': 'Senha incorreta.'
            }), 401

        # Gera o token
        token = generate_token(id_usuario, cpf)

        # Retorna sucesso e o token
        return jsonify({
            'success': 'Login realizado com sucesso!',
            'token': token
        }), 200
    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        # Fecha o cursor ao final
        cursor.close()