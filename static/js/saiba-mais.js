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
})();
