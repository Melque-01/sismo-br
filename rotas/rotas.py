"""Tabela de rotas da aplicação.

Formato: (MÉTODO, CAMINHO) -> função do controller.

Toda função recebe um dicionário `dados` (query string + corpo) e devolve
a tupla (status, cabeçalhos, corpo_em_bytes).
"""

from controles import auth_controle, home_controle, sismo_controle

ROTAS = {
    ("GET", "/login"): auth_controle.login_form,
    ("POST", "/login"): auth_controle.login,
    ("GET", "/registrar"): auth_controle.registrar_form,
    ("POST", "/registrar"): auth_controle.registrar,
    ("POST", "/logout"): auth_controle.logout,
    ("GET", "/"): home_controle.index,
    ("GET", "/saiba-mais"): home_controle.saiba_mais,
    ("GET", "/api/densidade"): sismo_controle.api_densidade,
    ("GET", "/api/sismos"): sismo_controle.api_sismos,
    ("GET", "/api/celula"): sismo_controle.api_celula,
    ("GET", "/api/evento"): sismo_controle.api_evento,
    ("GET", "/api/estatisticas"): sismo_controle.api_estatisticas,
    ("GET", "/api/filtros"): sismo_controle.api_filtros,
    ("GET", "/api/status"): sismo_controle.api_status,
    ("GET", "/api/importacoes"): sismo_controle.api_importacoes,
}
