from datetime import datetime
from flask import request, jsonify
from main import app, con
from components.utils import validar_token, remover_bearer, is_empty

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
        enfermagem = data.get('enfermagem')

        cpf = data.get('cpf')

        # Retorna caso algum dado não tenha sido informado
        if (is_empty(diagnostico) or
            is_empty(receita) or
            is_empty(cpf)
        ):

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

        # Seleciona um diagnostico em andamento existente
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
            (ID_CONSULTA, DIAGNOSTICO, RECEITA, RECEITA_ENFERMAGEM, ID_MEDICO)
            VALUES (?, ?, ?, ?, ?)
        ''', (id_consulta, diagnostico, receita, enfermagem, id_usuario))

        # Atualiza a situação
        cursor.execute('''
            UPDATE CONSULTA
            SET SITUACAO = 5
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        # Salva as alterações
        con.commit()

        return jsonify({
            'success': 'Diagnóstico cadastrado com sucesso!',
            'id_consulta': id_consulta
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()


@app.route('/diagnostico', methods=['GET'])
def get_diagnostico():
    # Obtém o token
    token = request.headers.get('Authorization')

    # Retorna caso não tenha token
    if not token:
        return jsonify({'error': 'Token de autenticação necessário'}), 401

    try:
        # Abre o cursor
        cursor = con.cursor()

        # Remove o Bearer
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
        if tipo_usuario not in [1, 2, 3, 4]:
            return jsonify({
                'error': 'Usuário não autorizado.',
                'logout': True
            }), 401

        # Obtém o CPF passado por query string
        cpf = request.args.get('cpf')
        id_consulta = request.args.get('id_consulta')

        if is_empty(cpf) and is_empty(id_consulta):
            return jsonify({'error': 'CPF ou ID da consulta não informados.'}), 400

        if cpf:
            # Busca o ID do paciente
            cursor.execute('''
                SELECT ID_USUARIO
                FROM USUARIO
                WHERE CPF = ? AND ATIVO = 1
            ''', (cpf,))

            user_result = cursor.fetchone()

            if not user_result:
                return jsonify({'error': 'Paciente não encontrado ou inativo.'}), 404

            id_paciente = user_result[0]

            # Busca a consulta mais recente (ou em andamento) do paciente
            cursor.execute('''
                SELECT ID_CONSULTA
                FROM CONSULTA
                WHERE ID_USUARIO = ?
                ORDER BY ID_CONSULTA DESC
            ''', (id_paciente,))

            consulta_result = cursor.fetchone()

            if not consulta_result:
                return jsonify({'error': 'Nenhuma consulta encontrada para este paciente.'}), 404

            id_consulta = consulta_result[0]

        # Busca os dados do diagnóstico
        cursor.execute('''
            SELECT 
                DIAGNOSTICO,
                RECEITA,
                RECEITA_ENFERMAGEM
            FROM DIAGNOSTICO
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        diagnostico = cursor.fetchone()

        if not diagnostico:
            return jsonify({'error': 'Nenhum dado do diagnóstico encontrado.'}), 404

        # Monta o dicionário de retorno
        diagnostico_dict = {
            'diagnostico': diagnostico[0],
            'receita': diagnostico[1],
            'enfermagem': diagnostico[2]
        }

        return jsonify({'diagnostico': diagnostico_dict}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 400

    finally:
        cursor.close()