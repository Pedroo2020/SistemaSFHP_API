from flask import Flask
from flask_cors import CORS
import fdb

app = Flask(__name__)
CORS(app, origins=["*"])

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

if __name__ == '__main__':
    app.run(debug=True)