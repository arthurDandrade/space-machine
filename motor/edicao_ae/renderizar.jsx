// Renderiza uma comp de um projeto para MP4. Uso: definir RENDER = {aep, comp, saida, log, meia} antes deste código.
// meia: true = meia resolução (960x540), a prévia de rascunho do bloco, só para o QA e para olhar (2026-10-16): ~6x mais
// rápida que a cheia (bloco de 72 s: 75 s × ~8 min). Fica em 15 Mbps: a 5 Mbps a compressão engorda as letras e o QA
// mediu o texto ~10% mais alto (84 → 92 px); a 15 Mbps as alturas batem com as da prévia cheia.
(function () {
    var msg = [];
    // os nomes dos modelos de saída são traduzidos ("H.264 - Corresponder configurações de renderização - 15 Mbps" no
    // After em português): sem o nome em inglês, vale o H.264 de 15 Mbps do idioma que estiver
    function modeloH264(om) {
        var lista = om.templates;
        for (var i = 0; i < lista.length; i++) if (lista[i] === "H.264 - Match Render Settings - 15 Mbps") return lista[i];
        for (var j = 0; j < lista.length; j++) if (lista[j].indexOf("H.264") === 0 && lista[j].indexOf("15 Mbps") >= 0) return lista[j];
        throw new Error("modelo de saída H.264 de 15 Mbps não encontrado (modelos: " + lista.join(" | ") + ")");
    }
    try {
        app.open(new File(RENDER.aep));
        var comp = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === RENDER.comp) comp = it;
        }
        if (!comp) throw new Error("comp não encontrada: " + RENDER.comp);
        while (app.project.renderQueue.numItems > 0) app.project.renderQueue.item(1).remove();
        var rq = app.project.renderQueue.items.add(comp);
        var aviso = "";
        if (RENDER.meia) {
            // "Half" é o valor em inglês; no After traduzido, o mesmo em número (fator 2 em x e y)
            try { rq.setSetting("Resolution", "Half"); }
            catch (e1) {
                try { rq.setSetting("Resolution", {"x": 2, "y": 2}); }
                catch (e2) { aviso = " (aviso: a meia resolução não pegou, a prévia sai cheia: " + e2.toString() + ")"; }
            }
        }
        rq.outputModule(1).applyTemplate(modeloH264(rq.outputModule(1)));
        rq.outputModule(1).file = new File(RENDER.saida);
        app.project.renderQueue.render();
        msg.push("OK " + RENDER.saida + aviso);
    } catch (e) { msg.push("ERRO " + e.toString() + " linha " + e.line); }
    var f = new File(RENDER.log); f.open("w"); f.write(msg.join("\n")); f.close();
})();
