# Dados e metodologia

## Fontes

| Fonte | O que é | Onde | Recorte usado |
|---|---|---|---|
| SISBRA/RSBR | Catálogo histórico e instrumental brasileiro (CSUSP/IAG-USP) | `https://seiscode.iag.usp.br/CSUSP/sisbra/raw/branch/master/catalogo_RAW.dat` | até 2023 |
| FDSN Moho/IAG-USP | Serviço FDSN de eventos (texto separado por `|`) | `http://www.moho.iag.usp.br/fdsnws/event/1/query` | a partir de 2024-01-01 |
| Malha do IBGE | Limite das 27 UFs | API de malhas do IBGE (`qualidade=minima`, `intrarregiao=UF`) | versão em `dados/brasil_uf.geojson` |

Os dois catálogos não se sobrepõem: o SISBRA é usado até 2023 e o FDSN cobre de
2024 em diante. A data de corte fica em `config.FDSN_DESDE`.

## Formato do SISBRA

Arquivo texto em colunas fixas, com cabeçalho `#_ano_mmdd_hhmmss.s_latit_longit...`.
O parser lê as colunas do cabeçalho e tem um fallback para linhas deslocadas
(hora com fração de segundo, latitude/longitude de largura variável).

Regras de normalização:

- `mmdd` e `hora` incompletos (`----`, `06--`) não viram data inventada.
- Hora com sufixo `L` é hora local (UTC−3) e é convertida para UTC; sem `L`, a
  hora já é UTC.
- `magnitude` fica nula quando o tipo (`tm`) é `-1` ou o valor é `0.0`.
- `profundidade_km` fica nula quando o campo é `0`, `0.` ou vazio.
- `uf` vem da coluna de 2 letras; o evento só entra no banco se a UF for uma das
  27 do Brasil.
- `evento_id` = md5 de `ano|mmdd|hora|lat|lon|mag` (o arquivo não tem id).
- Linhas sem coordenada ou fora do recorte (`lat` em [-34, 6], `lon` em
  [-74, -34]) são descartadas.

## Formato do FDSN

CSV com `|`, uma linha de cabeçalho começando com `#EventID`. O parser mantém
somente `EventType = earthquake` e anexa UTC às datas (o serviço não manda
offset). A UF é extraída do fim de `EventLocationName` quando existe `/UF`.

O filtro geográfico **não** é feito no parser: o serviço devolve Chile,
Argentina, Bolívia e oceano no recorte retangular. Depois do upsert, o
importador apaga da fonte o que não está dentro da malha do IBGE
(`ST_Contains`).

## Grade e métricas

- A célula é alinhada à origem: `x0 = floor(lon / célula) * célula` e o mesmo
  para a latitude. A célula que contém o ponto é a mesma na agregação e no
  clique.
- `contagem`: número de eventos na célula.
- `normalizada`: eventos por 1.000 km², com a área calculada pelo PostGIS em
  `geography` (km² reais, não graus).
- Cortes de cor: quantis por posto (20/40/60/80%) calculados sobre os valores
  das células. Cinco classes; valores repetidos geram menos cortes, nunca
  cortes duplicados. Consulta vazia devolve `cortes: []`.

## Contagens atuais (novembro/2026)

| Fonte | Linhas lidas | Importadas | Descartadas |
|---|---|---|---|
| SISBRA | 5.934 | 5.044 | 889 |
| FDSN | 1.420 | 97 | 1.323 |
| **Total** | — | **5.141** | — |

> O log da importação do SISBRA conta 5.045 processados; o banco tem 5.044
> linhas porque o catálogo traz um evento duplicado e o upsert mantém uma.

- 889 descartes do SISBRA: linhas sem coordenada, sem UF brasileira e eventos
  fora da malha do IBGE (por exemplo, registros com UF na coluna mas coordenada
  no Atlântico ou no Peru).
- 1.323 descartes do FDSN: eventos de países vizinhos e oceano dentro do
  retângulo consultado.

## Limitações

- **Precisão histórica**: eventos anteriores à instrumentação vêm em graus
  fechados. Uma célula de 0,5° mostra a posição do catálogo, não a incerteza
  real do epicentro.
- **Viés de detecção**: a rede cresce muito a partir de 1980; a série anual
  mede quantos eventos foram detectados e registrados, não a atividade sísmica
  absoluta.
- **Magnitude heterogênea**: os tipos (`mR`, `mb`, `-1`, ...) vêm das fontes e
  não foram convertidos; comparar magnitudes entre épocas exige cautela.
- **Profundidade rara**: no SISBRA a profundidade existe em uma minoria dos
  registros; no painel, a cobertura mostra esse percentual.
- **Sem sobreposição de fontes**, mas o FDSN pode reprocessar eventos antigos;
  por isso o importador usa `starttime=2024-01-01`.

## Reimportar

Na VM:

```bash
cd /opt/sismos-br
.venv/bin/python scripts/importar_catalogo.py
```

Só a atualização recente:

```bash
.venv/bin/python scripts/importar_catalogo.py --somente fdsn
```

O `sismos-atualizar.timer` roda esse comando semanalmente. O log de cada
execução fica na tabela `importacoes` e aparece em `/api/importacoes`.
