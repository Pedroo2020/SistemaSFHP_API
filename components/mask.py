import re

# Validar senha
def validar_senha(senha):
    if len(senha) < 8:
        return "A senha deve ter pelo menos 8 caracteres."

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", senha):
        return "A senha deve conter pelo menos um símbolo especial (!@#$%^&*...)."

    if not re.search(r"[A-Z]", senha):
        return "A senha deve conter pelo menos uma letra maiúscula."

    if not re.search(r"[0-9]", senha):
        return "A senha deve conter pelo menos um número."

    return True

def validar_cpf(cpf: str) -> bool:
    if not isinstance(cpf, str):
        return False

    # Remove tudo que não for dígito
    num = re.sub(r'\D', '', cpf)

    # Deve ter 11 dígitos
    if len(num) != 11:
        return False

    # Não pode ser sequência de mesmo dígito (ex: '00000000000', '11111111111', ...)
    if num == num[0] * 11:
        return False

    # Calcula o primeiro dígito verificador
    def calc_dig(slice_digits, multipliers):
        s = sum(int(d) * m for d, m in zip(slice_digits, multipliers))
        r = s % 11
        return '0' if r < 2 else str(11 - r)

    # primeiros 9 dígitos
    d1 = calc_dig(num[:9], range(10, 1, -1))
    # primeiros 9 + d1 -> primeiros 10 para calcular d2
    d2 = calc_dig(num[:9] + d1, range(11, 1, -1))

    return num[-2:] == (d1 + d2)

def validar_sus(numero: str) -> bool:
    if not isinstance(numero, str):
        return False

    num = re.sub(r'\D', '', numero)

    if len(num) != 15:
        return False

    # Se todos os dígitos forem iguais → inválido
    if num == num[0] * 15:
        return False

    inicio = num[0]

    # CNS definitivos (1 ou 2)
    if inicio in ('1', '2'):
        base = num[:13]
        dv_informado = num[13:]

        soma1 = sum(int(d) * (15 - i) for i, d in enumerate(base))
        resto1 = soma1 % 11
        dv1 = 0 if resto1 in (0, 1) else 11 - resto1

        soma2 = sum(int(d) * (16 - i) for i, d in enumerate(base + str(dv1)))
        resto2 = soma2 % 11
        dv2 = 0 if resto2 in (0, 1) else 11 - resto2

        dv_calculado = f"{dv1}{dv2}"
        return dv_informado == dv_calculado

    # CNS profissionais (7): apenas verificar se são 15 dígitos
    elif inicio == '7':
        return True  # regra específica do MS, não tem cálculo simples

    # CNS provisórios (8 ou 9): só verificar tamanho
    elif inicio in ('8', '9'):
        return True

    return False

def validar_coren_crm(numero: str) -> bool:
    if not isinstance(numero, str):
        return False

    # Ex: 123456-SP ou 123456
    padrao = r'^\d{6,8}(-[A-Z]{2})?$'
    return re.match(padrao, numero) is not None

def validar_telefone(telefone: str) -> bool:
    if not isinstance(telefone, str):
        return False

    # Remove caracteres não numéricos
    num = re.sub(r'\D', '', telefone)

    # Aceita formatos:
    # 10 dígitos (fixo: DDD + 8)
    # 11 dígitos (celular: DDD + 9 + 8)
    return len(num) in (10, 11)