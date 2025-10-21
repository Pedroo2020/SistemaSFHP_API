from datetime import datetime
from flask import request, jsonify
from main import app, con
from components.utils import validar_token, remover_bearer

@app.route('/start_diagnostico', methods=['POST'])
def start_diagnostico():
    # Obtém o token
    token = request.headers.get('Authorization')

    # Retorna caso não tenha token
    if not token:
        return jsonify({'error': 'Token de autenticação necessário'}), 401

    try:
        # Abre o cursor
        cursor = con.cursor()

        # Remove o bearer
        token = remover_bearer(token)

        # Valida o token
        token_valido, payload = validar_token(token)

        # Retorna caso token inválido
        if not token_valido:
            return jsonify({
                'error': payload
            }), 400

        # Obtém o id do usuário
        id_usuario = payload['id_usuario']

        # Obtém o tipo de usuário
        cursor.execute('''
            SELECT TIPO_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ? AND ATIVO = 1
        ''', (id_usuario,))

        result = cursor.fetchone()

        # Usuário não encontrado
        if not result:
            return jsonify({
                'error': 'Usuário não encontrado ou inativo.',
                'logout': True
            }), 404

        # Obtém o tipo do usuário
        tipo_usuario = int(result[0])

        # Se o usuário não for ADM
        if tipo_usuario != 1:
            # Se o usuário não for médico, retorna
            if tipo_usuario != 2:
                return jsonify({
                    'error': 'Usuário não autorizado.'
                }), 401

        # Obtém os dados
        data = request.get_json()

        # Obtém o CPF
        cpf = data.get('cpf')

        # Caso não tenha cpf, retorna
        if not cpf:
            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

        cursor.execute('''
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE CPF = ? AND ATIVO = 1
        ''', (cpf,))

        user_exist = cursor.fetchone()

        # Retorna caso usuário não exista
        if not user_exist:
            return jsonify({
                'error': 'Paciente não encontrado ou inativo.'
            }), 404

        # Id do paciente
        id_paciente = user_exist[0]

        # Seleciona uma consulta existente
        cursor.execute('''
            SELECT ID_CONSULTA
            FROM CONSULTA
            WHERE ID_USUARIO = ? AND SITUACAO = 3
        ''', (id_paciente,))

        consulta_exist = cursor.fetchone()

        # Retorna caso nenhuma consulta seja encontrada
        if not consulta_exist:
            return jsonify({
                'error': 'Nenhuma consulta encontrada.'
            }), 404

        id_consulta = consulta_exist[0]

        data_atual = datetime.now()

        cursor.execute('''
            UPDATE CONSULTA
            SET SITUACAO = 4, DATA_INICIO_DIAGNOSTICO = ?
            WHERE ID_CONSULTA = ?
        ''', (data_atual, id_consulta))

        con.commit()

        return jsonify({
            'success': 'Diagnóstico iniciado com sucesso!'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()

@app.route('/diagnostico', methods=['POST'])
def update_diagnostico():
    # Obtém o token
    token = request.headers.get('Authorization')

    # Retorna caso não tenha token
    if not token:
        return jsonify({'error': 'Token de autenticação necessário'}), 401

    try:
        # Abre o cursor
        cursor = con.cursor()

        # Remove o bearer
        token = remover_bearer(token)

        # Valida o token
        token_valido, payload = validar_token(token)

        # Retorna caso token inválido
        if not token_valido:
            return jsonify({
                'error': payload
            }), 400

        # Obtém o id do usuário
        id_usuario = payload['id_usuario']

        # Obtém o tipo de usuário
        cursor.execute('''
            SELECT TIPO_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ? AND ATIVO = 1
        ''', (id_usuario,))

        result = cursor.fetchone()

        # Usuário não encontrado
        if not result:
            return jsonify({
                'error': 'Usuário não encontrado ou inativo.',
                'logout': True
            }), 404

        # Obtém o tipo do usuário
        tipo_usuario = int(result[0])

        # Se o usuário não for ADM
        if tipo_usuario != 1:
            # Se o usuário não for médico, retorna
            if tipo_usuario != 2:
                return jsonify({
                    'error': 'Usuário não autorizado.'
                }), 401

        # Obtém os dados
        data = request.get_json()

        # Obtém o dados
        diagnostico = data.get('diagnostico')
        receita = data.get('receita')

        cpf = data.get('cpf')

        # Retorna caso algum dado não tenha sido informado
        if (not diagnostico or not receita or not cpf):

            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

        cursor.execute('''
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE CPF = ? AND ATIVO = 1
        ''', (cpf,))

        user_exist = cursor.fetchone()

        # Retorna caso usuário não exista
        if not user_exist:
            return jsonify({
                'error': 'Paciente não encontrado ou inativo.'
            }), 404

        # Id do paciente
        id_paciente = user_exist[0]

        # Seleciona uma triagem em andamento existente
        cursor.execute('''
            SELECT ID_CONSULTA
            FROM CONSULTA
            WHERE ID_USUARIO = ? AND SITUACAO = 4
        ''', (id_paciente,))

        consulta_exist = cursor.fetchone()

        # Retorna caso nenhuma consulta seja encontrada
        if not consulta_exist:
            return jsonify({
                'error': 'Nenhuma consulta encontrada.'
            }), 404

        id_consulta = consulta_exist[0]

        # Verifica se já possui diagnóstico cadastrado
        cursor.execute('''
            SELECT 1
            FROM DIAGNOSTICO
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        # Caso possua, retorna
        if cursor.fetchone():
            # Atualiza a situação
            cursor.execute('''
                UPDATE CONSULTA
                SET SITUACAO = 5
                WHERE ID_CONSULTA = ?
            ''', (id_consulta,))

            # Salva as alterações
            con.commit()

            return jsonify({
                'error': 'Diagnóstico já cadastrado.'
            }), 401

        # Cria o diagnóstico
        cursor.execute('''
            INSERT INTO DIAGNOSTICO
            (ID_CONSULTA, DIAGNOSTICO, RECEITA, ID_MEDICO)
            VALUES (?, ?, ?, ?)
        ''', (id_consulta, diagnostico, receita, id_usuario))

        # Atualiza a situação
        cursor.execute('''
            UPDATE CONSULTA
            SET SITUACAO = 5
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        # Salva as alterações
        con.commit()

        return jsonify({
            'success': 'Diagnóstico cadastrado com sucesso!'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()