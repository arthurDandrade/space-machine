// Renderiza uma comp de um projeto para MP4. Uso: definir RENDER = {aep, comp, saida, log, meia} antes deste código.
// meia: true = meia resolução (960x540), a prévia de rascunho do bloco, só para o QA e para olhar (2026-10-16): ~6x mais
// rápida que a cheia (bloco de 72 s: 75 s × ~8 min). Fica em 15 Mbps: a 5 Mbps a compressão engorda as letras e o QA
// mediu o texto ~10% mais alto (84 → 92 px); a 15 Mbps as alturas batem com as da prévia cheia.
(function () {
    var msg = [];
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
        if (RENDER.meia) rq.setSetting("Resolution", "Half");
        rq.outputModule(1).applyTemplate("H.264 - Match Render Settings - 15 Mbps");
        rq.outputModule(1).file = new File(RENDER.saida);
        app.project.renderQueue.render();
        msg.push("OK " + RENDER.saida);
    } catch (e) { msg.push("ERRO " + e.toString() + " linha " + e.line); }
    var f = new File(RENDER.log); f.open("w"); f.write(msg.join("\n")); f.close();
})();
