(function () {
  var video = document.getElementById("video-explicativo");
  var moldura = document.getElementById("video-moldura");
  var baixar = document.getElementById("baixar-video");
  if (!video || !moldura) return;

  var largura = window.matchMedia("(max-width: 820px)");
  var toque = window.matchMedia("(pointer: coarse)");
  var retrato = window.matchMedia("(orientation: portrait)");
  var atual = "";

  function usarMobile() {
    return largura.matches || (toque.matches && retrato.matches);
  }

  function ouvir(consulta, acao) {
    if (consulta.addEventListener) {
      consulta.addEventListener("change", acao);
    } else if (consulta.addListener) {
      consulta.addListener(acao);
    }
  }

  function trocar(fonte, capa, mobile) {
    var tempo = video.currentTime || 0;
    var tocando = !video.paused && !video.ended;

    moldura.classList.toggle("video-moldura--retrato", mobile);
    if (capa) video.poster = capa;
    if (baixar) baixar.href = fonte;
    if (fonte === atual) return;

    atual = fonte;
    video.src = fonte;
    video.load();

    function restaurar() {
      video.removeEventListener("loadedmetadata", restaurar);
      if (tempo > 0) {
        try {
          video.currentTime = tempo;
        } catch (erro) {
          /* alguns navegadores recusam antes do primeiro frame */
        }
      }
      if (tocando) video.play().catch(function () {});
    }

    video.addEventListener("loadedmetadata", restaurar);
  }

  function aplicar() {
    var mobile = usarMobile();
    trocar(
      mobile ? video.dataset.srcMobile : video.dataset.srcDesktop,
      mobile ? video.dataset.posterMobile : video.dataset.posterDesktop,
      mobile
    );
  }

  video.addEventListener("error", function () {
    if (atual !== video.dataset.srcMobile) return;
    trocar(video.dataset.srcDesktop, video.dataset.posterDesktop, false);
  });

  aplicar();
  ouvir(largura, aplicar);
  ouvir(toque, aplicar);
  ouvir(retrato, aplicar);

  var legendaCaixa = document.getElementById("legendas");
  var legendaTexto = document.getElementById("legenda");
  var botaoLegendas = document.getElementById("btn-legendas");
  var trackLegendas = video.textTracks && video.textTracks[0];
  var cues = [];
  var textoAtual = "";
  var legendaLigada = true;

  function lerTempo(valor) {
    var partes = valor.replace(",", ".").split(":");
    return (
      Number(partes[0]) * 3600 +
      Number(partes[1]) * 60 +
      Number(partes[2])
    );
  }

  function analisarVtt(texto) {
    return texto
      .replace(/\r/g, "")
      .split(/\n{2,}/)
      .map(function (bloco) {
        var linhas = bloco.trim().split("\n");
        var indice = linhas.findIndex(function (linha) {
          return linha.indexOf("-->") >= 0;
        });
        if (indice < 0) return null;
        var tempos = linhas[indice].split("-->");
        return {
          inicio: lerTempo(tempos[0].trim().split(/\s+/)[0]),
          fim: lerTempo(tempos[1].trim().split(/\s+/)[0]),
          texto: linhas.slice(indice + 1).join(" ").trim(),
        };
      })
      .filter(Boolean);
  }

  function atualizarLegenda() {
    if (!legendaLigada || !cues.length) return;

    var tempo = video.currentTime;
    var cue = null;
    for (var i = 0; i < cues.length; i++) {
      if (tempo >= cues[i].inicio && tempo < cues[i].fim) {
        cue = cues[i];
        break;
      }
    }

    var texto = cue ? cue.texto : "";
    if (texto === textoAtual) return;
    textoAtual = texto;

    if (!texto) {
      legendaCaixa.classList.add("legendas--ocultas");
      legendaTexto.textContent = "";
      return;
    }

    legendaCaixa.classList.remove("legendas--ocultas");
    legendaTexto.textContent = texto;
    legendaTexto.classList.remove("entrando");
    void legendaTexto.offsetWidth;
    legendaTexto.classList.add("entrando");
  }

  function aplicarLegendas() {
    botaoLegendas.setAttribute(
      "aria-pressed",
      legendaLigada ? "true" : "false"
    );
    if (!legendaLigada) {
      legendaCaixa.classList.add("legendas--ocultas");
      return;
    }
    textoAtual = "";
    atualizarLegenda();
  }

  if (legendaCaixa && legendaTexto && botaoLegendas) {
    botaoLegendas.addEventListener("click", function () {
      legendaLigada = !legendaLigada;
      aplicarLegendas();
    });

    video.addEventListener("timeupdate", atualizarLegenda);
    video.addEventListener("seeked", atualizarLegenda);
    video.addEventListener("play", atualizarLegenda);
    video.addEventListener("pause", atualizarLegenda);
    video.addEventListener("loadedmetadata", atualizarLegenda);

    fetch(video.dataset.legendas || "/static/videos/sismos-br.vtt")
      .then(function (resposta) {
        if (!resposta.ok) throw new Error("legendas indisponíveis");
        return resposta.text();
      })
      .then(function (texto) {
        cues = analisarVtt(texto);
        if (trackLegendas) trackLegendas.mode = "hidden";
        botaoLegendas.hidden = false;
        aplicarLegendas();
      })
      .catch(function () {
        if (trackLegendas) trackLegendas.mode = "showing";
      });

    function entrarTelaCheia() {
      if (trackLegendas) {
        trackLegendas.mode = legendaLigada ? "showing" : "hidden";
      }
      legendaCaixa.classList.add("legendas--ocultas");
    }

    function sairTelaCheia() {
      legendaCaixa.classList.remove("legendas--ocultas");
      if (trackLegendas) trackLegendas.mode = "hidden";
      aplicarLegendas();
    }

    function aoMudarTelaCheia() {
      if (document.fullscreenElement === video) {
        entrarTelaCheia();
      } else {
        sairTelaCheia();
      }
    }

    document.addEventListener("fullscreenchange", aoMudarTelaCheia);
    video.addEventListener("webkitbeginfullscreen", entrarTelaCheia);
    video.addEventListener("webkitendfullscreen", sairTelaCheia);

    (function lacoLegendas() {
      if (!video.paused) atualizarLegenda();
      requestAnimationFrame(lacoLegendas);
    })();
  }
})();
