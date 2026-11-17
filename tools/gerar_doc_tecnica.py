"""Gera o PDF "Sismos BR — por trás dos panos" (documentação técnica interna).

Uso:
    python tools/gerar_doc_tecnica.py

Saída:
    docs/Sismos_BR_por_tras_dos_panos.pdf
"""

import datetime
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    # permite importar config/servicos (fonte única de alguns números)
    sys.path.insert(0, RAIZ)

from config import SESSAO_TTL
from servicos.senhas import ITERACOES as ITERACOES_PBKDF2

from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as canvas_mod
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Paleta e estilos
# ---------------------------------------------------------------------------

PRIMARIO = colors.HexColor("#0B3C5D")   # azul escuro
ACENTO = colors.HexColor("#1D7A8C")     # teal
FUNDO = colors.HexColor("#EEF3F6")      # cinza azulado claro
GRADE = colors.HexColor("#B9C6CE")
TEXTO = colors.HexColor("#1F2933")

LARGURA, ALTURA = A4
MARGEM = 2.2 * cm
UTIL = LARGURA - 2 * MARGEM             # 16,6 cm de largura útil

# Números sem fonte única no código — atualizar aqui quando mudarem.
DATA_HOJE = datetime.date.today().strftime("%d/%m/%Y")
ITERACOES_TXT = "{:,}".format(ITERACOES_PBKDF2).replace(",", ".")
ITERACOES_CRU = str(ITERACOES_PBKDF2)
BASE_ATUAL = "5.141 eventos no recorte do Brasil (5.044 SISBRA + 97 FDSN)"
N_TESTES = 168

CORPO = ParagraphStyle(
    "corpo", parent=getSampleStyleSheet()["Normal"],
    fontName="Helvetica", fontSize=9.8, leading=14, textColor=TEXTO,
    alignment=TA_JUSTIFY, spaceAfter=4,
)
VIETA = ParagraphStyle(
    "vieta", parent=CORPO, leftIndent=14, bulletIndent=4, spaceAfter=2.5,
)
SECAO = ParagraphStyle(
    "secao", parent=getSampleStyleSheet()["Normal"],
    fontName="Helvetica-Bold", fontSize=14.5, leading=18,
    textColor=PRIMARIO, spaceBefore=6, spaceAfter=2,
)
CODIGO = ParagraphStyle(
    "codigo", parent=getSampleStyleSheet()["Normal"],
    fontName="Courier", fontSize=8.6, leading=11.5, textColor=TEXTO,
    backColor=FUNDO, borderPadding=5, leftIndent=4, rightIndent=4,
    spaceBefore=4, spaceAfter=6,
)
TCAB = ParagraphStyle(
    "tcab", parent=getSampleStyleSheet()["Normal"],
    fontName="Helvetica-Bold", fontSize=8.6, leading=11, textColor=colors.white,
)
TCAB_C = ParagraphStyle(
    "tcab_c", parent=TCAB, alignment=TA_CENTER,
)
TCEL = ParagraphStyle(
    "tcel", parent=getSampleStyleSheet()["Normal"],
    fontName="Helvetica", fontSize=8.6, leading=11.2, textColor=TEXTO,
)
TCEL_C = ParagraphStyle(
    "tcel_c", parent=TCEL, alignment=TA_CENTER,
)
RODAPE_TABELA = ParagraphStyle(
    "rodape_tabela", parent=CORPO, fontSize=8.2, leading=11,
    textColor=colors.HexColor("#5A6B76"), spaceBefore=2,
)


def titulo_secao(story, numero, texto):
    story.append(Paragraph("{} · {}".format(numero, texto), SECAO))
    story.append(
        HRFlowable(width="100%", thickness=1.2, color=ACENTO,
                   spaceBefore=1, spaceAfter=8)
    )


def tabela(dados, larguras, centro=()):
    """Tabela com cabeçalho azul e linhas zebradas; células viram Paragraph."""
    corpo_tabela = []
    for indice, linha in enumerate(dados):
        nova = []
        for coluna, valor in enumerate(linha):
            if indice == 0:
                nova.append(Paragraph(valor, TCAB_C if coluna in centro else TCAB))
            elif coluna in centro:
                nova.append(Paragraph(valor, TCEL_C))
            else:
                nova.append(Paragraph(valor, TCEL))
        corpo_tabela.append(nova)

    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARIO),
        ("GRID", (0, 0), (-1, -1), 0.5, GRADE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for indice in range(2, len(corpo_tabela), 2):
        estilo.append(("BACKGROUND", (0, indice), (-1, indice), FUNDO))
    for coluna in centro:
        estilo.append(("ALIGN", (coluna, 0), (coluna, -1), "CENTER"))
    objeto = Table(corpo_tabela, colWidths=larguras, repeatRows=1)
    objeto.setStyle(TableStyle(estilo))
    return objeto


# ---------------------------------------------------------------------------
# Diagramas (desenhados com reportlab.graphics)
# ---------------------------------------------------------------------------

def _seta(x1, y1, x2, y2, cor=ACENTO, ponta=5):
    """Segmento com ponta de seta (horizontal ou vertical)."""
    horizontal = y1 == y2
    if horizontal:
        direcao = 1 if x2 > x1 else -1
        corpo = Line(x1, y1, x2 - direcao * ponta, y2,
                     strokeColor=cor, strokeWidth=1.2)
        cabeca = Polygon(
            [x2, y2, x2 - direcao * ponta * 1.6, y2 + ponta * 0.8,
             x2 - direcao * ponta * 1.6, y2 - ponta * 0.8],
            fillColor=cor, strokeColor=cor,
        )
    else:
        direcao = 1 if y2 > y1 else -1
        corpo = Line(x1, y1, x2, y2 - direcao * ponta,
                     strokeColor=cor, strokeWidth=1.2)
        cabeca = Polygon(
            [x2, y2, x2 + ponta * 0.8, y2 - direcao * ponta * 1.6,
             x2 - ponta * 0.8, y2 - direcao * ponta * 1.6],
            fillColor=cor, strokeColor=cor,
        )
    return Group(corpo, cabeca)


def _caixa(x, y, w, h, rotulo, sub=None, fundo=FUNDO, texto_br=False):
    cor_texto = colors.white if texto_br else PRIMARIO
    partes = [
        Rect(x, y, w, h, rx=4, ry=4, fillColor=fundo,
             strokeColor=PRIMARIO if not texto_br else fundo,
             strokeWidth=1.1),
        String(x + w / 2.0, y + h / 2.0 + (2.6 if sub else 0), rotulo,
               textAnchor="middle", fontName="Helvetica-Bold", fontSize=8.2,
               fillColor=colors.white if texto_br else PRIMARIO),
    ]
    if sub:
        partes.append(
            String(x + w / 2.0, y + h / 2.0 - 7.5, sub, textAnchor="middle",
                   fontName="Helvetica", fontSize=6.9,
                   fillColor=colors.HexColor("#D7E3EA") if texto_br
                   else colors.HexColor("#5A6B76"))
        )
    return Group(*partes)


def _cinto(rotulo, palavras, largura_alvo):
    """Largura de caixa que cabe o título (8,2 bold) e o subtítulo (6,9)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    return max(
        largura_alvo,
        stringWidth(rotulo, "Helvetica-Bold", 8.2) + 14,
        stringWidth(palavras, "Helvetica", 6.9) + 12 if palavras else 0,
    )


def _duas_fileiras(fila1, fila2, altura=1.35 * cm, gap=0.36 * cm):
    """Desenha fila1 (esq→dir), cotovelo e fila2 (esq→dir). Soma ≤ UTIL."""
    d = Drawing(UTIL, 5.4 * cm)
    y1 = 3.55 * cm
    y2 = 1.35 * cm

    def fileira(itens, y, inicio=0.2 * cm):
        x = inicio
        caixas = []
        for rotulo, sub, largura, destaque in itens:
            larg = _cinto(rotulo, sub, largura * cm)
            fundo, branco = ((ACENTO if destaque == "acento" else PRIMARIO), True) \
                if destaque else (FUNDO, False)
            d.add(_caixa(x, y, larg, altura, rotulo, sub, fundo=fundo,
                         texto_br=branco))
            caixas.append((x, larg))
            x += larg + gap
        if x - inicio - gap > UTIL:
            raise ValueError(
                "fileira do diagrama passa da margem: " + itens[0][0]
            )
        return caixas, x

    caixas1, _ = fileira(fila1, y1)
    for x, larg in caixas1[:-1]:
        d.add(_seta(x + larg, y1 + altura / 2, x + larg + gap,
                    y1 + altura / 2))
    caixas2, _ = fileira(fila2, y2)
    for x, larg in caixas2[:-1]:
        d.add(_seta(x + larg, y2 + altura / 2, x + larg + gap,
                    y2 + altura / 2))

    # cotovelo: sai da última caixa da fila 1 e entra na primeira da fila 2
    fim_x = caixas1[-1][0] + caixas1[-1][1] / 2
    inicio_x = caixas2[0][0] + caixas2[0][1] / 2
    meio_y = (y1 + y2 + altura) / 2
    d.add(Group(
        Line(fim_x, y1, fim_x, meio_y, strokeColor=ACENTO, strokeWidth=1.2),
        Line(fim_x, meio_y, inicio_x + 5, meio_y, strokeColor=ACENTO,
             strokeWidth=1.2),
        Line(inicio_x, meio_y, inicio_x, y2 + altura + 5,
             strokeColor=ACENTO, strokeWidth=1.2),
        _seta(inicio_x, y2 + altura + 5, inicio_x, y2 + altura),
    ))
    return d


def diagrama_arquitetura():
    d = _duas_fileiras(
        [
            ("Navegador", "HTML/CSS/JS", 1.7, None),
            ("nginx + TLS", "Cloudflare Tunnel", 2.6, None),
            ("app.py", "ThreadingHTTPServer", 2.9, None),
            ("rotas/rotas.py", "(método, caminho)", 2.6, None),
        ],
        [
            ("controles/", "validação · resposta", 2.7, None),
            ("modelo/", "SQL parametrizado", 2.7, None),
            ("PostgreSQL + PostGIS", "consultas espaciais", 3.3, "primario"),
        ],
    )
    d.add(String(0.2 * cm, 0.72 * cm,
                 "Resposta: JSON (GeoJSON) ou HTML renderizado · static/ servido pelo próprio app.py",
                 fontName="Helvetica", fontSize=7.6,
                 fillColor=colors.HexColor("#5A6B76")))
    return d


def diagrama_densidade():
    d = _duas_fileiras(
        [
            ("Filtros validados", "400 se inválidos", 2.6, None),
            ("CTE base", "SELECT com %s", 2.2, None),
            ("Células", "floor(coord/c)*c", 2.4, "acento"),
            ("GROUP BY", "n · mag · período", 2.5, None),
        ],
        [
            ("Área real", "ST_Area(::geography)", 2.7, "acento"),
            ("Cortes de cor", "sobre os totais", 2.3, None),
            ("GeoJSON", "células para o Leaflet", 3.0, None),
        ],
        altura=1.4 * cm,
    )
    d.add(String(0.2 * cm, 0.72 * cm,
                 "A célula clicada usa a mesma fórmula floor: devolve exatamente os eventos que a formaram",
                 fontName="Helvetica", fontSize=7.6,
                 fillColor=colors.HexColor("#5A6B76")))
    return d


def _uma_fileira(itens, altura=1.5 * cm):
    d = Drawing(UTIL, 3.2 * cm)
    y = 1.2 * cm
    x = 0.2 * cm
    caixas = []
    for rotulo, sub, largura, destaque in itens:
        larg = _cinto(rotulo, sub, largura * cm)
        fundo, branco = ((ACENTO if destaque == "acento" else PRIMARIO), True) \
            if destaque else (FUNDO, False)
        d.add(_caixa(x, y, larg, altura, rotulo, sub, fundo=fundo,
                     texto_br=branco))
        caixas.append((x, larg))
        x += larg + 0.36 * cm
    if x - 0.2 * cm - 0.36 * cm > UTIL:
        raise ValueError("fileira do diagrama passa da margem: " + itens[0][0])
    for (x, larg), (prox_x, _) in zip(caixas, caixas[1:]):
        d.add(_seta(x + larg, y + altura / 2, prox_x, y + altura / 2))
    return d


def diagrama_senha():
    d = _uma_fileira(
        [
            ("Senha do usuário", "mín. 8 caracteres", 2.4, None),
            ("Salt aleatório", "16 bytes · secrets", 2.3, None),
            ("PBKDF2-SHA256", "{} iterações".format(ITERACOES_TXT), 2.4, None),
            ("Hash hex", "derivado da senha", 2.3, None),
            ("Armazenado", "só o derivado no banco", 2.6, "primario"),
        ],
        altura=1.5 * cm,
    )
    d.add(String(0.2 * cm, 0.7 * cm,
                 "Verificação recomputa o PBKDF2 e compara em tempo constante (hmac.compare_digest) — imune a timing attack",
                 fontName="Helvetica", fontSize=7.6,
                 fillColor=colors.HexColor("#5A6B76")))
    return d


def diagrama_sessao():
    d = _uma_fileira(
        [
            ("Payload JSON", "e-mail + expiração", 2.4, None),
            ("Base64url", "sem estado no servidor", 2.6, None),
            ("Assinatura", "HMAC-SHA256", 2.2, "acento"),
            ("Cookie", "HttpOnly · Lax · Secure", 2.7, "acento"),
            ("Validação", "assinatura + exp", 2.4, None),
        ],
        altura=1.5 * cm,
    )
    d.add(String(0.2 * cm, 0.7 * cm,
                 "Alterar um byte do token invalida a assinatura; sem o SESSION_SECRET não há como forjar sessão",
                 fontName="Helvetica", fontSize=7.6,
                 fillColor=colors.HexColor("#5A6B76")))
    return d


# ---------------------------------------------------------------------------
# Capa, cabeçalho e numeração
# ---------------------------------------------------------------------------

def capa_fundo(objeto, _doc):
    objeto.saveState()
    objeto.setFillColor(colors.HexColor("#F7FAFC"))
    objeto.rect(0, 0, LARGURA, ALTURA, stroke=0, fill=1)
    objeto.setFillColor(PRIMARIO)
    objeto.rect(0, ALTURA - 10.2 * cm, LARGURA, 10.2 * cm, stroke=0, fill=1)
    objeto.setFillColor(ACENTO)
    objeto.rect(0, ALTURA - 10.7 * cm, LARGURA, 0.5 * cm, stroke=0, fill=1)
    objeto.setFillColor(colors.white)
    objeto.setFont("Helvetica-Bold", 27)
    objeto.drawString(MARGEM, ALTURA - 3.5 * cm, "Sismos BR")
    objeto.setFont("Helvetica", 13.5)
    objeto.drawString(
        MARGEM, ALTURA - 4.6 * cm,
        "Densidade de epicentros no Brasil — como o projeto funciona por dentro",
    )
    objeto.setFont("Helvetica", 10.5)
    objeto.setFillColor(colors.HexColor("#C7D8E2"))
    objeto.drawString(MARGEM, ALTURA - 5.6 * cm,
                      "Documentação técnica interna · arquitetura, dados e segurança")
    objeto.setFillColor(colors.white)
    objeto.setFont("Helvetica-Bold", 11)
    objeto.drawString(MARGEM, ALTURA - 7.4 * cm, "Stack resumida")
    objeto.setFont("Helvetica", 9.5)
    for indice, linha in enumerate([
        "Python 3.12 puro (MVC, sem framework web) · http.server ThreadingHTTPServer",
        "PostgreSQL 16 + PostGIS 3.4 · driver psycopg 3 · SQL 100% parametrizado",
        "Front-end: Leaflet 1.9.4 · leaflet.heat 0.2.0 · Chart.js 4.4.1",
        "Senhas: PBKDF2-HMAC-SHA256 ({} iterações) · sessão em cookie assinado (HMAC)".format(ITERACOES_TXT),
        "Deploy: nginx + TLS · Cloudflare Tunnel · Ubuntu Server (container)",
    ]):
        objeto.drawString(MARGEM, ALTURA - (8.05 + indice * 0.42) * cm, linha)
    objeto.restoreState()


def cabecalho_rodape(objeto, _doc):
    numero = objeto.getPageNumber()
    if numero <= 1:
        return
    objeto.saveState()
    objeto.setStrokeColor(GRADE)
    objeto.setLineWidth(0.6)
    objeto.line(MARGEM, ALTURA - 1.35 * cm, LARGURA - MARGEM,
                ALTURA - 1.35 * cm)
    objeto.setFont("Helvetica", 8)
    objeto.setFillColor(colors.HexColor("#5A6B76"))
    objeto.drawString(MARGEM, ALTURA - 1.15 * cm, "Sismos BR — por trás dos panos")
    objeto.drawRightString(LARGURA - MARGEM, ALTURA - 1.15 * cm, DATA_HOJE)
    objeto.line(MARGEM, 1.5 * cm, LARGURA - MARGEM, 1.5 * cm)
    objeto.restoreState()


class Numeracao(canvas_mod.Canvas):
    """Segunda passada: grava estados e reescreve "Página X de Y" no fim."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas_salvas = []

    def showPage(self):
        self._paginas_salvas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas_salvas)
        for indice, estado in enumerate(self._paginas_salvas, start=1):
            self.__dict__.update(estado)
            if indice > 1:
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#5A6B76"))
                self.drawCentredString(LARGURA / 2, 1.05 * cm,
                                       "Página {} de {}".format(indice, total))
            super().showPage()
        super().save()


# ---------------------------------------------------------------------------
# Documento
# ---------------------------------------------------------------------------

def construir(story, destino):
    doc = BaseDocTemplate(
        destino, pagesize=A4,
        leftMargin=MARGEM, rightMargin=MARGEM,
        topMargin=MARGEM, bottomMargin=1.9 * cm,
        title="Sismos BR — por trás dos panos",
        author="Trabalho de faculdade",
        subject="Arquitetura, dados e segurança do projeto",
    )
    capa = Frame(0, 0, LARGURA, ALTURA - 11.2 * cm, id="capa",
                 leftPadding=MARGEM, rightPadding=MARGEM,
                 topPadding=1.2 * cm, bottomPadding=0.8 * cm)
    corpo = Frame(MARGEM, 1.9 * cm, LARGURA - 2 * MARGEM,
                  ALTURA - MARGEM - 1.9 * cm, id="corpo")
    doc.addPageTemplates([
        PageTemplate(id="capa", frames=[capa], onPage=capa_fundo),
        PageTemplate(id="corpo", frames=[corpo], onPage=cabecalho_rodape),
    ])
    doc.build(story, canvasmaker=Numeracao)


def montar():
    story = []

    # ---- capa (conteúdo abaixo da faixa) --------------------------------
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Este documento explica <b>como o Sismos BR foi construído</b>: a "
        "arquitetura de camadas, o servidor HTTP próprio, o papel de cada "
        "tecnologia, o cálculo da densidade no PostGIS e as escolhas de "
        "segurança — inclusive <b>qual algoritmo protege as senhas</b> e "
        "<b>como a sessão é assinada</b>. Tudo o que está descrito aqui "
        "corresponde ao código que está no repositório e publicado no site.",
        ParagraphStyle("intro", parent=CORPO, fontSize=10.2, leading=15),
    ))
    story.append(Spacer(1, 0.35 * cm))

    ficha = [
        ["Ficha técnica", ""],
        ["Nome", "Sismos BR — densidade de epicentros no Brasil"],
        ["Tipo", "Trabalho de faculdade · aplicação web full-stack"],
        ["Fontes de dados", "SISBRA/RSBR (1690–2023) e FDSN do Moho/IAG-USP (2024+)"],
        ["Base atual", BASE_ATUAL],
        ["Site", "https://sismos-br.duckdns.org (nginx + TLS + Cloudflare Tunnel)"],
        ["Repositório", "Código, schema do banco, testes e runbooks em docs/"],
    ]
    story.append(tabela(ficha, [3.1 * cm, UTIL - 3.1 * cm]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<b>Sumário:</b> 1. Visão geral · 2. Arquitetura MVC sem framework · "
        "3. Servidor HTTP e ciclo da requisição · 4. Banco de dados e "
        "modelagem · 5. O cálculo da densidade · 6. Importação dos catálogos · "
        "7. Segurança (senhas, sessão, CSRF e limites) · 8. API · "
        "9. Front-end · 10. Infraestrutura e operação · 11. Escolhas técnicas "
        "e o porquê de cada uma.",
        ParagraphStyle("sumario", parent=RODAPE_TABELA, fontSize=8.6,
                       leading=12.5),
    ))

    story.append(NextPageTemplate("corpo"))
    story.append(PageBreak())

    # ---- 1. visão geral --------------------------------------------------
    titulo_secao(story, "1", "Visão geral")
    story.append(Paragraph(
        "O Sismos BR é um mapa interativo que agrega epicentros de "
        "terremotos históricos e recentes em células de uma grade e mostra a "
        "<b>densidade</b> de eventos pelo território brasileiro. O usuário "
        "filtra por período, magnitude, profundidade, fonte, UF e categoria "
        "do catálogo; o navegador recebe células GeoJSON e desenha o mapa "
        "com o Leaflet. Além do mapa, há painel estatístico (série anual, "
        "histograma de magnitudes, top UFs), mapa de calor de pontos "
        "individuais e ficha completa de cada evento.",
        CORPO,
    ))
    story.append(Paragraph(
        "O diferencial do projeto é <b>não usar framework web</b>: todo o "
        "ciclo HTTP — roteamento, formulários, cookies, statics, segurança — "
        "está implementado com a biblioteca padrão do Python, o que torna "
        "cada decisão visível e didática. O banco de dados é o responsável "
        "pelo cálculo espacial (PostGIS), e o site apenas lê o resultado.",
        CORPO,
    ))

    # ---- 2. arquitetura --------------------------------------------------
    titulo_secao(story, "2", "Arquitetura MVC sem framework")
    story.append(Paragraph(
        "O padrão é MVC: <b>rotas</b> (tabela caminho → controller), "
        "<b>controles</b> (validação e resposta), <b>modelo</b> (SQL) e "
        "<b>visão</b> (templates + static). O fluxo de uma requisição:",
        CORPO,
    ))
    story.append(diagrama_arquitetura())
    story.append(Spacer(1, 0.3 * cm))

    camadas = [
        ["Camada", "Arquivo / pasta", "Papel"],
        ["Entrada HTTP", "app.py",
         "ThreadingHTTPServer: parse da URL, cookies, corpo, statics, "
         "headers de segurança e despacho"],
        ["Roteamento", "rotas/rotas.py",
         "Dicionário {(método, caminho): função} — uma linha por rota, "
         "sem mágica"],
        ["Controller", "controles/",
         "Valida filtros, monta respostas JSON/HTML, controla login e "
         "cadastro"],
        ["Visão", "templates/ + static/",
         "HTML com escape próprio ({{variavel}}), CSS, JS do mapa"],
        ["Modelo", "modelo/",
         "SQL parametrizado (psycopg 3), upsert e consultas espaciais"],
        ["Serviços", "servicos/",
         "Parsers dos catálogos, senhas, sessões, estatística, geografia"],
        ["Config", "config.py",
         "Lê .env sem dependência externa e expõe constantes (células, "
         "limites, URLs)"],
    ]
    story.append(tabela(camadas, [2.6 * cm, 3.4 * cm, UTIL - 6.0 * cm]))
    story.append(Paragraph(
        "Toda resposta sai dos controllers como tupla <b>(status, "
        "cabeçalhos, corpo)</b> — o app.py é quem efetivamente escreve no "
        "socket. Erro inesperado em qualquer controller vira um 500 "
        "genérico (\"erro interno\"), sem stack trace para o cliente.",
        CORPO,
    ))

    # ---- 3. servidor -----------------------------------------------------
    story.append(PageBreak())
    titulo_secao(story, "3", "Servidor HTTP e ciclo da requisição")
    story.append(Paragraph(
        "<b>app.py</b> é um servidor de produção leve escrito sobre "
        "http.server (ThreadingHTTPServer — uma thread por conexão). "
        "Cada requisição passa por:",
        CORPO,
    ))
    ciclo = [
        ["Etapa", "O que acontece"],
        ["Parse", "URL quebrada em caminho e query; corpo de POST (form ou JSON) entra no dicionário `dados`"],
        ["Cookies", "Cabeçalho Cookie vira dicionário; sessão e token CSRF são lidos daqui"],
        ["Proxy confiável", "X-Real-IP/X-Forwarded-For só valem se a conexão veio de IP na lista (nginx/cloudflared); senão o IP é o do socket"],
        ["HTTPS forçado", "Se o proxy declara http, resposta é 301 para https com o mesmo caminho"],
        ["Sessão", "Rotas fora da lista pública exigem token válido; sem sessão: 401 (JSON) ou redirect /login"],
        ["Despacho", "ROTAS[(metodo, caminho)] chama o controller e devolve (status, headers, corpo)"],
        ["Headers", "nosniff · X-Frame-Options: DENY · referrer-policy · permissions-policy · HSTS (1 ano) · no-store nas rotas privadas"],
        ["Estáticos", "Servidos pelo próprio app: bloqueio de path traversal (realpath + commonpath), MIME correto e suporte a Range (206/416) para streaming dos vídeos"],
    ]
    story.append(tabela(ciclo, [3.0 * cm, UTIL - 3.0 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "Essa centralização é proposital: <b>qualquer</b> rota nova herda "
        "grátis a exigência de sessão, os headers de segurança e o bloqueio "
        "de spoofing de IP — nada depende do programador lembrar.",
        CORPO,
    ))

    # ---- 4. banco --------------------------------------------------------
    titulo_secao(story, "4", "Banco de dados e modelagem")
    story.append(Paragraph(
        "PostgreSQL 16 + PostGIS 3.4. O schema (db/schema.sql) tem quatro "
        "tabelas; o acesso é sempre por <b>SQL parametrizado</b> (psycopg 3, "
        "placeholders %s) — string de SQL nunca é montada com dados do "
        "usuário.",
        CORPO,
    ))
    schema_tab = [
        ["Tabela", "Chaves / tipos", "Função"],
        ["sismos",
         "id BIGSERIAL · fonte CHECK (SISBRA|FDSN) · evento_id · geom "
         "GEOMETRY(Point,4326) · ano SMALLINT · magnitude · "
         "profundidade_km · uf · categoria · UNIQUE(fonte, evento_id)",
         "Catálogo normalizado; o par (fonte, evento_id) é a identidade "
         "do evento"],
        ["estados",
         "codarea (IBGE, 2 dígitos) PK · uf · geom MultiPolygon 4326",
         "Malha oficial das 27 UFs: recorte territorial e filtro por "
         "estado"],
        ["importacoes",
         "fonte · arquivo · linhas_lidas/importadas/descartadas · "
         "iniciado_em · concluido_em · erro",
         "Log auditável de cada execução do importador"],
        ["usuarios",
         "email UNIQUE · senha_hash (PBKDF2) · criado_em",
         "Contas de acesso ao mapa"],
    ]
    story.append(tabela(schema_tab, [2.4 * cm, 7.4 * cm, UTIL - 9.8 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "<b>Índices:</b> GiST em sismos.geom e estados.geom (consultas "
        "espaciais), b-tree em ano e magnitude (filtros). "
        "<b>Idempotência:</b> o upsert usa ON CONFLICT (fonte, evento_id) "
        "DO NOTHING, então reimportar o catálogo não duplica nada. "
        "<b>evento_id</b> é o EventID do FDSN ou um hash determinístico "
        "md5(ano|mmdd|hora|lat|lon|mag) do SISBRA — mesma linha sempre "
        "recebe o mesmo identificador.",
        CORPO,
    ))

    # ---- 5. densidade ----------------------------------------------------
    story.append(PageBreak())
    titulo_secao(story, "5", "O cálculo da densidade (o coração do projeto)")
    story.append(Paragraph(
        "A agregação acontece <b>no banco</b>, numa única consulta com CTE. "
        "Cada evento cai na célula cujo canto é "
        "<b>floor(coordenada / célula) × célula</b> — alinhada à origem; a "
        "mesma fórmula é usada quando o usuário clica numa célula, então o "
        "que aparece no mapa é exatamente o que a lista mostra.",
        CORPO,
    ))
    story.append(Preformatted(
        "x_celula = floor(lon / celula) * celula\n"
        "y_celula = floor(lat / celula) * celula\n"
        "-- 0,25° · 0,5° (padrão) · 1° · 2°", CODIGO,
    ))
    story.append(diagrama_densidade())
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(
        "Dois detalhes que fazem diferença técnica:",
        CORPO,
    ))
    story.append(Paragraph(
        "<b>Área real em km².</b> O envelope da célula é convertido para "
        "geography e a área é calculada pelo PostGIS levando em conta a "
        "curvatura da Terra. É isso que permite a métrica "
        "<b>eventos por 1.000 km²</b>: células de latitudes diferentes ficam "
        "comparáveis (uma célula de 1° perto do equador é bem maior que perto "
        "do sul do país).",
        VIETA, bulletText="•",
    ))
    story.append(Paragraph(
        "<b>Cortes de cor justos.</b> Os limites de cor do mapa não são "
        "fixos: são calculados sobre os totais reais das células do filtro "
        "atual (servicos/estatistica.py), então qualquer recorte fica legível "
        "em vez de saturar ou apagar.",
        VIETA, bulletText="•",
    ))

    # ---- 6. importação ---------------------------------------------------
    titulo_secao(story, "6", "Importação dos catálogos")
    story.append(Paragraph(
        "A carga é um CLI offline (<b>scripts/importar_catalogo.py</b>): "
        "baixa, normaliza e grava; o site nunca executa código vindo do "
        "arquivo externo — os parsers são próprios (servicos/catalogo.py) e "
        "só extraem campos tipados.",
        CORPO,
    ))
    import_tab = [
        ["Etapa", "O que é feito"],
        ["Download", "SISBRA catalogo_RAW.dat (CSUSP/IAG-USP) e FDSN event/1/query (Moho/IAG-USP) com recorte do Brasil"],
        ["Parser", "Formato RAW do SISBRA e texto FDSN viram registros tipados; categoria SISBRA (A–I) preservada"],
        ["Normalização", "Hora local (sufixo L) convertida de UTC−3 para UTC; sem hora, data_hora fica NULL e o ano é preservado"],
        ["Identidade", "FDSN EventID; SISBRA recebe md5(ano|mmdd|hora|lat|lon|mag) — reimportação idempotente"],
        ["Upsert", "INSERT ... ON CONFLICT (fonte, evento_id) DO NOTHING"],
        ["Recorte", "DELETE dos eventos fora da malha do IBGE (ST_Contains) — descarta andinos e oceânicos"],
        ["Auditoria", "Lidas/importadas/descartadas por execução ficam em importacoes (exibidas em /api/importacoes)"],
    ]
    story.append(tabela(import_tab, [2.8 * cm, UTIL - 2.8 * cm]))

    # ---- 7. segurança ----------------------------------------------------
    story.append(PageBreak())
    titulo_secao(story, "7", "Segurança — o que protege cada coisa")
    story.append(Paragraph(
        "<b>Senhas — PBKDF2-HMAC-SHA256 (biblioteca padrão hashlib).</b> "
        "Nenhuma senha é armazenada nem criptografada de forma reversível: "
        "guarda-se o <b>derivado</b> de uma função de hash lenta, com salt "
        "aleatório de 16 bytes por usuário (módulo secrets). O formato "
        "guardado no banco:",
        CORPO,
    ))
    story.append(Preformatted(
        "pbkdf2_sha256$" + ITERACOES_CRU + "$<salt_hex(32 chars)>$<hash_hex(64 chars)>\n"
        "algoritmo^iteracoes^salt^derivado — iterações lidas do próprio hash",
        CODIGO,
    ))
    story.append(Paragraph(
        "{} iterações seguem a recomendação da OWASP para PBKDF2-SHA256 "
        "e tornam força bruta/offline muito cara. A comparação usa ".format(ITERACOES_TXT)
        + "<b>hmac.compare_digest</b> (tempo constante, imune a timing attack) "
        "e um hash malformado simplesmente não autentica.",
        CORPO,
    ))
    story.append(diagrama_senha())
    story.append(Spacer(1, 0.25 * cm))

    story.append(Paragraph(
        "<b>Sessões — cookie assinado, sem banco de sessão.</b> O token é "
        "<b>base64url(payload) . base64url(HMAC-SHA256(segredo, payload))</b>. "
        "O payload só carrega o e-mail e a expiração; qualquer alteração "
        "quebra a assinatura. O segredo vem do SESSION_SECRET do .env (fora "
        "do repositório); sem ele, um segredo aleatório por boot invalida as "
        "sessões a cada reinício (fail-safe).",
        CORPO,
    ))
    story.append(diagrama_sessao())
    story.append(Spacer(1, 0.2 * cm))

    cookie_tab = [
        ["Atributo do cookie", "Valor", "Por quê"],
        ["HttpOnly", "sim", "JS não lê o token — mitiga roubo por XSS"],
        ["SameSite", "Lax", "Cookie não viaja em POST cross-site — mitiga CSRF"],
        ["Secure", "quando HTTPS", "Token nunca vai em HTTP puro"],
        ["Path / Max-Age", "/ · 12 h",
         "Válida só no app; sessão expira (SESSION_TTL {})".format(SESSAO_TTL)],
    ]
    story.append(tabela(cookie_tab, [3.4 * cm, 2.9 * cm, UTIL - 6.3 * cm]))
    story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph(
        "<b>CSRF — duplo envio.</b> Todo formulário carrega um token "
        "aleatório (secrets.token_urlsafe(32)) gravado em cookie dedicado e "
        "injetado no HTML; o POST compara os dois valores em tempo constante. "
        "Sem o par cookie+campo, a resposta é 403.",
        CORPO,
    ))
    story.append(Paragraph(
        "<b>Limites contra força bruta</b> (em memória, por janela "
        "deslizante, com teto de 5.000 chaves):",
        CORPO,
    ))
    limites = [
        ["Ação", "Limite", "Janela"],
        ["Falhas de login por IP", "5", "5 min"],
        ["Falhas por conta (somando IPs)", "10", "15 min"],
        ["Cadastros por IP", "10", "1 h"],
    ]
    story.append(tabela(limites, [6.2 * cm, 2.6 * cm, 3.2 * cm], centro=(1, 2)))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "<b>Mais três camadas:</b> validação central dos filtros "
        "(whitelist para fonte/UF/categoria, limites numéricos, ano mínimo "
        "1500 — valor inválido responde 400); senha mínima de 8 caracteres e "
        "e-mail com regex; erro de banco nunca vaza (o usuário vê \"sistema "
        "indisponível\", 503) e erro interno nunca mostra stack.",
        CORPO,
    ))

    # ---- 8. API ----------------------------------------------------------
    story.append(PageBreak())
    titulo_secao(story, "8", "API (JSON/GeoJSON)")
    api_tab = [
        ["Método", "Rota", "Devolve"],
        ["GET", "/api/densidade", "Células GeoJSON: contagem, densidade/1000 km², magnitude máx/média, período, área, cortes de cor"],
        ["GET", "/api/sismos", "Pontos individuais para o mapa de calor (limite 6.000, teto 20.000)"],
        ["GET", "/api/celula?lat=&lon=", "Eventos da célula clicada (mesma fórmula floor da agregação)"],
        ["GET", "/api/evento?id=", "Ficha completa de um evento"],
        ["GET", "/api/estatisticas", "Total, período, maior evento, top UFs, série anual, histograma de magnitudes"],
        ["GET", "/api/filtros", "Opções reais do banco para os selects (UF, fonte, categoria)"],
        ["GET", "/api/status", "Saúde do banco, contagem por fonte, última importação (pública)"],
        ["GET", "/api/importacoes", "Histórico de execuções do importador"],
    ]
    story.append(tabela(api_tab, [1.8 * cm, 4.2 * cm, UTIL - 6.0 * cm],
                        centro=(0,)))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "Todos aceitam os filtros ano_ini, ano_fim, mag_min, mag_max, "
        "prof_max, fonte, uf, categoria e celula — validados em um único "
        "ponto (montar_filtros) que lança ErroValidacao → 400 com mensagem "
        "em português.",
        CORPO,
    ))

    # ---- 9. front-end ----------------------------------------------------
    titulo_secao(story, "9", "Front-end")
    front_tab = [
        ["Tecnologia", "Versão", "Papel"],
        ["Leaflet", "1.9.4", "Mapa base, grade de células coloridas, clique por célula"],
        ["leaflet.heat", "0.2.0", "Camada alternativa de mapa de calor com os pontos individuais"],
        ["Chart.js", "4.4.1", "Série anual, histograma de magnitudes e gráficos do painel"],
        ["JS/CSS próprios", "—", "Estado dos filtros na URL (link compartilhável), player responsivo de vídeo (1080×1920 no celular, 1920×1080 no desktop), fetch com feedback de carregamento"],
    ]
    story.append(tabela(front_tab, [3.6 * cm, 1.9 * cm, UTIL - 5.5 * cm],
                        centro=(1,)))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "O HTML é servido por templates com escape automático de variáveis "
        "(respostas.py escapar) — valores vindos do banco ou do usuário "
        "nunca entram crus no markup.",
        CORPO,
    ))

    # ---- 10. infra -------------------------------------------------------
    titulo_secao(story, "10", "Infraestrutura e operação")
    infra_tab = [
        ["Item", "Como é"],
        ["Host", "Ubuntu Server (container) — sem systemd; wrapper do sshd roda start_servidor.sh no boot, então os serviços sobem sozinhos"],
        ["Processo", "app Python 3.12 em venv, porta 8080 interna"],
        ["Banco", "PostgreSQL 16.15 + PostGIS 3.4.2 no mesmo host; portas não são publicadas"],
        ["Entrada pública", "nginx com TLS (DNS DuckDNS) → proxy para 127.0.0.1:8080; Cloudflare Tunnel como alternativa"],
        ["Backup", "pg_dump -Fc da base (e da tabela usuarios antes de qualquer operação sensível)"],
        ["Testes", "{} testes unitários/de integração (unittest); os de banco pulam sem PostGIS (SISMOS_TESTAR_DB=1 liga)".format(N_TESTES)],
        ["Administração", "Ponte SSH/SCP em tools/vm.py (paramiko); runbook completo em docs/SERVIDOR_SSH.md"],
    ]
    story.append(tabela(infra_tab, [3.2 * cm, UTIL - 3.2 * cm]))

    # ---- 11. escolhas ----------------------------------------------------
    story.append(PageBreak())
    titulo_secao(story, "11", "Escolhas técnicas e o porquê de cada uma")
    escolhas = [
        ["Escolha", "Alternativa comum", "Por quê essa"],
        ["Sem framework (http.server)", "Flask/Django",
         "Cada decisão fica explícita e didática; zero dependência de "
         "runtime; domínio real do ciclo HTTP"],
        ["PostGIS no cálculo da densidade", "Agregar no Python",
         "Agregação espacial é trabalho do banco: índice GiST, um SELECT "
         "só, menos memória e rede"],
        ["Área via geography", "Fórmula plana",
         "Comparação justa entre latitudes; densidade/1000 km² correta"],
        ["PBKDF2 da stdlib", "bcrypt/argon2 (libs externas)",
         "Algoritmo atual (OWASP 2023+) sem dependência nativa; formato "
         "auto-descritivo permite subir iterações depois"],
        ["Cookie assinado (sem tabela de sessão)", "Sessões em banco/memória",
         "Escalável de graça e didático: assinatura HMAC garante "
         "integridade sem estado no servidor"],
        ["CSRF double-submit", "Token em sessão servidor",
         "Funciona sem armazenar estado; comparação em tempo constante"],
        ["SQL parametrizado sempre", "Concatenar strings",
         "Injeção de SQL estruturalmente impossível, não só \"cuidado do "
         "dev\""],
        ["Validação central de filtros", "Validar em cada rota",
         "Um único ponto (montar_filtros) — nenhuma rota esquece de "
         "validar"],
        ["Hash determinístico no SISBRA", "id sequencial",
         "Reimportação idempotente: mesma linha do catálogo é sempre a "
         "mesma linha do banco"],
        ["Grade por floor", "ST_SnapToGrid apenas",
         "A mesma conta em Python (clique) e SQL (agregação) garante "
         "consistência célula↔eventos"],
    ]
    story.append(tabela(escolhas, [4.4 * cm, 3.6 * cm, UTIL - 8.0 * cm]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=GRADE))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "<b>Como conferir tudo isso:</b> o código é aberto no repositório do "
        "projeto — app.py (servidor), rotas/rotas.py (mapa de rotas), "
        "servicos/senhas.py (PBKDF2), servicos/sessoes.py (HMAC), "
        "modelo/sismo.py (consulta de densidade), db/schema.sql (banco) e "
        "scripts/importar_catalogo.py (carga). O site está no ar em "
        "https://sismos-br.duckdns.org.",
        ParagraphStyle("final", parent=CORPO, fontSize=9.2, leading=13.5),
    ))

    return story


def main():
    destino = os.path.join(RAIZ, "docs", "Sismos_BR_por_tras_dos_panos.pdf")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    construir(montar(), destino)
    print("PDF gerado: {}".format(destino))
    return 0


if __name__ == "__main__":
    sys.exit(main())
