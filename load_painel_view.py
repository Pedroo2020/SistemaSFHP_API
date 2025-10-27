from flask import request, jsonify
from main import app, con
from components.utils import validar_token, remover_bearer, is_empty

@app.route('/load_painel', methods=['GET'])
def load_painel():
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

        # Caso não seja funcionário do hospital
        if tipo_usuario not in [1,2,3,4]:
            return jsonify({
                'error': 'Requisição não autorizada.'
            }), 401

        data_inicio = request.args.get('i')
        data_fim = request.args.get('f')

        if is_empty(data_inicio):
            return jsonify({
                'error': 'Informe a data de início.'
            }), 400

        if is_empty(data_fim):
            return jsonify({
                'error': 'Informe a data de término.'
            }), 400

        if tipo_usuario == 1:

            cursor.execute('''
                SELECT 
                    COUNT(*),
                    COUNT(DISTINCT ID_USUARIO)
                FROM CONSULTA c
                WHERE CAST(c.DATA_ENTRADA AS DATE) BETWEEN ? AND ?
            ''', (data_inicio, data_fim))

            result = cursor.fetchone()

            total_consultas = 0
            total_pacientes = 0

            if result:
                total_consultas = result[0]
                total_pacientes = result[1]

            cursor.execute('''
                SELECT ESPERA_ATE_ALTA    
                FROM PR_TEMPO_MEDIO_ESPERA(?, ?)
            ''', (data_inicio, data_fim))

            tempo_medio = cursor.fetchone()[0]

            return jsonify({
                'total_pacientes': total_pacientes,
                'total_consultas': total_consultas,
                'tempo_medio': tempo_medio
            }), 200

        else:
            cursor.execute('''
                SELECT 
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN t.CLASSIFICACAO_RISCO IN (4,5) THEN 1 ELSE 0 END), 0) AS casos_urgentes
                FROM CONSULTA c
                LEFT JOIN TRIAGEM t ON t.ID_CONSULTA = c.ID_CONSULTA
                WHERE SITUACAO != 5
            ''')

            result = cursor.fetchone()

            total_pacientes = 0
            casos_urgentes = 0

            if result:
                total_pacientes = result[0]
                casos_urgentes = result[1]

            if tipo_usuario in [3,4]:
                cursor.execute('''
                    SELECT ESPERA_TRIAGEM    
                    FROM PR_TEMPO_MEDIO_ESPERA(?, ?)
                ''', (data_inicio, data_fim))
            else:
                cursor.execute('''
                    SELECT ESPERA_CONSULTA  
                    FROM PR_TEMPO_MEDIO_ESPERA(?, ?)
                ''', (data_inicio, data_fim))

            tempo_medio = cursor.fetchone()[0]

            return jsonify({
                'total_pacientes': total_pacientes,
                'casos_urgentes': casos_urgentes,
                'tempo_medio': tempo_medio
            }), 200

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 400

    finally:
        cursor.close()