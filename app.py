"""Servidor HTTP da aplicação (MVC sem framework).

Responsabilidades deste arquivo:
- subir o servidor e escutar requisições;
- servir arquivos de `static/`;
- transformar a requisição em um dicionário `dados`;
- achar a função correspondente em `rotas/rotas.py` e devolver a resposta.

Execução:
    python app.py
"""

import ipaddress
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
    ("GET", "/saiba-mais"),
    ("GET", "/api/status"),
}

# Proxies confiáveis (nginx no host, cloudflared no container). Só eles
# podem declarar o IP do cliente e o protocolo externo. Aceita IP solto e
# rede CIDR (ex.: a subrede do docker compose, para o cloudflared).
PROXIES_CONFIAVEIS = {
    ip.strip()
    for ip in os.getenv("PROXIES_CONFIAVEIS", "127.0.0.1,::1,172.19.0.1").split(",")
    if ip.strip()
}
REDES_CONFIAVEIS = []
for _item in os.getenv("PROXIES_CONFIAVEIS", "127.0.0.1,::1,172.19.0.1").split(","):
    _item = _item.strip()
    if not _item:
        continue
    try:
        REDES_CONFIAVEIS.append(ipaddress.ip_network(_item, strict=False))
    except ValueError:
        pass  # não é rede: pode ser IP solto, coberto por PROXIES_CONFIAVEIS


def proxy_confiavel(peer):
    """Peer pode declarar cabeçalhos de proxy? (IP exato ou dentro de CIDR)"""
    if peer in PROXIES_CONFIAVEIS:
        return True
    try:
        endereco = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(endereco in rede for rede in REDES_CONFIAVEIS)


def ip_cliente(peer, cabecalhos):
    """IP real do cliente; cabeçalho de proxy só vale se o peer for confiável.

    Em `X-Forwarded-For` vale a ÚLTIMA entrada: é a que o proxy confiável
    anexou (nginx/Cloudflare anexam). As anteriores vêm do cliente e podem
    ser forjadas.
    """
    if not proxy_confiavel(peer):
        return peer
    candidatos = [(cabecalhos.get("x-real-ip") or "").strip()]
    encadeados = [
        entrada.strip()
        for entrada in (cabecalhos.get("x-forwarded-for") or "").split(",")
    ]
    candidatos.extend(reversed(encadeados))
    for candidato in candidatos:
        if not candidato:
            continue
        try:
            return str(ipaddress.ip_address(candidato))
        except ValueError:
            continue
    return peer


class Manipulador(BaseHTTPRequestHandler):
    """Converte HTTP em chamadas para os controllers registrados em ROTAS."""

    server_version = "SismosBR/1.0"

    def do_GET(self):
        self._despachar("GET")

    def do_HEAD(self):
        self._despachar("HEAD")

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
        confiavel = proxy_confiavel(self.client_address[0])
        # Proto externo: só cabeçalho de proxy confiável conta. Sem proxy
        # (acesso direto à origem), a conexão é HTTP puro por definição.
        proto_cabecalho = ""
        if confiavel:
            proto_cabecalho = (
                (cabecalhos.get("x-forwarded-proto") or "").strip().split(",")[0].lower()
            )
        dados["_proto"] = proto_cabecalho or "http"
        dados["_ip"] = ip_cliente(self.client_address[0], cabecalhos)

        # Segurança de transporte: só o proxy pode dizer o protocolo externo.
        self._https = dados["_proto"] == "https"
        self._privado = caminho.startswith("/api/") or caminho in (
            "/login",
            "/registrar",
        )
        if confiavel and proto_cabecalho == "http":
            # HOST_CANONICO evita 301 refletindo o Host do request
            # (envenenamento de cache de intermediários).
            host = config.HOST_CANONICO or (cabecalhos.get("host") or "localhost")
            alvo = "https://{}{}".format(host, self.path)
            return self._enviar(*respostas.redirecionar(alvo, status=301))

        funcao = ROTAS.get((metodo, caminho))
        chave_rota = (metodo, caminho)
        if funcao is None and metodo == "HEAD":
            chave_rota = ("GET", caminho)
            funcao = ROTAS.get(chave_rota)
        if funcao is None:
            return self._enviar(
                *respostas.json_resposta({"erro": "rota não encontrada"}, 404)
            )

        if chave_rota not in ROTAS_PUBLICAS:
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
        except Exception:  # noqa: BLE001 - falha inesperada vira 500
            traceback.print_exc()
            return self._enviar(
                *respostas.json_resposta({"erro": "erro interno"}, 500)
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

    def _intervalo_range(self, tamanho):
        """Interpreta um único Range. Devolve (inicio, fim), None ou 'invalido'."""
        cabecalho = (self.headers.get("range") or "").strip()
        if not cabecalho:
            return None
        if not cabecalho.lower().startswith("bytes="):
            return "invalido"

        bruto = cabecalho[6:].strip()
        if "," in bruto or "-" not in bruto:
            return "invalido"

        inicio_txt, fim_txt = bruto.split("-", 1)
        try:
            if not inicio_txt:
                quantidade = int(fim_txt)
                if quantidade <= 0:
                    return "invalido"
                inicio = max(0, tamanho - quantidade)
                fim = tamanho - 1
            else:
                inicio = int(inicio_txt)
                fim = int(fim_txt) if fim_txt else tamanho - 1
        except ValueError:
            return "invalido"

        if tamanho <= 0 or inicio < 0 or inicio >= tamanho or fim < inicio:
            return "invalido"
        return inicio, min(fim, tamanho - 1)

    def _servir_static(self, caminho):
        """Entrega arquivos de `static/` bloqueando path traversal."""
        relativo = posixpath.normpath(
            urllib.parse.unquote(caminho[len("/static/") :])
        )
        if relativo.startswith("..") or os.path.isabs(relativo):
            return self._enviar(
                *respostas.json_resposta({"erro": "acesso negado"}, 403)
            )

        raiz = os.path.realpath(PASTA_STATIC)
        arquivo = os.path.realpath(os.path.join(raiz, relativo))
        try:
            dentro = os.path.commonpath([raiz, arquivo]) == raiz
        except ValueError:
            dentro = False
        if not dentro:
            return self._enviar(
                *respostas.json_resposta({"erro": "acesso negado"}, 403)
            )

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

        tamanho = os.path.getsize(arquivo)
        intervalo = self._intervalo_range(tamanho)
        if intervalo == "invalido":
            return self._enviar(
                416,
                {
                    "content-type": tipo,
                    "accept-ranges": "bytes",
                    "content-range": "bytes */{}".format(tamanho),
                },
                b"",
            )
        if intervalo is not None:
            inicio, fim = intervalo
            return self._enviar_arquivo(
                206,
                {
                    "content-type": tipo,
                    "accept-ranges": "bytes",
                    "content-range": "bytes {}-{}/{}".format(
                        inicio, fim, tamanho
                    ),
                },
                arquivo,
                inicio,
                fim - inicio + 1,
            )

        self._enviar_arquivo(
            200,
            {"content-type": tipo, "accept-ranges": "bytes"},
            arquivo,
            0,
            tamanho,
        )

    def _iniciar_resposta(self, status, cabecalhos):
        """Envia status e cabeçalhos comuns, sem content-length."""
        self.send_response(status)
        cabecalhos = dict(cabecalhos)
        cabecalhos.setdefault("x-content-type-options", "nosniff")
        cabecalhos.setdefault("x-frame-options", "DENY")
        cabecalhos.setdefault(
            "referrer-policy", "strict-origin-when-cross-origin"
        )
        cabecalhos.setdefault(
            "permissions-policy", "geolocation=(), camera=(), microphone=()"
        )
        if getattr(self, "_https", False):
            cabecalhos.setdefault(
                "strict-transport-security", "max-age=31536000; includeSubDomains"
            )
        if getattr(self, "_privado", False):
            cabecalhos.setdefault("cache-control", "no-store")
        for nome, valor in cabecalhos.items():
            self.send_header(nome, valor)

    def _enviar(self, status, cabecalhos, corpo):
        self._iniciar_resposta(status, cabecalhos)
        self.send_header("content-length", str(len(corpo)))
        self.end_headers()
        if corpo and getattr(self, "command", "GET") != "HEAD":
            try:
                self.wfile.write(corpo)
            except ConnectionError:
                pass

    def _enviar_arquivo(self, status, cabecalhos, arquivo, inicio, tamanho):
        """Envia um trecho de arquivo em blocos, sem carregar tudo na memória."""
        self._iniciar_resposta(status, cabecalhos)
        self.send_header("content-length", str(tamanho))
        self.end_headers()
        if getattr(self, "command", "GET") == "HEAD" or tamanho <= 0:
            return

        restante = tamanho
        try:
            with open(arquivo, "rb") as aberto:
                aberto.seek(inicio)
                while restante > 0:
                    bloco = aberto.read(min(65536, restante))
                    if not bloco:
                        break
                    self.wfile.write(bloco)
                    restante -= len(bloco)
        except ConnectionError:
            return

    def log_message(self, formato, *args):
        print("[{}] {}".format(self.log_date_time_string(), formato % args))


def main():
    problemas = config.avisos_de_prod()
    if problemas:
        raise SystemExit(
            "Configuração insegura para servidor exposto:\n- "
            + "\n- ".join(problemas)
        )
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
