# Docker (stack validada; não é o deploy ativo)

> **Estado atual (12/11/2026):** o deploy ativo está em `<host-do-servidor>:2222`
> rodando nativamente, sem containers. A stack abaixo foi construída, testada
> no Docker Desktop local (PostGIS + importação + API) e parada depois. Não dá
> para rodá-la no host SSH atual: ele é um container sem permissões para
> namespaces/`unshare`. Use uma VM real com Docker Engine.

Stack com três containers:

| Serviço | Imagem | Função |
|---|---|---|
| `db` | `postgis/postgis:16-3.4` | PostgreSQL 16 + PostGIS, volume `pgdata` |
| `app` | build local (`Dockerfile`) | aplicação Python (`http.server`) na 8080 |
| `cloudflared` | `cloudflare/cloudflared` | túnel rápido público para o app |

Não esqueça de definir `LOGIN_EMAIL`, `LOGIN_SENHA` e `SESSION_SECRET` no `.env`;
sem eles ninguém consegue entrar no site.

## Requisitos do host

- Docker Engine + Compose plugin.
- Host com `systemd` (VM ou servidor dedicado). **Não funciona dentro de
  container sem privilégios** (sem `CAP_SYS_ADMIN`, sem systemd), como o
  servidor `<servidor>` em `<host-do-servidor>:2222`.

## Subir

```bash
cp .env.docker.example .env
# edite DB_PASSWORD (e APP_PORT se a 8080 estiver ocupada)
docker compose up -d --build
```

Aguardar `db` ficar healthy; o `app` só inicia depois.

## Importar os catálogos

```bash
docker compose exec app python scripts/importar_catalogo.py
```

Saída esperada: 5.141 eventos (5.044 SISBRA + 97 FDSN).

## URL pública

```bash
docker compose logs cloudflared | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -n1
```

A URL do túnel rápido muda quando o container `cloudflared` reinicia.

## Verificar

```bash
curl -s http://127.0.0.1:8080/api/status
docker compose ps
```

## Atualizar

```bash
git pull
docker compose up -d --build
```

## Backup

```bash
docker compose exec db pg_dump -U sismos_br -Fc sismos_br > sismos_br_$(date +%F).dump
```

## Parar

```bash
docker compose down          # mantém o volume
docker compose down -v       # apaga também o banco
```

## Imagem só da aplicação

```bash
docker build -t sismos-br-app .
docker run --rm -p 8080:8080 \
  -e DB_HOST=host-do-banco -e DB_PASSWORD=... sismos-br-app
```

Variáveis lidas pela aplicação: `HOST`, `PORTA`, `DB_HOST`, `DB_PORT`,
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `LOGIN_EMAIL`, `LOGIN_SENHA`,
`SESSION_SECRET`.
