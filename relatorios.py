from flask import send_file, jsonify
from main import app, con
from fpdf import FPDF
from datetime import datetime
import re
import unicodedata

# Funções de formatação
def remove_acentos(texto):
    if texto is None:
        return ""
    if not isinstance(texto, str):
        texto = str(texto)
    # Remove acentos e converte para caracteres ASCII
    texto_sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return texto_sem_acento

def format_none(value):
    return "Não informado" if value in [None, "none", "None", ""] else value

def format_phone(phone):
    if phone is None:
        return None
    phone_str = str(phone)
    digits = re.sub(r'\D', '', phone_str)
    if len(digits) == 11:
        return f"({digits[0:2]}) {digits[2:7]}-{digits[7:]}"
    elif len(digits) == 10:
        return f"({digits[0:2]}) {digits[2:6]}-{digits[6:]}"
    else:
        return phone_str

def format_date(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, datetime):
        return date_value.strftime('%d/%m/%Y')
    try:
        dt = datetime.strptime(str(date_value), '%Y-%m-%d')
        return dt.strftime('%d/%m/%Y')
    except ValueError:
        return str(date_value)

# Fim das funções de formatação


class PDFReceitaPaciente(FPDF):
    def __init__(self, paciente_nome, medico_nome, medico_crm, receita, data):
        # Usando tamanho A5: 148 × 210 mm
        super().__init__(format=(148, 210))
        self.paciente_nome = paciente_nome
        self.medico_nome = medico_nome
        self.medico_crm = medico_crm
        self.receita = receita
        self.data = data

    def header(self):
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 8, remove_acentos('Hospital Demonstracao'), ln=True, align='C')
        self.ln(4)

    def footer(self):
        self.set_y(-25)

        # Data de emissão
        self.set_font('Helvetica', '', 9)
        data_emissao = self.data.strftime('%d/%m/%Y %H:%M')
        self.cell(0, 5, remove_acentos(f"Emitido em: {data_emissao}"), ln=True, align='C')
        self.ln(3)

        self.set_y(-20)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 4, remove_acentos('Endereco: Rua da Saude, 123 - Sao Paulo/SP'), ln=True, align='C')
        self.cell(0, 4, remove_acentos('Telefone: (11) 1234-5678 | CNPJ: 00.000.000/0001-00'), ln=True, align='C')



    def corpo(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 25, remove_acentos('RECEITA MEDICA'), ln=True, align='C')
        self.ln(3)

        # Dados do paciente
        self.set_font('Helvetica', 'B', 10)
        self.cell(17, 5, remove_acentos("Paciente:"), ln=False)
        self.set_font('Helvetica', '', 10)
        self.cell(0, 5, remove_acentos(format_none(self.paciente_nome)), ln=True)
        self.ln(10)

        # Prescrição médica
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, remove_acentos('Prescricao Medica:'), ln=True)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, remove_acentos(format_none(self.receita)), ln=True)

        # Assinatura médica no meio da folha
        meio_altura = (self.h / 3) * 2
        self.set_y(meio_altura)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, remove_acentos('____________________________'), 0, 1, 'C')
        self.cell(0, 4, remove_acentos(f"Dr. {format_none(self.medico_nome)}"), 0, 1, 'C')
        self.cell(0, 4, remove_acentos(f"CRM {format_none(self.medico_crm)}"), 0, 1, 'C')


class PDFReceitaEnfermagem(FPDF):
    def __init__(self, paciente_nome, medico_nome, medico_crm, receita_enfermagem, data):
        # Usando tamanho A5: 148 × 210 mm
        super().__init__(format=(148, 210))
        self.paciente_nome = paciente_nome
        self.medico_nome = medico_nome
        self.medico_crm = medico_crm
        self.receita_enfermagem = receita_enfermagem
        self.data = data

    def header(self):
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 8, remove_acentos('Hospital Demonstracao'), ln=True, align='C')
        self.ln(4)

    def footer(self):
        self.set_y(-25)

        # Data de emissão
        self.set_font('Helvetica', '', 9)
        data_emissao = self.data.strftime('%d/%m/%Y %H:%M')
        self.cell(0, 5, remove_acentos(f"Emitido em: {data_emissao}"), ln=True, align='C')
        self.ln(3)

        self.set_y(-20)
        self.set_font('Helvetica', '', 8)
        self.cell(0, 4, remove_acentos('Endereco: Rua da Saude, 123 - Sao Paulo/SP'), ln=True, align='C')
        self.cell(0, 4, remove_acentos('Telefone: (11) 1234-5678 | CNPJ: 00.000.000/0001-00'), ln=True, align='C')



    def corpo(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 25, remove_acentos('RECEITA MEDICA INTERNA'), ln=True, align='C')
        self.ln(3)

        # Dados do paciente
        self.set_font('Helvetica', 'B', 10)
        self.cell(17, 5, remove_acentos("Paciente:"), ln=False)
        self.set_font('Helvetica', '', 10)
        self.cell(0, 5, remove_acentos(format_none(self.paciente_nome)), ln=True)
        self.ln(10)

        # Prescrição médica
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, remove_acentos('Prescricao Medica Interna:'), ln=True)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, remove_acentos(format_none(self.receita_enfermagem)), ln=True)

        # Assinatura médica no meio da folha
        meio_altura = (self.h / 3) * 2
        self.set_y(meio_altura)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 4, remove_acentos(f"Dr. {format_none(self.medico_nome)}"), 0, 1, 'C')
        self.cell(0, 4, remove_acentos(f"CRM {format_none(self.medico_crm)}"), 0, 1, 'C')

@app.route('/relatorio/receita/paciente/<int:id_consulta>', methods=['GET'])
def criar_pdf_receita_paciente(id_consulta):
    try:

        cursor = con.cursor()

        cursor.execute("""
            SELECT pac.NOME AS NOME_PACIENTE, med.NOME AS NOME_MEDICO, med.COREN_CRM_SUS, d.RECEITA 
            FROM CONSULTA c
            INNER JOIN USUARIO pac ON pac.ID_USUARIO = c.ID_USUARIO
            INNER JOIN DIAGNOSTICO d ON c.ID_CONSULTA = c.ID_CONSULTA
            INNER JOIN USUARIO med ON med.ID_USUARIO = d.ID_MEDICO
            WHERE c.ID_CONSULTA = ? 
        """
            , (id_consulta, ))

        consulta = cursor.fetchone()

        paciente_nome = consulta[0]
        medico_nome   = consulta[1]
        medico_crm    = consulta[2]
        receita       = consulta[3]

        data = datetime.now()

        pdf = PDFReceitaPaciente(paciente_nome, medico_nome, medico_crm, receita, data)
        pdf.add_page()
        pdf.corpo()

        output_path = "receita_medica_paciente.pdf"
        pdf.output(output_path)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        cursor.close()

@app.route('/relatorio/receita/enfermagem/<int:id_consulta>', methods=['GET'])
def criar_pdf_receita_enfermagem(id_consulta):
    try:

        cursor = con.cursor()

        cursor.execute("""
            SELECT pac.NOME AS NOME_PACIENTE, med.NOME AS NOME_MEDICO, med.COREN_CRM_SUS, d.RECEITA_ENFERMAGEM 
            FROM CONSULTA c
            INNER JOIN USUARIO pac ON pac.ID_USUARIO = c.ID_USUARIO
            INNER JOIN DIAGNOSTICO d ON c.ID_CONSULTA = c.ID_CONSULTA
            INNER JOIN USUARIO med ON med.ID_USUARIO = d.ID_MEDICO
            WHERE c.ID_CONSULTA = ? 
        """
               , (id_consulta,))

        consulta = cursor.fetchone()

        paciente_nome = consulta[0]
        medico_nome = consulta[1]
        medico_crm = consulta[2]
        receita_enfermagem = consulta[3]

        data = datetime.now()

        pdf = PDFReceitaEnfermagem(paciente_nome, medico_nome, medico_crm, receita_enfermagem, data)
        pdf.add_page()
        pdf.corpo()

        output_path = "receita_medica_enfermagem.pdf"
        pdf.output(output_path)

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

    finally:
        cursor.close()