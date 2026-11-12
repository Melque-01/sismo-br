# -*- coding: utf-8 -*-
"""Gera docs/Guia_Sismos_BR.pdf (guia técnico do projeto)."""

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "docs" / "assets"
SAIDA = RAIZ / "docs" / "Guia_Sismos_BR.pdf"

CORAL = colors.HexColor("#e85d4a")
CORAL_ESCURO = colors.HexColor("#b23a2b")
TINTA = colors.HexColor("#1c2430")
CINZA = colors.HexColor("#5b6775")
FUNDO_CODIGO = colors.HexColor("#f4f6f8")
BORDA = colors.HexColor("#d8dee6")
VERDE = colors.HexColor("#2f7d5b")

# --- Fontes -------------------------------------------------------------
FONTE = "Helvetica"
FONTE_NEGRITO = "Helvetica-Bold"
MONO = "Courier"

try:
    pdfmetrics.registerFont(TTFont("Segoe", r"C:\Windows\Fonts\segoeui.ttf"))
    pdfmetrics.registerFont(TTFont("Segoe-Bold", r"C:\Windows\Fonts\segoeuib.ttf"))
    pdfmetrics.registerFontFamily("Segoe", normal="Segoe", bold="Segoe-Bold")
    FONTE, FONTE_NEGRITO = "Segoe", "Segoe-Bold"
except Exception:  # noqa: BLE001 - Windows sem a fonte; usa a padrão
    pass

try:
    pdfmetrics.registerFont(TTFont("Consola", r"C:\Windows\Fonts\consola.ttf"))
    MONO = "Consola"
except Exception:  # noqa: BLE001
    pass

ESTILOS = getSampleStyleSheet()
TITULO = ParagraphStyle(
    "Titulo",
    parent=ESTILOS["Title"],
    fontName=FONTE_NEGRITO,
    fontSize=30,
    leading=34,
    textColor=TINTA,
    alignment=TA_LEFT,
    spaceAfter=10,
)
SUB = ParagraphStyle(
    "Sub",
    parent=ESTILOS["Normal"],
    fontName=FONTE,
    fontSize=13,
    leading=18,
    textColor=CINZA,
)
H1 = ParagraphStyle(
    "H1",
    parent=ESTILOS["Heading1"],
    fontName=FONTE_NEGRITO,
    fontSize=17,
    leading=21,
    textColor=CORAL_ESCURO,
    spaceBefore=18,
    spaceAfter=8,
)
H2 = ParagraphStyle(
    "H2",
    parent=ESTILOS["Heading2"],
    fontName=FONTE_NEGRITO,
    fontSize=12.5,
    leading=16,
    textColor=TINTA,
    spaceBefore=12,
    spaceAfter=5,
)
CORPO = ParagraphStyle(
    "Corpo",
    parent=ESTILOS["BodyText"],
    fontName=FONTE,
    fontSize=10,
    leading=14.5,
    textColor=TINTA,
    spaceAfter=6,
)
BULLET = ParagraphStyle(
    "Bullet",
    parent=CORPO,
    leftIndent=14,
    bulletIndent=4,
    spaceAfter=3,
)
LEGENDA = ParagraphStyle(
    "Legenda",
    parent=CORPO,
    fontSize=8.5,
    leading=11,
    textColor=CINZA,
    alignment=TA_CENTER,
    spaceBefore=3,
)
CODIGO = ParagraphStyle(
    "Codigo",
    parent=ESTILOS["Code"],
    fontName=MONO,
    fontSize=7.6,
    leading=9.8,
    textColor=TINTA,
    backColor=FUNDO_CODIGO,
    borderColor=BORDA,
    borderWidth=0.6,
    borderPadding=6,
    leftIndent=0,
    spaceBefore=4,
    spaceAfter=10,
)
CELULA = ParagraphStyle(
    "Celula", parent=CORPO, fontSize=8.4, leading=11, spaceAfter=0
)
CELULA_CAB = ParagraphStyle(
    "CelulaCab",
    parent=CELULA,
    fontName=FONTE_NEGRITO,
    textColor=colors.white,
)


def h1(texto):
    return Paragraph(texto, H1)


def h2(texto):
    return Paragraph(texto, H2)


def p(texto):
    return Paragraph(texto, CORPO)


def itens(lista):
    return [
        Paragraph(item, BULLET, bulletText="\u2022") for item in lista if item
    ]


def codigo(texto):
    return Preformatted(texto.strip("\n"), CODIGO, maxLineLength=110)


def tabela(cabecalho, linhas, larguras):
    dados = [[Paragraph(c, CELULA_CAB) for c in cabecalho]]
    for linha in linhas:
        dados.append([Paragraph(str(c), CELULA) for c in linha])
    tabela_ = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    tabela_.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TINTA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabela_


def imagem(caminho, largura_cm, legenda=None, max_altura_cm=17):
    caminho = Path(caminho)
    if not caminho.exists():
        return Spacer(1, 1)
    largura_px, altura_px = PILImage.open(caminho).size
    largura = largura_cm * cm
    altura = largura * altura_px / largura_px
    if altura > max_altura_cm * cm:
        altura = max_altura_cm * cm
        largura = altura * largura_px / altura_px
    partes = [Image(str(caminho), width=largura, height=altura)]
    if legenda:
        partes.append(Paragraph(legenda, LEGENDA))
    partes.append(Spacer(1, 8))
    return partes


def capa(canvas, doc):
    canvas.saveState()
    largura, altura = A4
    canvas.setFillColor(colors.HexColor("#0e141c"))
    canvas.rect(0, altura - 7.2 * cm, largura, 7.2 * cm, stroke=0, fill=1)
    canvas.setFillColor(CORAL)
    canvas.rect(0, altura - 7.5 * cm, largura, 0.3 * cm, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    canvas.setFont(FONTE_NEGRITO, 34)
    canvas.drawString(2.2 * cm, altura - 3.4 * cm, "Sismos BR")
    canvas.setFont(FONTE, 13)
    canvas.setFillColor(colors.HexColor("#c9d3df"))
    canvas.drawString(
        2.2 * cm,
        altura - 4.15 * cm,
        "Mapa de densidade de epicentros no Brasil",
    )
    canvas.setFont(FONTE, 10)
    canvas.drawString(
        2.2 * cm,
        altura - 5.0 * cm,
        "Guia técnico: dados, PostGIS, Python, login e Cloudflare Tunnel",
    )

    canvas.setFillColor(TINTA)
    canvas.setFont(FONTE_NEGRITO, 11)
    canvas.drawString(2.2 * cm, altura - 9.2 * cm, "O que este documento cobre")
    canvas.setFont(FONTE, 9.5)
    texto = [
        "1. Como os catálogos SISBRA e FDSN foram tratados",
        "2. Modelagem PostGIS, grade de densidade e consultas",
        "3. Backend MVC em Python puro e API JSON",
        "4. Login e cadastro com senha protegida",
        "5. Publicação com Cloudflare Tunnel (rápido e nomeado)",
        "6. Deploy em servidor sem systemd e alternativa Docker",
    ]
    y = altura - 10.0 * cm
    for linha in texto:
        canvas.drawString(2.2 * cm, y, linha)
        y -= 0.5 * cm

    canvas.setFont(FONTE, 8.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2.2 * cm, 2.6 * cm, "Versão de 12/11/2026")
    canvas.drawString(
        2.2 * cm,
        2.2 * cm,
        "Projeto acadêmico - não use para emergências ou decisões de risco.",
    )

    capa_img = ASSETS / "dashboard.png"
    if capa_img.exists():
        largura_img = 12.0 * cm
        altura_img = largura_img * 950 / 1440
        canvas.drawImage(
            str(capa_img),
            2.2 * cm,
            6.4 * cm,
            width=largura_img,
            height=altura_img,
            mask="auto",
        )
    canvas.restoreState()


def rodape(canvas, doc):
    canvas.saveState()
    largura, _ = A4
    canvas.setStrokeColor(BORDA)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, 1.45 * cm, largura - 2 * cm, 1.45 * cm)
    canvas.setFont(FONTE, 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2 * cm, 1.05 * cm, "Sismos BR - guia de construção")
    canvas.drawRightString(
        largura - 2 * cm, 1.05 * cm, "Página {}".format(doc.page)
    )
    canvas.restoreState()


historia = []
historia.append(PageBreak())

# --- 1 -------------------------------------------------------------------
historia.append(h1("1. Visão geral"))
historia.append(
    p(
        "O Sismos BR é um site que mostra onde os terremotos registrados no Brasil "
        "se concentram. Ele lê dois catálogos científicos, normaliza os eventos, "
        "grava tudo em PostgreSQL com PostGIS e desenha uma grade de densidade "
        "sobre o mapa. O usuário filtra por período, magnitude, profundidade, "
        "fonte, UF e categoria; clica numa célula e vê os eventos que a formaram."
    )
)
historia.append(
    p(
        "A base atual tem 5.141 eventos entre 1690 e 2026: 5.044 do SISBRA/RSBR "
        "(catálogo histórico brasileiro) e 97 do serviço FDSN do Moho/IAG-USP "
        "(2024 em diante). O site exige login e permite que novas contas sejam "
        "criadas em /registrar."
    )
)
historia.append(h2("Principais decisões"))
historia.extend(
    itens(
        [
            "Python puro com http.server, no padrão MVC, sem Flask/Django.",
            "PostGIS como motor das consultas espaciais e da grade.",
            "Catálogo SISBRA até 2023 e FDSN de 2024 em diante, sem sobreposição.",
            "Somente eventos dentro da malha do IBGE (27 UFs).",
            "Grade alinhada à origem: floor(coordenada / célula) * célula.",
            "Publicação por Cloudflare Tunnel, sem abrir porta no roteador.",
            "Login com senha em PBKDF2 e sessão em cookie assinado.",
        ]
    )
)

# --- 2 -------------------------------------------------------------------
historia.append(h1("2. Arquitetura"))
historia.append(
    p(
        "O navegador conversa com um único processo Python. O processo serve os "
        "arquivos estáticos, valida filtros nos controllers, executa SQL "
        "parametrizado nos models e devolve JSON ou HTML. O banco guarda os "
        "eventos, a malha das UFs, o log de importações e as contas de usuário."
    )
)
historia.append(
    codigo(
        """
navegador (Leaflet + Chart.js)
      |
      v
app.py  (http.server.ThreadingHTTPServer)
      |  (metodo, caminho) -> funcao
      v
rotas/rotas.py
      |
      v
controles/   validacao, login, respostas HTML/JSON
      |
      v
modelo/      SQL parametrizado, upsert, consultas espaciais
      |
      v
PostgreSQL 16 + PostGIS 3.4
"""
    )
)
historia.append(h2("Fluxo de uma requisição"))
historia.extend(
    itens(
        [
            "app.py lê a query string, o corpo do POST e os cookies.",
            "A rota é localizada em ROTAS; rotas privadas exigem sessão válida.",
            "O controller valida os filtros e chama o model.",
            "O model monta o WHERE com %s e executa via psycopg 3.",
            "A resposta volta como (status, cabeçalhos, corpo) e o servidor envia.",
        ]
    )
)
historia.append(
    tabela(
        ["Camada", "Responsabilidade", "Exemplos"],
        [
            ["rotas", "Mapear método + caminho para uma função", "GET /api/densidade"],
            ["controles", "Validar entrada, decidir status, montar resposta", "montar_filtros, login"],
            ["modelo", "SQL, upsert, agregações", "densidade(), estatisticas()"],
            ["servicos", "Parsers, sessão, hash, estatística pura", "ler_sisbra(), senhas.py"],
            ["db", "Conexão e schema", "database.py, schema.sql"],
        ],
        [3.2 * cm, 7.4 * cm, 6.4 * cm],
    )
)

# --- 3 -------------------------------------------------------------------
historia.append(h1("3. Estrutura de pastas"))
historia.append(
    codigo(
        """
app.py                 servidor HTTP e estaticos
config.py              .env, constantes, recorte do Brasil
rotas/rotas.py         tabela de rotas
controles/             auth, home, sismos, respostas
modelo/                sismo.py, usuario.py, importacao.py
servicos/              catalogo.py, geografia.py, estatistica.py,
                       sessoes.py, senhas.py
db/                    schema.sql e database.py
templates/             index.html, login.html, registrar.html
static/                css/style.css, js/mapa.js
scripts/               importar, criar banco, start/status do servidor
tests/                 testes unitarios e de integracao
tools/vm.py            SSH/SCP via paramiko
docs/                  dados, servidor, Docker e este guia
"""
    )
)
historia.append(
    p(
        "O servidor de produção mantém apenas o runtime: app.py, config.py, "
        "controles, modelo, servicos, db, rotas, templates, static, requirements, "
        ".env, dados/brasil_uf.geojson e os scripts de importação e operação."
    )
)

# --- 4 -------------------------------------------------------------------
historia.append(h1("4. Banco de dados e modelo espacial"))
historia.append(h2("Tabelas"))
historia.append(
    tabela(
        ["Tabela", "Para que serve", "Destaques"],
        [
            ["sismos", "eventos normalizados", "geom Point 4326, UNIQUE(fonte, evento_id), índices GIST/ano/magnitude"],
            ["estados", "malha do IBGE", "codarea, uf, geom MultiPolygon, índice GIST"],
            ["importacoes", "log de cada carga", "contagens, início/fim, erro"],
            ["usuarios", "contas do site", "email UNIQUE, senha_hash PBKDF2, criado_em"],
        ],
        [2.7 * cm, 4.6 * cm, 9.7 * cm],
    )
)
historia.append(h2("Por que PostGIS"))
historia.append(
    p(
        "A malha das UFs é usada para descartar eventos fora do Brasil com "
        "ST_Contains. A grade é calculada no SQL com floor(), e a área de cada "
        "célula é medida em geography para que a densidade por 1.000 km2 seja "
        "comparável entre latitudes. O índice GIST acelera clique em célula e "
        "filtro geográfico."
    )
)
historia.append(
    codigo(
        """
-- célula alinhada à origem
ST_SetSRID(ST_MakePoint(
    floor(ST_X(geom) / %s) * %s,
    floor(ST_Y(geom) / %s) * %s
), 4326) AS celula

-- área real da célula em km2
ST_Area(ST_MakeEnvelope(x, y, x + %s, y + %s, 4326)::geography) / 1000000.0
"""
    )
)
historia.append(
    p(
        "O schema é aplicado no boot com CREATE TABLE IF NOT EXISTS. O script "
        "create_db.sh cria o papel, o banco e a extensão PostGIS, aplica o schema "
        "e transfere as tabelas para o usuário da aplicação."
    )
)

# --- 5 -------------------------------------------------------------------
historia.append(h1("5. Dados: SISBRA, FDSN e IBGE"))
historia.append(
    tabela(
        ["Fonte", "Formato", "Uso"],
        [
            ["SISBRA/RSBR", "texto em colunas fixas", "eventos até 2023"],
            ["FDSN Moho/IAG-USP", "CSV separado por |", "eventos de 2024 em diante"],
            ["IBGE", "GeoJSON da malha", "limite das 27 UFs"],
        ],
        [3.4 * cm, 4.8 * cm, 8.8 * cm],
    )
)
historia.append(h2("SISBRA"))
historia.extend(
    itens(
        [
            "Colunas lidas por fatia fixa (ano, mmdd, hora, latitude, longitude, UF, profundidade, magnitude, tipo, categoria, localidade, autor).",
            "Hora com sufixo L é local (UTC-3) e é convertida para UTC; sem hora, data_hora fica nula.",
            "Magnitude nula quando o tipo é -1 ou o valor é 0.0; profundidade nula quando é 0.",
            "Há fallback para linhas desalinhadas (hora com fração de segundo e coordenadas de largura variável).",
            "O parser valida sinal e limites das coordenadas; latitude positiva inesperada é descartada.",
        ]
    )
)
historia.append(h2("FDSN"))
historia.extend(
    itens(
        [
            "Consulta format=text, starttime=2024-01-01, eventtype=earthquake e bbox do Brasil.",
            "O serviço devolve também Chile, Argentina, Bolívia e oceano: o filtro real é feito depois, por ST_Contains.",
            "A UF sai do sufixo /UF do EventLocationName, quando existe.",
            "O parser anexa UTC às datas, porque o serviço não manda offset.",
        ]
    )
)
historia.append(h2("Contagens da carga atual"))
historia.append(
    tabela(
        ["Fonte", "Linhas lidas", "Importadas", "Descartadas"],
        [
            ["SISBRA", "5.934", "5.044", "889"],
            ["FDSN", "1.420", "97", "1.323"],
            ["Total", "-", "5.141", "-"],
        ],
        [4 * cm, 4 * cm, 4 * cm, 4 * cm],
    )
)
historia.append(
    p(
        "Os descartes são, em sua maioria, eventos sem coordenada, sem UF "
        "brasileira ou fora da malha do IBGE. O upsert por (fonte, evento_id) "
        "torna a reimportação idempotente: rodar de novo não duplica."
    )
)

# --- 6 -------------------------------------------------------------------
historia.append(h1("6. Grade, densidade e estatística"))
historia.extend(
    itens(
        [
            "Células permitidas: 0.25, 0.5, 1 e 2 graus (0.5 padrão).",
            "Contagem: número de eventos por célula.",
            "Normalizada: eventos por 1.000 km2, usando a área geográfica da célula.",
            "Cortes de cor: quantis por posto (20/40/60/80%), sem duplicatas.",
            "Consulta vazia devolve total 0 e cortes vazios, sem erro 500.",
        ]
    )
)
historia.append(
    p(
        "O clique numa célula usa exatamente a mesma conta floor() da agregação. "
        "Assim, a lista de eventos da célula sempre fecha com o número que o "
        "mapa mostrou."
    )
)
historia.append(h2("Estatísticas do painel"))
historia.append(
    p(
        "Total, período, maior magnitude, top 10 UFs, série anual, histograma de "
        "magnitudes, mediana de profundidade e percentual de eventos com "
        "magnitude/profundidade preenchidos."
    )
)

# --- 7 -------------------------------------------------------------------
historia.append(h1("7. API e validação"))
historia.append(
    tabela(
        ["Rota", "Resposta"],
        [
            ["GET /", "mapa + painel (exige login)"],
            ["GET /api/densidade", "FeatureCollection de células + cortes"],
            ["GET /api/sismos", "pontos para mapa de calor (limite 6.000, teto 20.000)"],
            ["GET /api/celula?lat=&lon=", "eventos da célula clicada"],
            ["GET /api/evento?id=", "ficha completa do evento"],
            ["GET /api/estatisticas", "resumo do recorte"],
            ["GET /api/filtros", "opções reais para os selects"],
            ["GET /api/status", "saúde do banco e contagens"],
            ["GET /api/importacoes", "últimas cargas"],
        ],
        [5.2 * cm, 11.8 * cm],
    )
)
historia.append(
    p(
        "Todos aceitam ano_ini, ano_fim, mag_min, mag_max, prof_max, fonte, uf, "
        "categoria e celula. A validação é central: filtro inválido responde 400 "
        "com mensagem em português; erro de banco responde 503; falta de sessão "
        "responde 401 nas APIs e redireciona para /login nas páginas."
    )
)

# --- 8 -------------------------------------------------------------------
historia.append(h1("8. Login e cadastro"))
historia.append(
    p(
        "As contas ficam na tabela usuarios. A senha nunca é gravada em texto: "
        "é armazenada como PBKDF2-HMAC-SHA256 com 260.000 iterações e salt "
        "aleatório por usuário. O login compara o hash em tempo constante."
    )
)
historia.append(
    p(
        "A sessão é um cookie HttpOnly assinado com HMAC-SHA256 (payload com "
        "e-mail e expiração). A validade padrão é 12 horas. O cookie recebe "
        "Secure quando a requisição chega por HTTPS (X-Forwarded-Proto do túnel)."
    )
)
historia.append(h2("Regras de proteção"))
historia.extend(
    itens(
        [
            "5 tentativas de login erradas por IP em 5 minutos bloqueiam temporariamente.",
            "Cadastro limitado a 10 tentativas por IP por hora.",
            "Senha mínima de 8 caracteres; confirmação obrigatória.",
            "E-mail normalizado para minúsculas e validado por expressão regular.",
            "O primeiro usuário é criado no boot a partir de LOGIN_EMAIL/LOGIN_SENHA, somente se a tabela estiver vazia.",
        ]
    )
)
historia.append(
    p(
        "Depois de criada a conta, o usuário já entra e vai para o mapa. O botão "
        "Sair apaga o cookie. Não há recuperação de senha automática: para "
        "redefinir, atualize o hash no banco ou apague a conta e cadastre de novo."
    )
)
historia.append(PageBreak())
historia.append(h2("Tela de login"))
historia.extend(imagem(ASSETS / "login.png", 8.5, "Login em /login"))
historia.append(h2("Tela de cadastro"))
historia.extend(imagem(ASSETS / "registrar.png", 8.5, "Cadastro em /registrar"))

# --- 9 -------------------------------------------------------------------
historia.append(h1("9. Interface"))
historia.extend(
    itens(
        [
            "Leaflet 1.9.4 com tiles do OpenStreetMap escurecidos por filtro CSS.",
            "leaflet.heat 0.2.0 para a camada de calor (um ponto por evento).",
            "Chart.js 4.4.1 para série anual e histograma de magnitudes.",
            "Fontes Inter e Space Grotesk, com fallback para o sistema.",
            "Filtros refletidos na URL; link compartilhável.",
            "Legenda com faixas numéricas; status com aria-live; foco visível.",
        ]
    )
)
historia.extend(imagem(ASSETS / "dashboard.png", 16, "Mapa de densidade e painel"))
historia.extend(imagem(ASSETS / "card-serie.png", 12, "Série anual de eventos detectados"))
historia.extend(
    imagem(ASSETS / "card-histograma.png", 12, "Distribuição de magnitudes")
)

# --- 10 ------------------------------------------------------------------
historia.append(h1("10. Cloudflare Tunnel explicado"))
historia.append(
    p(
        "O site roda numa máquina sem IP público ou atrás de NAT. Em vez de abrir "
        "porta no roteador, o cloudflared abre uma conexão de saída para a "
        "Cloudflare e mantém um túnel. Quando alguém acessa a URL pública, a "
        "Cloudflare entrega a requisição por dentro dessa conexão ao processo "
        "local. Não é necessário abrir porta 80/8080 para a internet."
    )
)
historia.append(
    codigo(
        """
navegador -> Cloudflare (HTTPS) -> tunel de saida -> cloudflared
          -> http://127.0.0.1:8080 -> app.py
"""
    )
)
historia.append(h2("Túnel rápido (quick tunnel)"))
historia.append(
    p(
        "É o modo usado na demonstração. Não exige conta nem domínio: a "
        "Cloudflare gera uma URL aleatória trycloudflare.com. A URL muda quando "
        "o processo cloudflared reinicia e o serviço não tem SLA."
    )
)
historia.append(
    codigo(
        """
# instalar (Ubuntu/Debian, x86_64)
curl -fsSL -o /tmp/cloudflared.deb \\
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i /tmp/cloudflared.deb

# subir o túnel apontando para o app
cloudflared tunnel --no-autoupdate --protocol http2 \\
  --url http://127.0.0.1:8080

# a URL aparece no log:
# <tunel-efemero>
"""
    )
)
historia.append(
    p(
        "Neste projeto o túnel roda como processo iniciado por "
        "scripts/start_servidor.sh. Em host com systemd, o mesmo comando pode "
        "virar uma unit (ExecStart=...). Em Docker, o serviço cloudflared do "
        "compose faz o mesmo com --url http://app:8080."
    )
)
historia.append(h2("Túnel nomeado (link fixo)"))
historia.append(
    p(
        "Para uma URL estável é preciso um domínio no Cloudflare. Crie o túnel "
        "no painel (Zero Trust > Networks > Tunnels), aponte o hostname para "
        "http://127.0.0.1:8080 e instale o conector com o token:"
    )
)
historia.append(
    codigo(
        """
sudo cloudflared service install 'TOKEN-DO-TUNEL'
sudo systemctl enable --now cloudflared
"""
    )
)
historia.append(h2("Cuidados e erros comuns"))
historia.append(
    tabela(
        ["Sintoma", "Causa provável", "O que fazer"],
        [
            ["Error 1033", "conector caiu ou ainda não registrou", "ver logs e reiniciar cloudflared; aguardar 20 s"],
            ["502/530", "origem não respondeu durante a queda", "recarregar; conferir app em 127.0.0.1:8080"],
            ["DNS não resolve", "túnel rápido encerrado", "subir de novo e pegar a URL nova"],
            ["QUIC instável", "Wi-Fi/roteador bloqueando UDP", "usar --protocol http2"],
            ["cookie não persiste", "HTTPS + Secure", "acessar pela URL https do túnel"],
        ],
        [3.6 * cm, 6.2 * cm, 7.2 * cm],
    )
)

# --- 11 -----------------------------------------------------------------
historia.append(h1("11. Deploy no servidor atual"))
historia.append(
    p(
        "O host de produção é um container Ubuntu 24.04 acessado por SSH na "
        "porta 2222, com sudo sem senha. Ele não tem systemd e não permite "
        "namespaces, então Docker não roda ali. O deploy é nativo: PostgreSQL "
        "como processo do cluster, aplicação em venv e cloudflared como processo."
    )
)
historia.append(h2("Passos executados"))
historia.append(
    codigo(
        """
# 1. pacotes
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib postgis python3-venv curl

# 2. banco (script do projeto)
sudo bash scripts/create_db.sh 'SENHA-FORTE'
sudo pg_ctlcluster 16 main start

# 3. aplicação
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. .env (sem versionar)
HOST=0.0.0.0
PORTA=8080
DB_HOST=127.0.0.1
DB_PASSWORD=...
LOGIN_EMAIL=...
LOGIN_SENHA=...
SESSION_SECRET=...

# 5. dados
.venv/bin/python scripts/importar_catalogo.py

# 6. processos (sem systemd)
setsid -f .venv/bin/python app.py >> app.log 2>&1 < /dev/null
setsid -f cloudflared tunnel --no-autoupdate --protocol http2 \\
  --url http://127.0.0.1:8080 > tunnel.log 2>&1 < /dev/null
"""
    )
)
historia.append(
    p(
        "Os scripts start_servidor.sh e status_servidor.sh automatizam subir, "
        "religar e conferir. Como não há systemd, reiniciar o container não sobe "
        "nada sozinho: é preciso rodar o start depois de cada reinício."
    )
)
historia.append(h2("Banco e permissões"))
historia.append(
    p(
        "O script cria o papel e o banco sismos_br, habilita PostGIS, aplica o "
        "schema e transfere as tabelas para o usuário da aplicação. Isso é "
        "necessário porque o boot repete CREATE TABLE IF NOT EXISTS, e o "
        "PostgreSQL exige que o usuário seja dono da tabela mesmo quando ela já "
        "existe."
    )
)
historia.append(h2("Backup"))
historia.append(
    codigo(
        """
set -a; . ./.env; set +a
PGPASSWORD="$DB_PASSWORD" pg_dump -h 127.0.0.1 -U sismos_br \\
  -Fc sismos_br > "$HOME/sismos_br_$(date +%F).dump"
"""
    )
)

# --- 12 -----------------------------------------------------------------
historia.append(h1("12. Alternativa Docker"))
historia.append(
    p(
        "O repositório tem Dockerfile e docker-compose.yml com três serviços: "
        "db (postgis/postgis:16-3.4), app (build local) e cloudflared. A stack "
        "foi construída e testada no Docker Desktop: banco healthy, importação "
        "de 5.141 eventos, API 200 e login funcionando."
    )
)
historia.append(
    codigo(
        """
cp .env.docker.example .env
# edite DB_PASSWORD, LOGIN_EMAIL, LOGIN_SENHA e SESSION_SECRET
docker compose up -d --build
docker compose exec app python scripts/importar_catalogo.py
docker compose logs cloudflared | grep trycloudflare
"""
    )
)
historia.append(
    p(
        "No host de produção atual a stack não roda: sem CAP_SYS_ADMIN, o daemon "
        "não cria a rede bridge e o docker run falha ao registrar camada com "
        "unshare: operation not permitted. Para usar Docker, leve o projeto para "
        "uma VM de verdade (Google Cloud, Oracle, VPS ou VirtualBox)."
    )
)

# --- 13 -----------------------------------------------------------------
historia.append(h1("13. Operação e manutenção"))
historia.extend(
    itens(
        [
            "Conferir: bash scripts/status_servidor.sh (processos, API e URL).",
            "Atualizar dados: .venv/bin/python scripts/importar_catalogo.py --somente fdsn.",
            "Logs: tail -f app.log e tail -f tunnel.log.",
            "Reiniciar app: pkill -f '[p]ython app.py' e rodar start_servidor.sh.",
            "Trocar senha: atualizar o hash na tabela usuarios ou recriar a conta.",
            "Backup: pg_dump -Fc antes de reimportações grandes.",
        ]
    )
)
historia.append(h2("Segurança recomendada"))
historia.extend(
    itens(
        [
            "Usar HTTPS (o túnel já entrega) para o cookie Secure.",
            "Trocar a senha do usuário SSH e preferir chave em vez de senha.",
            "Não versionar .env: ele guarda senha do banco, login e segredo de sessão.",
            "Para link fixo, migrar do túnel rápido para o nomeado.",
            "Revisar contas criadas em /registrar; não há painel de administração.",
        ]
    )
)

# --- 14 -----------------------------------------------------------------
historia.append(h1("14. Problemas reais e soluções"))
historia.append(
    tabela(
        ["Problema", "Solução aplicada"],
        [
            ["VM VirtualBox com kernel panic", "deploy migrado para servidor SSH"],
            ["bridge Wi-Fi sem rota", "adaptador NAT com portas encaminhadas"],
            ["porta 80 ocupada", "app na 8080 e túnel apontando para ela"],
            ["Docker sem unshare", "deploy nativo; Docker só em VM real"],
            ["túnel caindo no Wi-Fi", "--protocol http2 e reconexão automática"],
            ["schema com ; em comentário", "parser de comandos remove comentários antes de dividir"],
            ["teste sujando o banco", "tearDown apaga usuário/evento de teste"],
            ["hora local do SISBRA", "sufixo L convertido de UTC-3 para UTC"],
            ["coordenada com sinal perdido", "fallback valida sinal e limites"],
        ],
        [7 * cm, 10 * cm],
    )
)

# --- 15 -----------------------------------------------------------------
historia.append(h1("15. Passo a passo para replicar"))
historia.append(
    p(
        "Checklist mínimo para um amigo construir algo parecido. Troque nomes, "
        "portas e senhas conforme o ambiente."
    )
)
historia.append(
    codigo(
        """
[ ] 1. Escolher fonte de dados e entender o formato (colunas, CSV, GeoJSON).
[ ] 2. Subir PostgreSQL + PostGIS e criar banco/usuário.
[ ] 3. Escrever o schema e o acesso (psycopg, SQL parametrizado).
[ ] 4. Implementar parser + normalização + testes com amostras reais.
[ ] 5. Importar com upsert idempotente e filtrar pela malha oficial.
[ ] 6. Modelar a grade/consulta espacial e validar totais.
[ ] 7. Criar a API MVC com validação central e respostas 400/401/503.
[ ] 8. Montar o frontend (mapa, filtros, painel, legenda, acessibilidade).
[ ] 9. Adicionar login/cadastro com hash de senha e cookie assinado.
[ ] 10. Testar tudo localmente (incluindo consulta vazia e filtro inválido).
[ ] 11. Publicar com Cloudflare Tunnel e testar pela URL pública.
[ ] 12. Configurar processo/serviço, logs, backup e atualização de dados.
[ ] 13. Documentar credenciais, limitações e o que fazer após reinício.
"""
    )
)
historia.append(h2("Comandos que mais vão ser usados"))
historia.append(
    codigo(
        """
python -m unittest discover -s tests -v
python scripts/importar_catalogo.py
bash scripts/start_servidor.sh
bash scripts/status_servidor.sh
cloudflared tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8080
"""
    )
)

# --- 16 -----------------------------------------------------------------
historia.append(h1("16. Hospedagem: opções e custos"))
historia.append(
    tabela(
        ["Opção", "Prós", "Contras"],
        [
            ["VM local / PC ligado", "custo zero", "depende do PC e da rede"],
            ["Servidor SSH em container", "barato e simples", "sem systemd/Docker; reinício manual"],
            ["Oracle Always Free", "grátis 24h", "cartão de verificação e capacidade ARM"],
            ["Google Cloud e2-micro", "grátis em 3 regiões dos EUA", "cartão; latência maior"],
            ["VPS barato", "estável e previsível", "custo mensal (~R$ 20-35)"],
            ["Cloudflare Tunnel", "não abre portas; HTTPS", "rápido muda de URL; nomeado exige domínio"],
        ],
        [4 * cm, 5.8 * cm, 7.2 * cm],
    )
)
historia.append(
    p(
        "Para entrega acadêmica, o túnel rápido é suficiente. Para um link que "
        "funcione por meses, use túnel nomeado e uma VM com reinício automático."
    )
)

# --- 17 -----------------------------------------------------------------
historia.append(h1("17. Referências"))
historia.extend(
    itens(
        [
            "SISBRA/CSUSP-IAG-USP: seiscode.iag.usp.br/CSUSP/sisbra",
            "FDSN Moho/IAG-USP: moho.iag.usp.br/fdsnws/event/1/query",
            "Malhas do IBGE: servicodados.ibge.gov.br/api/v3/malhas",
            "PostGIS: postgis.net/documentation",
            "Cloudflare Tunnel: developers.cloudflare.com/cloudflare-one/connections/connect-networks",
            "Leaflet: leafletjs.com | Chart.js: chartjs.org",
        ]
    )
)
historia.append(Spacer(1, 10))
historia.append(
    p(
        "Documento gerado a partir do código real do projeto. Se algo divergir, "
        "o repositório e o servidor são a fonte da verdade."
    )
)

# --- build ---------------------------------------------------------------
doc = SimpleDocTemplate(
    str(SAIDA),
    pagesize=A4,
    leftMargin=2 * cm,
    rightMargin=2 * cm,
    topMargin=1.8 * cm,
    bottomMargin=1.8 * cm,
    title="Sismos BR - guia de construcao",
    author="Projeto Sismos BR",
    subject="Mapa de densidade de epicentros no Brasil",
)
doc.build(historia, onFirstPage=capa, onLaterPages=rodape)
print("PDF gerado:", SAIDA)
print("Páginas:", len(__import__("pypdf").PdfReader(str(SAIDA)).pages))
