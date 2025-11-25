from flask import request, jsonify
from main import app, con, socketio
from components.utils import validar_token, remover_bearer, is_empty
from flask_socketio import emit
from datetime import datetime

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

        like = request.args.get('s')

        if like:
            like = like.upper()

        # Busca os dados
        cursor.execute(f"""    
                          SELECT ID_CONSULTA
                               , DATA_ENTRADA
                               , SITUACAO 
                               , NOME 
                               , SEXO 
                               , IDADE
                               , CLASSIFICACAO_RISCO 
                               , TEMPO_DECORRIDO
                               , CPF
                            FROM PR_LISTA_CONSULTA(?, ?)
                       """, (situacao, like))

        res = cursor.fetchall()

        consultas = []

        posicao = 0

        if res:
            for consulta in res:
                posicao = posicao + 1

                consultas.append({
                    "posicao": posicao,
                    "id_consulta": consulta[0],
                    "data_entrada": consulta[1].strftime("%d/%m/%Y %H:%M") if consulta[0] else None,
                    "situacao": consulta[2].strip('  '),
                    "nome": consulta[3],
                    "sexo": consulta[4],
                    "idade": consulta[5],
                    "classificacao_risco": consulta[6].strip() if consulta[5] else None,
                    "tempo_decorrido": consulta[7],
                    "cpf": consulta[8]
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

# Rota para obter as consultas de um usuário
@app.route('/get_consultas', methods=['GET'])
def get_consultas_user():
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

        pacienteRequest = request.args.get('p')

        if pacienteRequest:
            # Obtém o tipo de usuário
            cursor.execute('''
                    SELECT CPF
                    FROM USUARIO
                    WHERE ID_USUARIO = ? AND ATIVO = 1
                ''', (id_usuario,))
        else:
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

        if pacienteRequest:
            cpf = result[0]
        else:
            # Obtém o tipo do usuário
            tipo_usuario = int(result[0])

            if tipo_usuario not in [1,2,3,4,5]:
                return jsonify({
                    'error': 'Requisição não permitida.'
                }), 401

            cpf = request.args.get('cpf')

        if is_empty(cpf):
            return jsonify({
                'error': 'Informe o CPF do paciente.'
            }), 400

        cursor.execute('''
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE CPF = ? AND ATIVO = 1
        ''', (cpf,))

        result = cursor.fetchone()

        if not result:
            return jsonify({
                'error': 'Paciente não encontrado ou inativo.'
            }), 404

        # Obtém as médias de todo o período
        cursor.execute('''
                    select ESPERA_TRIAGEM, TRIAGEM, ESPERA_CONSULTA, DIAGNOSTICO 
                    from PR_TEMPO_MEDIO_ESPERA('0001-01-01', '9999-12-31');
                ''')

        datas = cursor.fetchone()

        if not datas:
            return jsonify({
                'error': 'Erro ao obter tempo de espera.'
            }), 400

        espera_triagem = datas[0]
        triagem = datas[1]
        espera_consulta = datas[2]
        diagnostico = datas[3]

        id_paciente = result[0]

        cursor.execute('''
            SELECT 
                paciente.NOME, 
                c.DATA_ENTRADA, 
                CASE c.SITUACAO
                    WHEN 1 THEN 'Aguardando triagem'
                    WHEN 2 THEN 'Na triagem'
                    WHEN 3 THEN 'Aguardando consulta'
                    WHEN 4 THEN 'Na consulta'
                    WHEN 5 THEN 'Alta recebida'
                    ELSE ''
                END AS SITUACAO,
                COALESCE(recepcionista.NOME, '~') AS RECEPCIONISTA,
                COALESCE(enfermeiro.NOME, '~') AS ENFERMEIRO,
                COALESCE(medico.NOME, '~') AS MEDICO,
                c.ID_CONSULTA,
                d.DIAGNOSTICO,
                c.SITUACAO,
                d.DATA_DIAGNOSTICO
            FROM CONSULTA c
            LEFT JOIN TRIAGEM t ON t.ID_CONSULTA = c.ID_CONSULTA 
            LEFT JOIN DIAGNOSTICO d ON d.ID_CONSULTA = c.ID_CONSULTA
            LEFT JOIN USUARIO paciente ON paciente.ID_USUARIO = c.ID_USUARIO
            LEFT JOIN USUARIO recepcionista ON recepcionista.ID_USUARIO = c.ID_RECEPCIONISTA
            LEFT JOIN USUARIO enfermeiro ON enfermeiro.ID_USUARIO = t.ID_ENFERMEIRO 
            LEFT JOIN USUARIO medico ON medico.ID_USUARIO = d.ID_MEDICO 
            WHERE c.ID_USUARIO = ?
            ORDER BY c.DATA_ENTRADA DESC
        ''', (id_paciente,))

        data_consultas = cursor.fetchall()

        consultas = []

        for consulta in data_consultas:
            # Obtém o tempo de espera correto para determinada etapa
            tempo_espera = (
                espera_triagem if consulta[8] == 1 else
                triagem if consulta[8] == 2 else
                espera_consulta if consulta[8] == 3 else
                diagnostico if consulta[8] == 4 else
                int((consulta[9] - consulta[1]).total_seconds() // 60)
            )

            consultas.append({
                'paciente': consulta[0],
                'data_entrada': consulta[1],
                'situacao': consulta[2].strip(),
                'recepcionista': consulta[3],
                'enfermeiro': consulta[4],
                'medico': consulta[5],
                'id_consulta': consulta[6],
                'diagnostico': consulta[7],
                'situacao_vetor': consulta[8],
                'tempo_espera': tempo_espera
            })

        return jsonify({
            "consultas": consultas
        }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        cursor.close()