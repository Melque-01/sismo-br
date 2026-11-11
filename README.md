# Sismos BR — densidade de epicentros no Brasil

Trabalho de faculdade: mapa interativo da densidade de epicentros no território
brasileiro a partir do catálogo histórico do **SISBRA/RSBR** (1690–2023) e do
catálogo **FDSN do Moho/IAG-USP** (2024 em diante).

Aplicação em **Python puro, no padrão MVC, sem framework web** — mesma
arquitetura do projeto Geo Buss. Roda em uma VM Ubuntu Server e é publicada por
**Cloudflare Tunnel**.

## O que o site faz

- Grade de densidade com célula de 0,25°, 0,5°, 1° ou 2°.
- Duas métricas: contagem de eventos e eventos por 1.000 km² (normalizada).
- Filtros por período, magnitude, profundidade, fonte, UF e categoria SISBRA.
- Camada alternativa de mapa de calor (pontos individuais).
- Clique numa célula lista os eventos e abre a ficha completa de cada um.
- Painel com total, período, maior magnitude, top UFs, série anual, histograma
  de magnitudes e cobertura dos dados.
- Estado dos filtros fica na URL (link compartilhável).

## Arquitetura

```
navegador
   │  HTML/CSS/JS (Leaflet + leaflet.heat + Chart.js)
   ▼
app.py  ── http.server.ThreadingHTTPServer
   │  (método, caminho) → função
   ▼
rotas/rotas.py
   │
   ▼
controles/            validação dos filtros, respostas JSON/HTML
   │
   ▼
modelo/               SQL parametrizado, upsert, consultas espaciais
   │
   ▼
PostgreSQL 18 + PostGIS 3.6   (grade via floor()/ST_MakeEnvelope)
```

A importação é offline do ponto de vista da requisição: um CLI baixa os
catálogos, normaliza e grava no banco; o site só lê o banco.

## Estrutura de pastas

```
app.py                 servidor HTTP e entrega de estáticos
config.py              configuração (lê .env), constantes e recorte do Brasil
rotas/                 tabela (método, caminho) → controller
controles/             home, validação de filtros, API, helpers de resposta
modelo/                sismos (upsert + consultas) e log de importações
servicos/              parsers SISBRA/FDSN, mapa codarea→UF, estatística
db/                    schema.sql e acesso ao Postgres (psycopg 3)
scripts/               importação e scripts de deploy/verificação da VM
deploy/                units systemd e timer de atualização
templates/, static/    interface (HTML, CSS, JS)
docs/                  dados, deploy e estado da VM
tests/                 testes unitários + integração (SISMOS_TESTAR_DB=1)
tools/vm.py            ponte SSH/SCP (paramiko) para a VM
```

## API

Todos os endpoints aceitam os filtros `ano_ini`, `ano_fim`, `mag_min`,
`mag_max`, `prof_max`, `fonte` (`todas|SISBRA|FDSN`), `uf`, `categoria` e
`celula` (0.25, 0.5, 1, 2). A validação é central e erro de filtro responde 400.

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | página com mapa e painel |
| GET | `/api/densidade` | células GeoJSON com contagem, densidade, cortes de cor |
| GET | `/api/sismos` | pontos GeoJSON para o mapa de calor (limite 6.000, teto 20.000) |
| GET | `/api/celula?lat=&lon=` | eventos da célula clicada |
| GET | `/api/evento?id=` | ficha completa do evento |
| GET | `/api/estatisticas` | total, período, maior evento, top UFs, série anual, histograma |
| GET | `/api/filtros` | opções reais do banco para os selects |
| GET | `/api/status` | saúde do banco, contagem por fonte, última importação |
| GET | `/api/importacoes` | últimas execuções do importador |

## Rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
copy .env.example .env        # ajuste DB_HOST/DB_PASSWORD
python app.py
```

No Linux:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python app.py
```

O app sobe mesmo sem banco (a página abre e a API responde 503 com mensagem em
português). Para carregar os dados é preciso um PostGIS acessível.

## Importar os catálogos

```bash
python scripts/importar_catalogo.py               # SISBRA + FDSN
python scripts/importar_catalogo.py --somente fdsn
python scripts/importar_catalogo.py --sem-baixar  # usa dados/brutos
```

O upsert por `(fonte, evento_id)` torna a reimportação idempotente. Eventos fora
da malha do IBGE são removidos depois da carga.

## Testes

```bash
python -m unittest discover -s tests -v
```

Testes de banco são pulados por padrão; na VM:

```bash
SISMOS_TESTAR_DB=1 python -m unittest discover -s tests -v
```

## Estado atual da publicação

- VM Ubuntu Server 26.04 no VirtualBox, rede NAT (SSH `127.0.0.1:2222`), usuário `melque`.
- Serviço `sismos-br` em `http://127.0.0.1:8080` (a porta 80 já é usada pelo
  projeto Geo Buss).
- Túnel rápido: `<tunel-efemero>`
  (URL temporária - muda se o serviço/túnel reiniciar).
- Base: **5.141 eventos** no recorte do Brasil (5.044 SISBRA + 97 FDSN).

Detalhes em [docs/DADOS.md](docs/DADOS.md),
[docs/DEPLOY_VM.md](docs/DEPLOY_VM.md) e
[docs/AMBIENTE_VM.md](docs/AMBIENTE_VM.md).

## Decisões e limitações

- **Só território brasileiro**: filtro pela malha do IBGE (27 UFs). Eventos
  andinos ou oceânicos que aparecem no recorte são descartados.
- **Hora local do SISBRA**: registros com sufixo `L` são convertidos de UTC−3
  para UTC; sem hora, `data_hora` fica nula (o ano é preservado).
- **Coordenadas históricas arredondadas**: eventos antigos vêm em graus
  fechados (ex.: `-3,00 / -60,00`), então a célula mostra a precisão do
  catálogo, não a do epicentro real.
- **Viés de rede**: a partir de ~1980 o número de estações cresce muito; a
  série anual mede detecção, não necessariamente atividade sísmica.
- **Densidade normalizada**: a área de cada célula é calculada em km² pelo
  PostGIS (`geography`), por isso células em latitudes diferentes são
  comparáveis.
- **Célula clicada**: o evento pertence à célula cujo canto é
  `floor(coord / célula) * célula`; é a mesma conta usada na agregação.
- **Catálogo SISBRA até 2023 + FDSN de 2024 em diante**, sem sobreposição.
- **Túnel rápido da Cloudflare** é adequado para demonstração; para um link
  fixo é preciso um túnel nomeado (ver `docs/DEPLOY_VM.md`).
