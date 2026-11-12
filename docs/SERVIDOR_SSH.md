# Estado atual do sistema (12/11/2026)

Este é o runbook do ambiente que está servindo o site agora.

## O que é esse host

| Item | Valor |
|---|---|
| Host | `melque@<host-do-servidor>` porta `2222` (chave SSH) |
| Sistema | Ubuntu 24.04.5 LTS, **container** (PID 1 = sshd) |
| Recursos observados | 7,7 GB RAM; disco de 58 GB (43 GB livres na última checagem) |
| Python | 3.12.3; venv em `/home/melque/sismos-br/.venv` |
| PostgreSQL / PostGIS | PostgreSQL 16.15 / PostGIS 3.4.2 |
| Limitações | sem systemd; Docker CLI instalado, mas daemon/container bloqueado por falta de namespaces/permissões |
| Acesso | `sudo` sem senha para o usuário `melque` |

## O que está rodando

| Componente | Como |
|---|---|
| PostgreSQL 16 + PostGIS 3.4 | cluster `16/main`, iniciado com `pg_ctlcluster` |
| Aplicação | `/home/melque/sismos-br`, venv, `python app.py` na 8080 |
| Túnel público | binário `cloudflared`, `--protocol http2`, log em `tunnel.log` |

- URL pública atual: `<tunel-efemero>`
- Banco: `sismos_br`, usuário `sismos_br`, senha em `/home/melque/sismos-br/.env` (modo 600).
- Dados: **5.141 eventos** (5.044 SISBRA + 97 FDSN), 27 UFs, 0 fora da malha.
- Endpoint local no host: `http://127.0.0.1:8080`; acesso público é pelo túnel.
- Portas do banco (5432) não são publicadas pelo túnel.

Fluxo das requisições:

```text
navegador → Cloudflare Tunnel (HTTP/2) → cloudflared
         → http://127.0.0.1:8080 → app.py → PostgreSQL/PostGIS local
```

## Login

- E-mail atual: `melque@sismos.br`.
- A senha e o segredo de sessão ficam em `/home/melque/sismos-br/.env`
  (`LOGIN_EMAIL`, `LOGIN_SENHA`, `SESSION_SECRET`), modo 600.
- Sessão em cookie assinado, validade de 12 h (`SESSION_TTL`).
- 5 tentativas erradas por IP em 5 minutos bloqueiam temporariamente.
- Para trocar a senha: edite o `.env` e reinicie apenas o app
  (`pkill -f '[p]ython app.py'` e rode o `start_servidor.sh`).

## Comandos

```bash
# estado
ssh -p 2222 melque@<host-do-servidor>
cd /home/melque/sismos-br
bash scripts/status_servidor.sh

# iniciar qualquer componente parado (banco, app, túnel)
bash /home/melque/sismos-br/scripts/start_servidor.sh

# reiniciar app e túnel se necessário
pkill -f '[p]ython app.py' || true
pkill -f '[c]loudflared tunnel' || true
bash /home/melque/sismos-br/scripts/start_servidor.sh

# atualizar só o FDSN
cd /home/melque/sismos-br
.venv/bin/python scripts/importar_catalogo.py --somente fdsn

# logs
tail -f /home/melque/sismos-br/app.log
tail -f /home/melque/sismos-br/tunnel.log

# backup do banco (cria arquivo na home do usuário)
cd /home/melque/sismos-br
set -a; . ./.env; set +a
PGPASSWORD="$DB_PASSWORD" pg_dump -h 127.0.0.1 -U sismos_br -Fc sismos_br \
  > "$HOME/sismos_br_$(date +%F).dump"
```

## Limitação importante

O host não tem systemd: **se o container/host reiniciar, PostgreSQL, app e túnel
não sobem sozinhos**. Depois de qualquer reinício, entre por SSH e rode:

```bash
bash /home/melque/sismos-br/scripts/start_servidor.sh
```

A URL do túnel rápido muda quando `cloudflared` reinicia; o script imprime a
nova URL no final. Atualize o link salvo se o túnel tiver sido reiniciado.

## Docker: status neste host

O sistema **não está rodando em Docker neste host**. O Docker CLI foi instalado,
mas o servidor é um container sem `CAP_SYS_ADMIN`; o daemon não cria a rede
bridge (`operation not permitted`) e `docker run` falha ao registrar camada
(`unshare: operation not permitted`). Copiar a imagem não remove essa
restrição.

A stack Compose foi construída, testada e depois parada no Docker Desktop local.
Para executá-la, use uma VM/servidor que permita Docker Engine + namespaces:

```bash
docker compose up -d --build
docker compose exec app python scripts/importar_catalogo.py
```

## Histórico

- A VM VirtualBox local (`ubunto`) sofreu kernel panic e foi desligada; não é
  mais usada.
- A imagem Docker existe no repositório e foi validada localmente, mas não está
  ativa nem hospedada em `<host-do-servidor>`.
- A atualização do FDSN é manual; não há timer semanal neste host.
