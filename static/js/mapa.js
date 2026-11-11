/* Mapa de densidade de epicentros — front-end sem framework. */

(function () {
  "use strict";

  var CORES = ["#2c115f", "#721f81", "#b73779", "#f0705b", "#fec287"];
  var CENTRO_BRASIL = [-15.8, -52.0];

  var estado = {
    mapa: null,
    camadaGrade: null,
    camadaCalor: null,
    modo: "grade",
    cortes: [],
    metrica: "contagem",
    celula: 0.5,
    graficoSerie: null,
    graficoHistograma: null,
    filtros: {},
  };

  var el = {};

  function $(id) {
    return document.getElementById(id);
  }

  function texto(valor, padrao) {
    if (valor === null || valor === undefined || valor === "") {
      return padrao || "—";
    }
    return String(valor);
  }

  function numero(valor, casas) {
    if (valor === null || valor === undefined || valor === "") {
      return "—";
    }
    var n = Number(valor);
    if (!isFinite(n)) {
      return "—";
    }
    return n.toLocaleString("pt-BR", {
      minimumFractionDigits: casas || 0,
      maximumFractionDigits: casas || 0,
    });
  }

  function dataCurta(iso) {
    if (!iso) {
      return "—";
    }
    var d = new Date(iso);
    if (isNaN(d.getTime())) {
      return String(iso);
    }
    return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  }

  function definirStatus(mensagem, classe) {
    el.status.textContent = mensagem;
    el.status.className = "status" + (classe ? " " + classe : "");
  }

  function buscarJSON(url) {
    return fetch(url, { headers: { accept: "application/json" } }).then(function (r) {
      return r.json().catch(function () {
        return { ok: false, erro: "Resposta inválida do servidor." };
      }).then(function (corpo) {
        if (!r.ok || corpo.ok === false) {
          throw new Error(corpo.erro || "Falha ao consultar o servidor.");
        }
        return corpo;
      });
    });
  }

  /* --- Filtros ---------------------------------------------------------- */

  function filtrosDoFormulario() {
    var f = {
      ano_ini: el.anoIni.value.trim(),
      ano_fim: el.anoFim.value.trim(),
      mag_min: el.magMin.value.trim(),
      prof_max: el.profMax.value.trim(),
      fonte: el.fonte.value,
      uf: el.uf.value,
      categoria: el.categoria.value,
      celula: el.celula.value,
      metrica: el.metrica.value,
    };
    Object.keys(f).forEach(function (chave) {
      if (f[chave] === "" && chave !== "fonte" && chave !== "metrica") {
        delete f[chave];
      }
    });
    return f;
  }

  function queryDosFiltros(f) {
    var p = new URLSearchParams();
    Object.keys(f).forEach(function (chave) {
      if (f[chave] !== undefined && f[chave] !== null && f[chave] !== "") {
        p.set(chave, f[chave]);
      }
    });
    return p.toString();
  }

  function escreverURL(f) {
    var query = queryDosFiltros(f);
    var url = window.location.pathname + (query ? "?" + query : "");
    window.history.replaceState(null, "", url);
  }

  function lerURL() {
    return new URLSearchParams(window.location.search);
  }

  function preencherFormulario(params) {
    var mapa = {
      ano_ini: el.anoIni,
      ano_fim: el.anoFim,
      mag_min: el.magMin,
      prof_max: el.profMax,
      fonte: el.fonte,
      uf: el.uf,
      categoria: el.categoria,
      celula: el.celula,
      metrica: el.metrica,
    };
    Object.keys(mapa).forEach(function (chave) {
      var valor = params.get(chave);
      if (valor !== null && valor !== "") {
        mapa[chave].value = valor;
      }
    });
  }

  function carregarOpcoes() {
    return buscarJSON("/api/filtros").then(function (dados) {
      while (el.uf.options.length > 1) {
        el.uf.remove(1);
      }
      (dados.ufs || []).forEach(function (uf) {
        var opcao = document.createElement("option");
        opcao.value = uf;
        opcao.textContent = uf;
        el.uf.appendChild(opcao);
      });

      while (el.categoria.options.length > 1) {
        el.categoria.remove(1);
      }
      (dados.categorias || []).forEach(function (categoria) {
        var opcao = document.createElement("option");
        opcao.value = categoria;
        opcao.textContent = categoria;
        el.categoria.appendChild(opcao);
      });

      if (dados.ano_min) {
        el.anoIni.min = dados.ano_min;
        el.anoIni.placeholder = dados.ano_min;
      }
      if (dados.ano_max) {
        el.anoFim.max = dados.ano_max;
        el.anoFim.placeholder = dados.ano_max;
      }
    });
  }

  /* --- Mapa ------------------------------------------------------------- */

  function criarMapa() {
    estado.mapa = L.map("mapa", {
      center: CENTRO_BRASIL,
      zoom: 4,
      minZoom: 3,
      maxZoom: 12,
      worldCopyJump: true,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        subdomains: "abcd",
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      }
    ).addTo(estado.mapa);

    L.control.scale({ imperial: false }).addTo(estado.mapa);
  }

  function cortesDeValores(valores) {
    var ordenados = valores.slice().sort(function (a, b) {
      return a - b;
    });
    if (!ordenados.length) {
      return [];
    }
    var total = ordenados.length;
    var resultado = [];
    [20, 40, 60, 80].forEach(function (percentual) {
      var posto = Math.max(Math.ceil((percentual / 100) * total), 1);
      var valor = ordenados[Math.min(posto, total) - 1];
      if (!resultado.length || valor !== resultado[resultado.length - 1]) {
        resultado.push(valor);
      }
    });
    return resultado;
  }

  function indiceClasse(valor, cortes) {
    var indice = 0;
    while (indice < cortes.length && valor > cortes[indice]) {
      indice += 1;
    }
    return indice;
  }

  function estiloCelula(feature, cortes) {
    var valor = estado.metrica === "normalizada"
      ? feature.properties.densidade_km2
      : feature.properties.n;
    var indice = indiceClasse(Number(valor) || 0, cortes);
    return {
      fillColor: CORES[Math.min(indice, CORES.length - 1)],
      fillOpacity: 0.68,
      color: "#0b0f14",
      weight: 0.4,
    };
  }

  function desenharGrade(colecao, cortes) {
    if (estado.camadaGrade) {
      estado.mapa.removeLayer(estado.camadaGrade);
    }
    estado.camadaGrade = L.geoJSON(colecao, {
      style: function (feature) {
        return estiloCelula(feature, cortes);
      },
      onEachFeature: function (feature, layer) {
        var p = feature.properties;
        layer.bindTooltip(
          p.n + " sismo(s)<br>" + numero(p.densidade_km2, 2) + " por 1.000 km²",
          { sticky: true }
        );
        layer.on("click", function () {
          var centro = layer.getBounds().getCenter();
          carregarCelula(centro.lat, centro.lng);
        });
      },
    }).addTo(estado.mapa);

    if (estado.camadaGrade.getLayers().length) {
      estado.mapa.fitBounds(estado.camadaGrade.getBounds().pad(0.05), {
        maxZoom: 6,
      });
    }
  }

  function desenharLegenda(cortes) {
    if (!cortes.length) {
      el.legenda.innerHTML =
        '<h3>Densidade</h3><p class="legenda-linha">Nenhum evento no recorte.</p>';
      return;
    }
    var linhas = [];
    var corteAnterior = 0;
    cortes.forEach(function (corte, indice) {
      linhas.push(
        '<div class="legenda-linha"><span class="legenda-cor" style="background:' +
          CORES[indice] +
          '"></span><span>' +
          corteAnterior +
          " – " +
          corte +
          (estado.metrica === "normalizada" ? " /mil km²" : " eventos") +
          "</span></div>"
      );
      corteAnterior = corte + 1;
    });
    linhas.push(
      '<div class="legenda-linha"><span class="legenda-cor" style="background:' +
        CORES[Math.min(cortes.length, CORES.length - 1)] +
        '"></span><span>' +
        corteAnterior +
        " ou mais" +
        (estado.metrica === "normalizada" ? " /mil km²" : " eventos") +
        "</span></div>"
    );
    el.legenda.innerHTML = "<h3>Densidade</h3>" + linhas.join("");
  }

  /* --- Camada de calor -------------------------------------------------- */

  function alternarCamada() {
    if (estado.modo === "grade") {
      estado.modo = "calor";
      el.btnCamada.textContent = "Ver grade";
      carregarCalor();
    } else {
      estado.modo = "grade";
      el.btnCamada.textContent = "Ver calor";
      if (estado.camadaCalor) {
        estado.mapa.removeLayer(estado.camadaCalor);
        estado.camadaCalor = null;
      }
      if (estado.camadaGrade) {
        estado.camadaGrade.addTo(estado.mapa);
      }
    }
  }

  function carregarCalor() {
    var query = queryDosFiltros(estado.filtros);
    definirStatus("Carregando pontos para o mapa de calor…", "carregando");
    buscarJSON("/api/sismos?" + query)
      .then(function (dados) {
        var pontos = dados.sismos.features.map(function (feature) {
          var coordenadas = feature.geometry.coordinates;
          return [coordenadas[1], coordenadas[0], 0.6];
        });
        if (estado.camadaGrade) {
          estado.mapa.removeLayer(estado.camadaGrade);
        }
        if (estado.camadaCalor) {
          estado.mapa.removeLayer(estado.camadaCalor);
        }
        estado.camadaCalor = L.heatLayer(pontos, {
          radius: 20,
          blur: 24,
          maxZoom: 9,
          minOpacity: 0.35,
          gradient: {
            0.2: "#2c115f",
            0.4: "#721f81",
            0.6: "#b73779",
            0.8: "#f0705b",
            1.0: "#fec287",
          },
        }).addTo(estado.mapa);
        definirStatus(dados.total + " pontos no mapa de calor.");
      })
      .catch(function (erro) {
        definirStatus("Erro no mapa de calor: " + erro.message, "erro");
      });
  }

  /* --- Painel ----------------------------------------------------------- */

  function atualizarPainel(dados) {
    el.total.textContent = numero(dados.total);
    el.periodo.textContent =
      dados.total && dados.ano_min
        ? "de " + dados.ano_min + " a " + dados.ano_max
        : "sem eventos no recorte";

    if (dados.maior) {
      el.maior.innerHTML =
        "M " + numero(dados.maior.magnitude, 2) + " — " +
        texto(dados.maior.localidade, "local não informado") +
        (dados.maior.uf ? " (" + dados.maior.uf + ")" : "") +
        "<br><span class=\"rotulo\">" + dataCurta(dados.maior.data_hora) + "</span>";
    } else {
      el.maior.textContent = "—";
    }

    el.topUfs.innerHTML = "";
    (dados.top_ufs || []).forEach(function (item) {
      var li = document.createElement("li");
      var nome = document.createElement("span");
      nome.textContent = item.uf;
      var quantidade = document.createElement("span");
      quantidade.textContent = numero(item.n);
      li.appendChild(nome);
      li.appendChild(quantidade);
      el.topUfs.appendChild(li);
    });
    if (!el.topUfs.children.length) {
      el.topUfs.innerHTML = "<li>Sem eventos com UF no recorte.</li>";
    }

    el.cobertura.textContent =
      "Magnitude em " + numero(dados.cobertura.magnitude_pct, 1) + "% dos eventos; " +
      "profundidade em " + numero(dados.cobertura.profundidade_pct, 1) + "%.";

    atualizarSerie(dados.serie_anual || []);
    atualizarHistograma(dados.histograma_magnitude || []);
  }

  function atualizarSerie(serie) {
    var rotulos = serie.map(function (item) {
      return item.ano;
    });
    var valores = serie.map(function (item) {
      return item.n;
    });

    if (estado.graficoSerie) {
      estado.graficoSerie.data.labels = rotulos;
      estado.graficoSerie.data.datasets[0].data = valores;
      estado.graficoSerie.update("none");
      return;
    }
    if (!window.Chart) {
      return;
    }
    estado.graficoSerie = new Chart(el.serie, {
      type: "line",
      data: {
        labels: rotulos,
        datasets: [
          {
            label: "Eventos por ano",
            data: valores,
            borderColor: "#f0705b",
            backgroundColor: "rgba(240, 112, 91, 0.18)",
            fill: true,
            pointRadius: 0,
            borderWidth: 1.6,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxTicksLimit: 6, color: "#93a1b1" }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: "#93a1b1" }, grid: { color: "rgba(36,48,63,0.7)" } },
        },
      },
    });
  }

  function atualizarHistograma(faixas) {
    var rotulos = faixas.map(function (faixa) {
      return numero(faixa.de, 1) + "–" + numero(faixa.ate, 1);
    });
    var valores = faixas.map(function (faixa) {
      return faixa.n;
    });

    if (estado.graficoHistograma) {
      estado.graficoHistograma.data.labels = rotulos;
      estado.graficoHistograma.data.datasets[0].data = valores;
      estado.graficoHistograma.update("none");
      return;
    }
    if (!window.Chart) {
      return;
    }
    estado.graficoHistograma = new Chart(el.histograma, {
      type: "bar",
      data: {
        labels: rotulos,
        datasets: [
          {
            label: "Eventos",
            data: valores,
            backgroundColor: "#b73779",
            borderRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxTicksLimit: 8, color: "#93a1b1" }, grid: { display: false } },
          y: { beginAtZero: true, ticks: { color: "#93a1b1" }, grid: { color: "rgba(36,48,63,0.7)" } },
        },
      },
    });
  }

  /* --- Célula e ficha --------------------------------------------------- */

  function carregarCelula(lat, lon) {
    var filtros = Object.assign({}, estado.filtros, {
      lat: lat.toFixed(4),
      lon: lon.toFixed(4),
      celula: estado.celula,
    });
    definirStatus("Carregando eventos da célula…", "carregando");
    buscarJSON("/api/celula?" + queryDosFiltros(filtros))
      .then(function (dados) {
        el.tituloCelula.textContent =
          "Célula " + numero(lat, 2) + "°, " + numero(lon, 2) + "°";
        el.notaCelula.textContent =
          dados.total + " evento(s) nessa célula — clique em “Ficha” para os detalhes.";
        var corpo = el.tabelaCelula.querySelector("tbody");
        corpo.innerHTML = "";
        dados.eventos.forEach(function (evento) {
          var linha = document.createElement("tr");
          linha.innerHTML =
            "<td>" + dataCurta(evento.data_hora) + "</td>" +
            "<td>" + numero(evento.magnitude, 2) + "</td>" +
            "<td>" + numero(evento.profundidade_km, 1) + "</td>" +
            "<td>" + texto(evento.uf) + "</td>" +
            "<td>" + texto(evento.localidade) + "</td>" +
            "<td>" + texto(evento.fonte) + "</td>" +
            '<td><button type="button" class="link-ficha" data-id="' + evento.id + '">Ficha</button></td>';
          corpo.appendChild(linha);
        });
        corpo.querySelectorAll(".link-ficha").forEach(function (botao) {
          botao.addEventListener("click", function () {
            abrirFicha(botao.getAttribute("data-id"));
          });
        });
        if (!dados.eventos.length) {
          corpo.innerHTML = "<tr><td colspan=\"7\">Nenhum evento nessa célula.</td></tr>";
        }
        definirStatus(dados.total + " evento(s) na célula selecionada.");
      })
      .catch(function (erro) {
        definirStatus("Erro ao carregar a célula: " + erro.message, "erro");
      });
  }

  function abrirFicha(id) {
    buscarJSON("/api/evento?id=" + encodeURIComponent(id))
      .then(function (dados) {
        var evento = dados.evento;
        var campos = [
          ["Fonte", evento.fonte],
          ["ID na fonte", evento.evento_id],
          ["Data/hora (UTC)", dataCurta(evento.data_hora)],
          ["Ano", evento.ano],
          ["Latitude", numero(evento.lat, 5)],
          ["Longitude", numero(evento.lon, 5)],
          ["Magnitude", numero(evento.magnitude, 2)],
          ["Tipo de magnitude", evento.tipo_magnitude],
          ["Profundidade (km)", numero(evento.profundidade_km, 1)],
          ["Categoria (SISBRA)", evento.categoria],
          ["UF", evento.uf],
          ["Localidade", evento.localidade],
          ["Autor", evento.autor],
        ];
        el.fichaDados.innerHTML = campos
          .map(function (par) {
            return "<dt>" + par[0] + "</dt><dd>" + texto(par[1]) + "</dd>";
          })
          .join("");
        el.ficha.hidden = false;
        el.fecharFicha.focus();
      })
      .catch(function (erro) {
        definirStatus("Erro ao abrir a ficha: " + erro.message, "erro");
      });
  }

  /* --- Aplicação -------------------------------------------------------- */

  function aplicar() {
    var filtros = filtrosDoFormulario();
    estado.filtros = filtros;
    estado.metrica = filtros.metrica;
    estado.celula = Number(filtros.celula);
    escreverURL(filtros);

    var query = queryDosFiltros(filtros);
    definirStatus("Consultando o banco…", "carregando");

    Promise.all([
      buscarJSON("/api/densidade?" + query),
      buscarJSON("/api/estatisticas?" + query),
    ])
      .then(function (resultados) {
        var densidade = resultados[0];
        var estatisticas = resultados[1];

        var cortes = densidade.cortes;
        if (estado.metrica === "normalizada") {
          cortes = cortesDeValores(
            densidade.celulas.features.map(function (feature) {
              return Number(feature.properties.densidade_km2) || 0;
            })
          );
        }
        estado.cortes = cortes;

        if (estado.modo === "calor") {
          carregarCalor();
        }
        desenharGrade(densidade.celulas, cortes);
        desenharLegenda(cortes);
        atualizarPainel(estatisticas);

        if (!densidade.total_eventos) {
          definirStatus(
            "Nenhum sismo no período/filtro selecionado. Ajuste os filtros.",
            ""
          );
        } else {
          definirStatus(
            densidade.total_eventos + " eventos em " +
              densidade.celulas.features.length + " células de " +
              numero(densidade.celula, 2) + "°."
          );
        }
      })
      .catch(function (erro) {
        definirStatus("Erro: " + erro.message, "erro");
        el.total.textContent = "—";
        el.periodo.textContent = "—";
      });
  }

  function limpar() {
    el.form.reset();
    el.celula.value = "0.5";
    el.metrica.value = "contagem";
    if (estado.mapa) {
      aplicar();
    }
  }

  function iniciar() {
    el.status = $("status");
    el.legenda = $("legenda");
    el.total = $("total");
    el.periodo = $("periodo");
    el.maior = $("maior");
    el.topUfs = $("top-ufs");
    el.cobertura = $("cobertura");
    el.serie = $("serie");
    el.histograma = $("histograma");
    el.tituloCelula = $("titulo-celula");
    el.notaCelula = $("nota-celula");
    el.tabelaCelula = $("tabela-celula");
    el.ficha = $("ficha");
    el.fichaDados = $("ficha-dados");
    el.fecharFicha = $("fechar-ficha");
    el.btnCamada = $("btn-camada");

    el.anoIni = $("ano-ini");
    el.anoFim = $("ano-fim");
    el.magMin = $("mag-min");
    el.profMax = $("prof-max");
    el.fonte = $("fonte");
    el.uf = $("uf");
    el.categoria = $("categoria");
    el.celula = $("celula");
    el.metrica = $("metrica");

    criarMapa();

    document.getElementById("form-filtros").addEventListener("submit", function (evento) {
      evento.preventDefault();
      aplicar();
    });
    document.getElementById("btn-limpar").addEventListener("click", limpar);
    el.btnCamada.addEventListener("click", alternarCamada);
    el.fecharFicha.addEventListener("click", function () {
      el.ficha.hidden = true;
    });
    el.ficha.addEventListener("click", function (evento) {
      if (evento.target === el.ficha) {
        el.ficha.hidden = true;
      }
    });
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") {
        el.ficha.hidden = true;
      }
    });

    carregarOpcoes()
      .then(function () {
        preencherFormulario(lerURL());
        aplicar();
      })
      .catch(function (erro) {
        definirStatus(
          "Não foi possível carregar as opções do banco: " + erro.message,
          "erro"
        );
      });
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
