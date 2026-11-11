"""Ponte SSH/SCP para a VM de deploy (paramiko).

Uso:
    python tools/vm.py run "comando"
    python tools/vm.py sudo "comando"
    python tools/vm.py put arquivo_local /caminho/remoto
    python tools/vm.py get /caminho/remoto arquivo_local

Credenciais por variável de ambiente (ou padrão do projeto):
    VM_HOST=127.0.0.1 VM_USER=melque VM_PASS=...
"""

import os
import sys

import paramiko

HOST = os.getenv("VM_HOST", "127.0.0.1")
PORTA = int(os.getenv("VM_PORT", "22"))
USUARIO = os.getenv("VM_USER", "melque")
SENHA = os.getenv("VM_PASS", "")
CHAVE = os.getenv("VM_KEY", "")


def _cliente() -> paramiko.SSHClient:
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    parametros = dict(
        hostname=HOST,
        port=PORTA,
        username=USUARIO,
        timeout=15,
        banner_timeout=20,
        auth_timeout=20,
    )
    if CHAVE:
        parametros["key_filename"] = os.path.expanduser(CHAVE)
    else:
        parametros["password"] = SENHA
    cliente.connect(**parametros)
    return cliente


def run(comando: str, senha_sudo: str = None) -> int:
    """Executa um comando e imprime saída/erro; devolve o código de saída."""
    with _cliente() as cliente:
        if senha_sudo:
            comando = "sudo -S -p '' bash -lc {}".format(_aspas(comando))
            entrada, saida, erro = cliente.exec_command(comando, get_pty=True)
            entrada.write(senha_sudo + "\n")
            entrada.flush()
        else:
            entrada, saida, erro = cliente.exec_command(
                "bash -lc {}".format(_aspas(comando))
            )
        for linha in iter(saida.readline, ""):
            sys.stdout.write(linha)
        mensagem_erro = erro.read().decode("utf-8", "replace")
        if mensagem_erro:
            sys.stderr.write(mensagem_erro)
        return saida.channel.recv_exit_status()


def _aspas(texto: str) -> str:
    return "'" + texto.replace("'", "'\"'\"'") + "'"


def put(origem: str, destino: str) -> None:
    with _cliente() as cliente:
        with cliente.open_sftp() as sftp:
            try:
                sftp.put(origem, destino)
            except IOError:
                pasta = os.path.dirname(destino)
                cliente.exec_command("mkdir -p " + _aspas(pasta))
                sftp.put(origem, destino)


def get(origem: str, destino: str) -> None:
    with _cliente() as cliente:
        with cliente.open_sftp() as sftp:
            sftp.get(origem, destino)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    acao = argv[1]
    if acao == "run":
        return run(argv[2])
    if acao == "sudo":
        return run(argv[2], senha_sudo=SENHA)
    if acao == "put":
        put(argv[2], argv[3])
        return 0
    if acao == "get":
        get(argv[2], argv[3])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
