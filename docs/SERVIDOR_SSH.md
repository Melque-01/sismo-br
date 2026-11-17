# Estado atual do sistema (13/11/2026)

Este é o runbook do ambiente que está servindo o site agora.

> **Nota:** host, usuário e paths reais ficam em `docs/LOCAL_NOTAS.md`
> (arquivo local, fora do Git). Este documento usa os placeholders
> `<host-do-servidor>` e `<usuario>`.

## O que é esse host

| Item | Valor |
|---|---|
| Host | `<usuario>@<host-do-servidor>` porta `2222` (chave SSH) |
| Sistema | Ubuntu 24.04.5 LTS, **container** (PID 1 = sshd) |
| Recursos observados | 7,7 GB RAM; disco de 58 GB (43 GB livres na última checagem) |
| Python | 3.12.3; venv em `/home/<usuario>/sismos-br/.venv` |
| PostgreSQL / PostGIS | PostgreSQL 16.15 / PostGIS 3.4.2 |
| Limitações | sem systemd; Docker CLI instalado, mas daemon/container bloqueado por falta de namespaces/permissões |
| Acesso | `sudo` sem senha para o usuário `<usuario>` |

## O que está rodando

| Componente | Como |
|---|---|
| PostgreSQL 16 + PostGIS 3.4 | cluster `16/main`, iniciado com `pg_ctlcluster` |
| Aplicação | `/home/<usuario>/sismos-br`, venv, `python app.py` na 8080 |
| Túnel público | binário `cloudflared`, `--protocol http2`, log em `tunnel.log` |

- URL pública estável: `https://sismos-br.duckdns.org` (nginx + TLS no host).
- Banco: `sismos_br`, usuário `sismos_br`, senha em `/home/<usuario>/sismos-br/.env` (modo 600).
- Dados: **5.141 eventos** (5.044 SISBRA + 97 FDSN), 27 UFs, 0 fora da malha.
- Endpoint local no host: `http://127.0.0.1:8080`; acesso público é pelo túnel.
- Portas do banco (5432) não são publicadas pelo túnel.

Fluxo das requisições:

```text
navegador → Cloudflare Tunnel (HTTP/2) → cloudflared
         → http://127.0.0.1:8080 → app.py → PostgreSQL/PostGIS local
```

## Login e cadastro

- Contas ficam na tabela `usuarios` (e-mail único, hash PBKDF2-HMAC-SHA256 com
  salt por usuário).
- O site tem auto-cadastro em `/registrar`; depois de criar, o usuário já entra.
- O primeiro usuário é criado no boot a partir de `LOGIN_EMAIL`/`LOGIN_SENHA`
  do `.env` **somente quando a tabela está vazia**. Depois disso, o `.env` não
  altera senhas existentes.
- Sessão em cookie assinado, validade de 12 h (`SESSION_TTL`).
- 5 tentativas de login erradas por IP em 5 minutos bloqueiam temporariamente;
  cadastro limitado a 10 tentativas por IP por hora.
- Para trocar a senha de um usuário, atualize o hash na tabela (ou apague a
  conta e cadastre de novo).

## Comandos

```bash
# estado
ssh -p 2222 <usuario>@<host-do-servidor>
cd /home/<usuario>/sismos-br
bash scripts/status_servidor.sh

# iniciar qualquer componente parado (banco, app, túnel)
bash /home/<usuario>/sismos-br/scripts/start_servidor.sh

# reiniciar app e túnel se necessário
pkill -f '[p]ython app.py' || true
pkill -f '[c]loudflared tunnel' || true
bash /home/<usuario>/sismos-br/scripts/start_servidor.sh

# atualizar só o FDSN
cd /home/<usuario>/sismos-br
.venv/bin/python scripts/importar_catalogo.py --somente fdsn

# logs
tail -f /home/<usuario>/sismos-br/app.log
tail -f /home/<usuario>/sismos-br/tunnel.log

# backup do banco (cria arquivo na home do usuário)
cd /home/<usuario>/sismos-br
set -a; . ./.env; set +a
PGPASSWORD="$DB_PASSWORD" pg_dump -h 127.0.0.1 -U sismos_br -Fc sismos_br \
  > "$HOME/sismos_br_$(date +%F).dump"
```

## Vídeos da página "Saiba mais"

Os MP4s não entram no Git. Depois de gerar ou atualizar:

```bash
scp -P 2222 static/videos/*.mp4 static/videos/*.vtt static/videos/*.jpg \
  <usuario>@<host-do-servidor>:/home/<usuario>/sismos-br/static/videos/
```

O app serve `/static/videos/...` com suporte a `Range`, então o player
consegue buscar e avançar sem baixar o arquivo inteiro.

## Limitação importante

O host não tem systemd: **se o container/host reiniciar, PostgreSQL, app e túnel
não sobem sozinhos**. Depois de qualquer reinício, entre por SSH e rode:

```bash
bash /home/<usuario>/sismos-br/scripts/start_servidor.sh
```

### Subida automática (wrapper do sshd)

Desde 12/11/2026, `/usr/sbin/sshd` no container é um wrapper: no boot ele roda
`start_servidor.sh` como `<usuario>` (log em `/home/<usuario>/sismos-br/boot.log`) e
depois exec o sshd real (`/usr/sbin/sshd.real`). Ou seja: **os serviços sobem
sozinhos quando o container reinicia** — o manual acima virou fallback. A URL
do túnel rápido ainda muda a cada subida; consulte `boot.log` ou o
`status_servidor.sh` para a URL atual.

### Acesso SSH

SSH no container exige **chave** (`PasswordAuthentication no`, `X11Forwarding
no`, `AllowUsers <usuario>`). Os drop-ins ficam em `/etc/ssh/sshd_config.d/`
(`00-<usuario>-password.conf`, `99-<usuario>.conf`), com backup em
`/home/<usuario>/ssh-backup/`. O `sudo` do `<usuario>` segue sem senha porque
`start_servidor.sh` precisa dele.

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
