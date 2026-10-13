// Renderiza a comp do bloco aberto para MP4. Uso: definir RENDER = {aep, comp, saida, log} antes deste código.
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
        rq.outputModule(1).applyTemplate("H.264 - Match Render Settings - 15 Mbps");
        rq.outputModule(1).file = new File(RENDER.saida);
        app.project.renderQueue.render();
        msg.push("OK " + RENDER.saida);
    } catch (e) { msg.push("ERRO " + e.toString() + " linha " + e.line); }
    var f = new File(RENDER.log); f.open("w"); f.write(msg.join("\n")); f.close();
})();
