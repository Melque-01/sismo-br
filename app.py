"""Servidor HTTP da aplicação (MVC sem framework).

Responsabilidades deste arquivo:
- subir o servidor e escutar requisições;
- servir arquivos de `static/`;
- transformar a requisição em um dicionário `dados`;
- achar a função correspondente em `rotas/rotas.py` e devolver a resposta.

Execução:
    python app.py
"""

import json
import mimetypes
import os
import posixpath
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
from controles import respostas
from rotas.rotas import ROTAS
from servicos import sessoes

RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_STATIC = os.path.join(RAIZ, "static")

# Rotas que não exigem login (a página de login e o healthcheck).
ROTAS_PUBLICAS = {
    ("GET", "/login"),
    ("POST", "/login"),
    ("GET", "/registrar"),
    ("POST", "/registrar"),
    ("GET", "/api/status"),
}


class Manipulador(BaseHTTPRequestHandler):
    """Converte HTTP em chamadas para os controllers registrados em ROTAS."""

    server_version = "SismosBR/1.0"

    def do_GET(self):
        self._despachar("GET")

    def do_POST(self):
        self._despachar("POST")

    def do_PUT(self):
        self._despachar("PUT")

    def do_DELETE(self):
        self._despachar("DELETE")

    def _despachar(self, metodo):
        url = urllib.parse.urlparse(self.path)
        caminho = "/" + url.path.strip("/")

        if caminho.startswith("/static/"):
            return self._servir_static(caminho)

        dados = {
            chave: valores[0]
            for chave, valores in urllib.parse.parse_qs(url.query).items()
        }
        if metodo in ("POST", "PUT", "DELETE"):
            dados.update(self._ler_corpo())

        cabecalhos = {nome.lower(): valor for nome, valor in self.headers.items()}
        dados["_headers"] = cabecalhos
        dados["_cookies"] = self._ler_cookies(cabecalhos.get("cookie") or "")
        dados["_proto"] = (
            (cabecalhos.get("x-forwarded-proto") or "http").split(",")[0].strip()
        )
        dados["_ip"] = self.client_address[0]

        funcao = ROTAS.get((metodo, caminho))
        if funcao is None:
            return self._enviar(
                *respostas.json_resposta({"erro": "rota não encontrada"}, 404)
            )

        if (metodo, caminho) not in ROTAS_PUBLICAS:
            email = sessoes.validar_token(
                dados["_cookies"].get(sessoes.NOME_COOKIE)
            )
            if not email:
                if caminho.startswith("/api/"):
                    return self._enviar(
                        *respostas.json_resposta(
                            {"ok": False, "erro": "faça login para continuar"}, 401
                        )
                    )
                return self._enviar(*respostas.redirecionar("/login"))
            dados["_email"] = email

        try:
            status, cabecalhos_resposta, corpo = funcao(dados)
        except Exception as erro:  # noqa: BLE001 - falha inesperada vira 500
            traceback.print_exc()
            return self._enviar(
                *respostas.json_resposta({"erro": "erro interno: {}".format(erro)}, 500)
            )

        self._enviar(status, cabecalhos_resposta, corpo)

    @staticmethod
    def _ler_cookies(cabecalho):
        """Converte 'a=1; b=2' em dicionário."""
        cookies = {}
        for parte in cabecalho.split(";"):
            if "=" not in parte:
                continue
            nome, valor = parte.split("=", 1)
            cookies[nome.strip()] = valor.strip()
        return cookies

    def _ler_corpo(self):
        """Lê o corpo da requisição e devolve um dicionário."""
        tamanho = int(self.headers.get("content-length") or 0)
        if tamanho <= 0:
            return {}

        bruto = self.rfile.read(tamanho).decode("utf-8", errors="replace")
        tipo = (self.headers.get("content-type") or "").lower()

        if "application/json" in tipo:
            try:
                conteudo = json.loads(bruto)
            except json.JSONDecodeError:
                return {}
            return conteudo if isinstance(conteudo, dict) else {}

        return {
            chave: valores[0]
            for chave, valores in urllib.parse.parse_qs(bruto).items()
        }

    def _servir_static(self, caminho):
        """Entrega arquivos de `static/` bloqueando path traversal."""
        relativo = posixpath.normpath(
            urllib.parse.unquote(caminho[len("/static/") :])
        )
        if relativo.startswith("..") or os.path.isabs(relativo):
            return self._enviar(
                *respostas.json_resposta({"erro": "acesso negado"}, 403)
            )

        arquivo = os.path.join(PASTA_STATIC, relativo)
        if not os.path.isfile(arquivo):
            return self._enviar(
                *respostas.json_resposta({"erro": "arquivo não encontrado"}, 404)
            )

        tipo = mimetypes.guess_type(arquivo)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in (
            "application/javascript",
            "application/json",
        ):
            tipo += "; charset=utf-8"

        with open(arquivo, "rb") as arquivo_aberto:
            corpo = arquivo_aberto.read()

        self._enviar(200, {"content-type": tipo}, corpo)

    def _enviar(self, status, cabecalhos, corpo):
        self.send_response(status)
        for nome, valor in cabecalhos.items():
            self.send_header(nome, valor)
        self.send_header("content-length", str(len(corpo)))
        self.end_headers()
        if corpo:
            self.wfile.write(corpo)

    def log_message(self, formato, *args):
        print("[{}] {}".format(self.log_date_time_string(), formato % args))


def main():
    if not config.LOGIN_EMAIL or not config.LOGIN_SENHA:
        print(
            "AVISO: LOGIN_EMAIL/LOGIN_SENHA não configurados. O site exige "
            "login e ninguém conseguirá entrar até definir as credenciais."
        )
    if not config.SEGREDO_SESSAO:
        print(
            "AVISO: SESSION_SECRET não definido; as sessões serão invalidadas "
            "a cada reinício do processo."
        )

    try:
        from db.database import criar_tabelas

        criar_tabelas()
        print("Banco: schema aplicado.")
        from modelo import usuario

        if usuario.garantir_admin_inicial(
            config.LOGIN_EMAIL, config.LOGIN_SENHA
        ):
            print("Usuário inicial criado a partir do .env.")
    except Exception as erro:  # noqa: BLE001 - app sobe mesmo sem banco
        print(
            "AVISO: sem banco de dados ({}). O mapa abre, mas as consultas "
            "vão responder 503.".format(erro)
        )

    servidor = ThreadingHTTPServer((config.HOST, config.PORTA), Manipulador)
    print(
        "Servidor em http://{}:{} (Ctrl+C para parar)".format(
            config.HOST, config.PORTA
        )
    )
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
