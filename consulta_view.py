from flask import request, jsonify
from main import app, con, socketio
from components.utils import validar_token, remover_bearer
from flask_socketio import emit

@app.route('/consulta', methods=['POST'])
def add_consulta():
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
            # Se o usuário não for paciente, retorna
            if tipo_usuario != 4:
                return jsonify({
                    'error': 'Usuário não autorizado.',
                    'logout': True
                }), 401

        # Obtém os dados
        data = request.get_json()

        situacao = data.get('situacao')
        cpf = data.get('cpf')

        # Caso não tenha situação ou cpf, retorna
        if not situacao or not cpf:
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

        id_paciente = user_exist[0]

        # Verifica se o paciente já possui consulta ativa
        cursor.execute('''
            SELECT 1
            FROM CONSULTA
            WHERE ID_USUARIO = ? AND SITUACAO != ?
        ''', (id_paciente, 5))

        consulta_exist = cursor.fetchone()

        # Retorna caso já possua consulta cadastrada
        if consulta_exist:
            return jsonify({
                'error': 'Paciente já possui consulta em andamento.'
            }), 401

        # Insere a consulta na tabela
        cursor.execute('''
            INSERT INTO CONSULTA
            (ID_USUARIO, SITUACAO, ID_RECEPCIONISTA)
            VALUES (?, ?, ?)
        ''', (id_paciente, situacao, id_usuario))

        # Salva os dados
        con.commit()

        return jsonify({
            'success': 'Consulta cadastrada com sucesso!'
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()

@app.route('/consultas/<int:situacao>', methods=['GET'])
def get_consultas(situacao):
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
        if tipo_usuario not in [1, 2, 3, 4]:
            return jsonify({
                'error': 'Usuário não autorizado.',
                'logout': True
            }), 401

        # Busca os dados
        cursor.execute("""    
                          SELECT DATA_ENTRADA
                               , SITUACAO 
                               , NOME 
                               , SEXO 
                               , IDADE
                               , CLASSIFICACAO_RISCO 
                               , TEMPO_DECORRIDO
                               , CPF
                            FROM PR_LISTA_CONSULTA(?)
                       """, (situacao,))

        res = cursor.fetchall()

        consultas = []

        posicao = 0

        if res:
            for consulta in res:
                posicao = posicao + 1

                consultas.append({
                    "posicao": posicao,
                    "data_entrada": consulta[0].strftime("%d/%m/%Y %H:%M") if consulta[0] else None,
                    "situacao": consulta[1].strip('  '),
                    "nome": consulta[2],
                    "sexo": consulta[3],
                    "idade": consulta[4],
                    "classificacao_risco": consulta[5].strip() if consulta[5] else None,
                    "tempo_decorrido": consulta[6],
                    "cpf": consulta[7]
                })

        return jsonify({
            'consultas': consultas
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()