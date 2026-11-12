# Servidor SSH (<host-do-servidor>:2222)

Segundo ambiente de produção do trabalho, usado enquanto a VM local e o Google
Cloud não estão disponíveis.

## O que é esse host

| Item | Valor |
|---|---|
| Host | `melque@<host-do-servidor>` porta `2222` (chave SSH) |
| Sistema | Ubuntu 24.04.5 LTS, **container** (PID 1 = sshd) |
| Recursos | 7,7 GB RAM, 58 GB de disco (45 GB livres) |
| Limitações | sem systemd, sem Docker (`unshare` bloqueado, sem `CAP_SYS_ADMIN`) |
| Acesso | `sudo` sem senha para o usuário `melque` |

## O que está rodando

| Componente | Como |
|---|---|
| PostgreSQL 16 + PostGIS 3.4 | cluster `16/main`, iniciado com `pg_ctlcluster` |
| Aplicação | `/home/melque/sismos-br`, venv, `python app.py` na 8080 |
| Túnel público | binário `cloudflared`, `--protocol http2`, log em `tunnel.log` |

- URL pública: `<tunel-efemero>`
- Banco: `sismos_br`, usuário `sismos_br`, senha em `/home/melque/sismos-br/.env` (modo 600).
- Dados: **5.141 eventos** (5.044 SISBRA + 97 FDSN), 27 UFs, 0 fora da malha.

## Comandos

```bash
# estado
bash /home/melque/sismos-br/scripts/status_servidor.sh

# religar tudo (app, banco e túnel)
bash /home/melque/sismos-br/scripts/start_servidor.sh

# atualizar só o FDSN
cd /home/melque/sismos-br
.venv/bin/python scripts/importar_catalogo.py --somente fdsn

# logs
tail -f /home/melque/sismos-br/app.log
tail -f /home/melque/sismos-br/tunnel.log
```

## Limitação importante

O container não tem systemd: **se ele reiniciar, nada sobe sozinho**. Depois de
qualquer reinício, rode:

```bash
bash /home/melque/sismos-br/scripts/start_servidor.sh
```

A URL do túnel rápido muda quando o `cloudflared` reinicia; o script imprime a
nova URL no final.

## Docker

Não roda neste host. A imagem do projeto (`Dockerfile` + `docker-compose.yml`)
foi construída e validada no Docker Desktop e está pronta para uma VM de
verdade (Google Cloud/Oracle) com:

```bash
docker compose up -d --build
docker compose exec app python scripts/importar_catalogo.py
```

## Backup do banco

```bash
pg_dump -h 127.0.0.1 -U sismos_br -Fc sismos_br > ~/sismos_br_$(date +%F).dump
```

## Histórico

- A VM VirtualBox local (`ubunto`) sofreu kernel panic e foi desligada; o
  ambiente dela está documentado em `docs/AMBIENTE_VM.md`.
- O deploy neste servidor foi feito sem Docker porque o host não permite
  namespaces; o PostgreSQL roda como processo do cluster local.
