from flask import jsonify, request
from main import app, con
from flask_bcrypt import generate_password_hash
from components.mask import validar_senha, validar_cpf, validar_sus, validar_coren_crm, validar_telefone, validar_nascimento
from components.utils import remover_bearer, validar_token

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
        senha = data.get('senha')

        # Retorna caso dados incompletos
        if not nome or not email or not cpf or not telefone or not sexo or not nascimento or not tipo_usuario:
            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

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

        # Valida o CPF, telefone e a data de nascimento
        cpf_valido = validar_cpf(cpf)
        telefone_valido = validar_telefone(telefone)
        nascimento_valido = validar_nascimento(nascimento)

        # CPF inválido
        if not cpf_valido:
            return jsonify({
                'error': 'CPF inválido.'
            }), 400

        # Telefone inválido
        if not telefone_valido:
            return jsonify({
                'error': 'Telefone inválido.'
            }), 400

        # Data de nacimento inválida
        if not nascimento_valido:
            return jsonify({
                'error': 'Data de nascimento inválida.'
            }), 400

        # SUS e coren inválidos
        if tipo_usuario == 5:

            # Verifica se o usuário informou o documento
            if not coren_crm_sus:
                return jsonify({
                    'error': 'Informe o número do SUS.'
                }), 400

            sus_valido = validar_sus(coren_crm_sus)

            if not sus_valido:
                return jsonify({
                    'error': 'Número do SUS inválido.'
                }), 400

            # Caso o usuário seja paciente, gera senha a partir do número do sus
            senha_hash = generate_password_hash(coren_crm_sus)

        else:
            # Caso seja médico ou enfermeiro, verifica CRM / COREN
            if tipo_usuario in [2, 3]:

                # Verifica se o usuário informou o documento
                if not coren_crm_sus:
                    return jsonify({
                        'error': f'Informe o {'CRM' if tipo_usuario == 2 else 'COREN'}.'
                    }), 400

                crm_coren_valido = validar_coren_crm(coren_crm_sus)

                if not crm_coren_valido:
                    return jsonify({
                        'error': f'{'CRM' if tipo_usuario == 2 else 'COREN'} inválido.'
                    }), 400

            # Caso a senha não for informada
            if not senha:
                return jsonify({
                    'error': 'Informe a senha.'
                }), 400

            # Verifica se a senha é forte
            senha_valida = validar_senha(senha)

            # Retorna o erro da senha
            if senha_valida is not True:
                return jsonify({
                    'error': senha_valida
                }), 400

            # Gera a senha criptografada
            senha_hash = generate_password_hash(senha)

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

        # Cadastro o usuário no banco
        cursor.execute('''
            INSERT INTO USUARIO
            (NOME, EMAIL, CPF, COREN_CRM_SUS, TELEFONE, SEXO, DATA_NASCIMENTO, TIPO_USUARIO, SENHA, TENTATIVA_ERRO, ATIVO)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
        ''', (nome.upper(), email, cpf, coren_crm_sus, telefone, sexo, nascimento, tipo_usuario, senha_hash))

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


@app.route('/users', methods=['GET'])
def get_all_users():
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

        # Seleciona o tipo do usuário
        cursor.execute('''
            SELECT TIPO_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        ''', (id_usuario,))

        user_exist = cursor.fetchone()

        # Retorna caso usuário não exista
        if not user_exist:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        # Obtém o tipo do usuário
        tipo_usuario = user_exist[0]

        # Retorna caso o usuário não seja ADM, médico, enfermeiro ou recepcionista
        if tipo_usuario not in [1,2,3,4]:
            return jsonify({
                'error': 'Requisição não autorizada.'
            }), 401


        # Obtém todos os usuários
        cursor.execute('''
            SELECT NOME, EMAIL, CPF, TELEFONE, DATA_NASCIMENTO, SEXO, TIPO_USUARIO, COREN_CRM_SUS
            FROM USUARIO
        ''', (id_usuario,))

        data = cursor.fetchall()

        if not data:
            return jsonify({
                'error': 'Nenhum usuário encontrado.'
            }), 404

        users = []

        for user in data:
            users.append({
                'nome': user[0],
                'email': user[1],
                'cpf': user[2],
                'telefone': user[3],
                'data_nascimento': user[4],
                'sexo': user[5],
                'tipo_usuario': user[6],
                'coren_crm_sus': user[7]
            })

        return jsonify({
            "users": users
        }), 200
    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()

@app.route('/cadastro', methods=['PUT'])
def editar_user():
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
        cpfNovo = data.get('cpfNovo')
        cpfAntigo = data.get('cpfAntigo')
        coren_crm_sus = data.get('coren_crm_sus')
        telefone = data.get('telefone')
        sexo = data.get('sexo')
        nascimento = data.get('nascimento')
        tipo_usuario = data.get('tipo_usuario')
        senha = data.get('senha')

        # Valida o CPF e telefone
        cpf_valido = validar_cpf(cpfNovo)
        telefone_valido = validar_telefone(telefone)
        nascimento_valido = validar_nascimento(nascimento)

        # CPF inválido
        if not cpf_valido:
            return jsonify({
                'error': 'CPF inválido.'
            }), 400

        # Telefone inválido
        if not telefone_valido:
            return jsonify({
                'error': 'Telefone inválido.'
            }), 400

        # Data de nacimento inválida
        if not nascimento_valido:
            return jsonify({
                'error': 'Data de nascimento inválida.'
            }), 400

        # Retorna caso dados incompletos
        if not nome or not email or not cpfNovo or not telefone or not sexo or not nascimento or not tipo_usuario:
            return jsonify({
                'error': 'Dados incompletos.'
            }), 400

        # Usuário não for ADM, retorna
        if tipo_usuario_token != 1:

            if tipo_usuario_token != 4:
                return jsonify({
                    'error': 'Usuário não autorizado.'
                }), 401

            elif tipo_usuario != 5:
                return jsonify({
                    'error': 'Atualização de tipo de usuário não autorizada.'
                }), 401

        # SUS e coren inválidos
        if tipo_usuario == 5:

            # Verifica se o usuário informou o documento
            if not coren_crm_sus:
                return jsonify({
                    'error': 'Informe o número do SUS.'
                }), 400

            sus_valido = validar_sus(coren_crm_sus)

            if not sus_valido:
                return jsonify({
                    'error': 'Número do SUS inválido.'
                }), 400

            # Caso o usuário seja paciente, gera senha a partir do número do sus
            senha_hash = generate_password_hash(coren_crm_sus)

        else:
            # Caso seja médico ou enfermeiro, verifica CRM / COREN
            if tipo_usuario in [2, 3]:

                # Verifica se o usuário informou o documento
                if not coren_crm_sus:
                    return jsonify({
                        'error': f'Informe o {'CRM' if tipo_usuario == 2 else 'COREN'}.'
                    }), 400

                crm_coren_valido = validar_coren_crm(coren_crm_sus)

                if not crm_coren_valido:
                    return jsonify({
                        'error': f'{'CRM' if tipo_usuario == 2 else 'COREN'} inválido.'
                    }), 400

        # Caso os dados já existam, retorna
        user_exists = cursor.fetchone()

        if user_exists:
            cursor.close()
            return jsonify({
                'error': 'Dados já cadastrados.'
            }), 401

        # Parâmetros da query
        params = [nome, email, cpfNovo, coren_crm_sus or "", telefone, sexo, nascimento, tipo_usuario]

        if tipo_usuario in [1, 2, 3, 4]:
            # Caso a senha não for informada
            if senha:
                # Verifica se a senha é forte
                senha_valida = validar_senha(senha)

                # Retorna o erro da senha
                if senha_valida is not True:
                    return jsonify({
                        'error': senha_valida
                    }), 400

                # Gera a senha criptografada
                senha_hash = generate_password_hash(senha)

                params.append(senha_hash)

        params.append(cpfAntigo)

        # Cadastro os novos dados do usuário no banco
        cursor.execute(f'''
                UPDATE USUARIO
                SET NOME = ?, EMAIL = ?, CPF = ?, COREN_CRM_SUS = ?, TELEFONE = ?, SEXO = ?, DATA_NASCIMENTO = ?, TIPO_USUARIO = ? {', SENHA = ?' if senha else ''}
                WHERE CPF = ?
            ''', (params))

        # Salva as mudanças
        con.commit()

        # Retorna sucesso
        return jsonify({
            'success': 'Usuário editado com sucesso!'
        }), 200

    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()