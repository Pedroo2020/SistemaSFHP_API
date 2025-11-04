from flask import request, jsonify, current_app, render_template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import jwt
from flask_bcrypt import check_password_hash
from main import app, con, senha_secreta, socketio, senha_app_email
import json
from flask_socketio import emit
from components.utils import validar_token
from components.mask import validar_senha
import random
from threading import Thread
from flask_bcrypt import generate_password_hash

def generate_token(user_id, cpf):
    payload = {'id_usuario': user_id, 'cpf': cpf}
    token = jwt.encode(payload, senha_secreta, algorithm='HS256')
    return token


def enviar_email_recuperar_senha(email_destinatario, codigo):

    app_context = current_app._get_current_object()

    def task_envio():
        remetente = 'sfhp.sistema@gmail.com'
        senha = senha_app_email
        servidor_smtp = 'smtp.gmail.com'
        porta_smtp = 465  # Conexão SSL direta
        assunto = 'SFHP - Código de Verificação'

        # Renderiza o template com as variáveis desejadas dentro do contexto da aplicação
        with app_context.app_context():
            corpo = render_template('email-codigo.html', codigo=codigo, ano=datetime.now().year)

        # Cria e configura a mensagem do e-mail
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = email_destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'html'))

        try:
            # Usando SSL direto (mais confiável com Gmail)
            server = smtplib.SMTP_SSL(servidor_smtp, porta_smtp, timeout=60)
            server.set_debuglevel(1)  # Ative para debugging
            server.ehlo()  # Identifica-se ao servidor
            server.login(remetente, senha)
            text = msg.as_string()
            server.sendmail(remetente, email_destinatario, text)
            server.quit()
            print(f"E-mail de recuperação enviado para {email_destinatario}")
        except Exception as e:
            print(f"Erro ao enviar e-mail de recuperação: {e}")

    Thread(target=task_envio, daemon=True).start()

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

    # Retorna caso o CPF não exista
    if len(cpf) < 11:
        return jsonify({
            'error': 'CPF inválido.'
        }), 401

    try:
        # Abre o cursor
        cursor = con.cursor()

        # Obtém a senha criptografada e o id_usuario
        cursor.execute('''
            SELECT SENHA, ID_USUARIO, TENTATIVA_ERRO, ATIVO, TIPO_USUARIO
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
        tentativa_erro = user_exist[2]
        ativo = True if user_exist[3] == 1 else False
        tipo_usuario = int(user_exist[4])

        # Retorna caso usuário inativo
        if not ativo:
            return jsonify({
                'error': 'Usuário inativo.'
            }), 403

        # Verifica se a senha inserida é igual a criptografada
        senha_check = check_password_hash(senha_hash, senha)

        # Caso sejam diferentes, retorna
        if not senha_check:
            # Caso não seja ADM
            if tipo_usuario != 1:
                tentativa_erro = tentativa_erro + 1
                new_ativo = 1

                # Caso tenha 3 tentativas
                if tentativa_erro >= 3:
                    tentativa_erro = 0
                    new_ativo = 0

                # Atualiza as tentativas e o ativo
                cursor.execute('''
                    UPDATE USUARIO
                    SET TENTATIVA_ERRO = ?, ATIVO = ?
                    WHERE ID_USUARIO = ?
                ''', (tentativa_erro, new_ativo, id_usuario))

                con.commit()

            return jsonify({
                'error': 'Senha incorreta.'
            }), 401

        # Reseta as tentativas caso a senha esteja certa
        cursor.execute('''
            UPDATE USUARIO
            SET TENTATIVA_ERRO = ?
            WHERE ID_USUARIO = ?
        ''', (0, id_usuario))

        con.commit()

        # Gera o token
        token = generate_token(id_usuario, cpf)

        # Retorna sucesso e o token
        return jsonify({
            'success': 'Login realizado com sucesso!',
            'token': token,
            'tipo_usuario': tipo_usuario
        }), 200
    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        }), 400
    finally:
        # Fecha o cursor ao final
        cursor.close()

# Rota para gerar código de recuperação de senha
@app.route('/gerar_codigo', methods=['POST'])
def gerar_codigo():
    try:
        cursor = con.cursor()

        cpf = request.args.get('cpf')

        if not cpf:
            return jsonify({
                'error': 'CPF não informado.'
            }), 400

        cursor.execute('''
            SELECT EMAIL
            FROM USUARIO
            WHERE CPF = ?
        ''', (cpf,))

        user_exist = cursor.fetchone()

        if not user_exist:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        email = user_exist[0]
        codigo = ""

        # Gera um código aleatório de 6 dígitos
        for i in range(6):
            digit = random.randint(0,9)
            codigo += str(digit)

        enviar_email_recuperar_senha(email, codigo)

        cursor.execute('''
            UPDATE USUARIO
            SET CODIGO = ?
            WHERE email = ?
        ''', (codigo, email))

        email_lista = email.split('@')

        email_adress = list(email_lista[0])

        endereco_lista = email_lista[1].split('.')

        endereco = endereco_lista[0]
        final = endereco_lista[1]

        first_letter_email = email_adress[0]
        first_letter_endereco = endereco[0]

        con.commit()

        return jsonify({
            'success': 'Código de verificação enviado por e-mail.',
            'email': f'{first_letter_email}***@{first_letter_endereco}***.{final}'
        }), 200

    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()

# Validar código de verificação
@app.route('/validar_codigo', methods=['POST'])
def validar_codigo():

    cpf = request.args.get('cpf')
    codigo = request.args.get('codigo')

    if not cpf or not codigo:
        return jsonify({
            'error': 'CPF ou código não informados.'
        }), 400

    try:
        cursor = con.cursor()

        cursor.execute('''
            SELECT CODIGO, EMAIL
            FROM USUARIO
            WHERE CPF = ?
        ''', (cpf,))

        user_exist = cursor.fetchone()

        if not user_exist:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        codigo_banco = user_exist[0]
        email = user_exist[1]

        if str(codigo_banco) != str(codigo):
            return jsonify({
                'error': 'Código incorreto.'
            }), 400

        cursor.execute('''
            UPDATE USUARIO
            SET CODIGO = NULL, REC_SENHA = 1, DATAHORA_REC_SENHA = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (email,))

        con.commit()

        return jsonify({
            'success': 'Código validado com sucesso.'
        }), 200

    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()

# Alterar senha
@app.route('/alterar_senha', methods=['POST'])
def alterar_senha():
    cpf = request.args.get('cpf')

    data = request.get_json()

    senha = data.get('senha')
    confirmarSenha = data.get('confirmarSenha')

    if not senha or not confirmarSenha:
        return jsonify({
            'error': 'Informe e confirme a senha.'
        }), 400

    try:
        cursor = con.cursor()

        cursor.execute('''
            SELECT rec_senha, datahora_rec_senha, email
            FROM USUARIO
            WHERE CPF = ?
        ''', (cpf,))

        user_exist = cursor.fetchone()

        if not user_exist:
            return jsonify({
                'error': 'Usuário não encontrado.'
            }), 404

        if senha != confirmarSenha:
            return jsonify({
                'error': 'Senhas diferem.'
            }), 400

        rec_senha = True if user_exist[0] == 1 else False
        datahora_rec_senha = user_exist[1]
        email = user_exist[2]

        if not rec_senha:
            return jsonify({
                'error': 'Alteração não autorizada.'
            }), 401

        horario_atual = datetime.now()

        if horario_atual - datahora_rec_senha > timedelta(minutes=10):
            return jsonify({'error': 'Código expirado.'}), 401

        senha_check = validar_senha(senha)

        if senha_check is not True:
            return jsonify({
                'error': senha_check
            }), 400

        senha_hash = generate_password_hash(senha)

        cursor.execute('''
            UPDATE USUARIO
            SET SENHA = ?, REC_SENHA = NULL, DATAHORA_REC_SENHA = NULL
            WHERE EMAIL = ?
        ''', (senha_hash, email))

        con.commit()

        return jsonify({
            'success': 'Senha alterada com sucesso.'
        }), 200

    except Exception as e:
        # Retorna caso ocorra erro inesperado
        return jsonify({
            'error': str(e)
        })
    finally:
        # Fecha o cursor ao final
        cursor.close()

# Autenticar Socket.io
@socketio.on('autenticar')
def autenticar(data):

    # Obtém o token
    token = data['token']

    # Retorna caso seja nulo
    if not token:
        emit("autenticado", {"error": "Sessão não informada."})
        return False

    # Valida o token
    token_valido, payload = validar_token(token)

    # Obtém o id do usuário
    id_usuario = payload['id_usuario']

    # Retorna caso token inválido
    if not token_valido:
        emit("autenticado", {"error": "Sessão inválida."})
        return False

    # Lê o arquivo JSON
    with open("components/sid.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Adiciona o novo sid na lista
    data[id_usuario] = request.sid

    # Salva de volta no arquivo
    with open("components/sid.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Logout Socket.io
@socketio.on('logout')
def autenticar(data):

    # Obtém o token
    token = data['token']

    # Retorna caso seja nulo
    if not token:
        emit("autenticado", {"error": "Sessão não informada."})
        return False

    # Valida o token
    token_valido, payload = validar_token(token)

    # Obtém o id do usuário
    id_usuario = payload['id_usuario']

    # Retorna caso token inválido
    if not token_valido:
        emit("autenticado", {"error": "Sessão inválida."})
        return False

    # Lê o arquivo JSON
    with open("components/sid.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Se a chave existe, remove
    if str(id_usuario) in data:
        del data[str(id_usuario)]

    # Salva de volta no arquivo
    with open("components/sid.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)