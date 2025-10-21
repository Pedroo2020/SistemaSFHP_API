# import eventlet
# eventlet.monkey_patch()

from flask import Flask
import fdb
from flask_socketio import SocketIO
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=['*'])
socketio = SocketIO(app, cors_allowed_origins="*")

app.config.from_pyfile('config.py')

host = app.config['DB_HOST']
database = app.config['DB_NAME']
user = app.config['DB_USER']
password = app.config['DB_PASSWORD']

senha_app_email = app.config['SENHA_APP_EMAIL']
senha_secreta = app.config['SECRET_KEY']
upload_folder = app.config['UPLOAD_FOLDER']

try:
    con = fdb.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        charset='UTF8'
    )
    print('Conexão estabelecida com sucesso')
except Exception as e:
    print(f'Error: {e}')

from cadastro_view import *
from login_view import *
from consulta_view import *
from triagem_view import *
from diagnostico_view import *

if __name__ == '__main__':
    socketio.run(app, port=5000, allow_unsafe_werkzeug=True)