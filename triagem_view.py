from datetime import datetime
from flask import request, jsonify
from main import app, con
from components.utils import validar_token, remover_bearer

@app.route('/start_triagem', methods=['POST'])
def start_triagem():
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
            WHERE ID_USUARIO = ?
        ''', (id_usuario,))

        result = cursor.fetchone()

        # Usuário não encontrado
        if not result:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        # Obtém o tipo do usuário
        tipo_usuario = int(result[0])

        # Se o usuário não for ADM
        if tipo_usuario != 1:
            # Se o usuário não for paciente, retorna
            if tipo_usuario != 3:
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
            WHERE CPF = ?
        ''', (cpf,))

        user_exist = cursor.fetchone()

        # Retorna caso usuário não exista
        if not user_exist:
            return jsonify({
                'error': 'Paciente não encontrado.'
            }), 404

        # Id do paciente
        id_paciente = user_exist[0]

        # Seleciona uma consulta existente
        cursor.execute('''
            SELECT ID_CONSULTA
            FROM CONSULTA
            WHERE ID_USUARIO = ? AND SITUACAO = 1
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
            SET SITUACAO = 2, DATA_INICIO_TRIAGEM = ?
            WHERE ID_CONSULTA = ?
        ''', (data_atual, id_consulta))

        con.commit()

        return jsonify({
            'success': 'Triagem iniciada com sucesso!'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()

@app.route('/triagem', methods=['POST'])
def update_triagem():
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
            WHERE ID_USUARIO = ?
        ''', (id_usuario,))

        result = cursor.fetchone()

        # Usuário não encontrado
        if not result:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        # Obtém o tipo do usuário
        tipo_usuario = int(result[0])

        # Se o usuário não for ADM
        if tipo_usuario != 1:
            # Se o usuário não for enfermeiro, retorna
            if tipo_usuario != 3:
                return jsonify({
                    'error': 'Usuário não autorizado.'
                }), 401

        # Obtém os dados
        data = request.get_json()

        # Obtém o dados
        queixa = data.get('queixa')
        temperatura = data.get('temperatura')
        pressao = data.get('pressao')
        frequencia_cardiaca = data.get('frequencia_cardiaca')
        saturacao = data.get('saturacao')
        nivel_dor = data.get('nivel_dor')
        alergia = data.get('alergia')
        medicamento_uso = data.get('medicamento_uso')
        classificacao_risco = data.get('classificacao_risco')

        cpf = data.get('cpf')

        # Retorna caso algum dado não tenha sido informado
        if (not queixa or not temperatura or not pressao or not frequencia_cardiaca
            or not saturacao or not nivel_dor or not alergia or not medicamento_uso
            or not classificacao_risco or not cpf):

            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

        cursor.execute('''
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE CPF = ?
        ''', (cpf,))

        user_exist = cursor.fetchone()

        # Retorna caso usuário não exista
        if not user_exist:
            return jsonify({
                'error': 'Paciente não encontrado.'
            }), 404

        # Id do paciente
        id_paciente = user_exist[0]

        # Seleciona uma triagem em andamento existente
        cursor.execute('''
            SELECT ID_CONSULTA
            FROM CONSULTA
            WHERE ID_USUARIO = ? AND SITUACAO = 2
        ''', (id_paciente,))

        consulta_exist = cursor.fetchone()

        # Retorna caso nenhuma consulta seja encontrada
        if not consulta_exist:
            return jsonify({
                'error': 'Nenhuma consulta encontrada.'
            }), 404

        id_consulta = consulta_exist[0]

        # Verifica se já possui triagem cadastrada
        cursor.execute('''
            SELECT 1
            FROM TRIAGEM
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        # Caso possua, retorna
        if cursor.fetchone():
            # Atualiza a situação
            cursor.execute('''
                UPDATE CONSULTA
                SET SITUACAO = 3
                WHERE ID_CONSULTA = ?
            ''', (id_consulta,))

            # Salva as alterações
            con.commit()

            return jsonify({
                'error': 'Triagem já cadastrada.'
            }), 401

        # Cria a triagem
        cursor.execute('''
            INSERT INTO TRIAGEM
            (ID_CONSULTA, QUEIXA, TEMPERATURA, PRESSAO, FREQUENCIA_CARDIACA,
            SATURACAO, NIVEL_DOR, ALERGIA, MEDICAMENTO_USO, CLASSIFICACAO_RISCO,
            ID_ENFERMEIRO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (id_consulta, queixa, temperatura, pressao, frequencia_cardiaca, saturacao,
              nivel_dor, alergia, medicamento_uso, classificacao_risco, id_usuario))

        # Atualiza a situação
        cursor.execute('''
            UPDATE CONSULTA
            SET SITUACAO = 3
            WHERE ID_CONSULTA = ?
        ''', (id_consulta,))

        # Salva as alterações
        con.commit()

        return jsonify({
            'success': 'Triagem iniciada com sucesso!'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()