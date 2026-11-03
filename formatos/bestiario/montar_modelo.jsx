// Bestiário: cria as layers de DADOS.layers (footage e textos) sobre fundo preto, com vinheta e grão leve.
// Mesma base do modelo do explained (chaves, textos que cabem em max_w), mais: blend "screen" (gravura e ilustração
// em traço claro: o preto da imagem some no fundo) e "pb" (vídeo real em preto e branco, com mais contraste).
(function () {
    var LOG = [];
    function log(s) { LOG.push(s); }
    function salvarLog() { var f = new File(DADOS.log); f.encoding = "UTF-8"; f.open("w"); f.write(LOG.join("\n")); f.close(); }

    function nDims(prop) {
        var t = prop.propertyValueType;
        if (t === PropertyValueType.TwoD || t === PropertyValueType.TwoD_SPATIAL) return 2;
        if (t === PropertyValueType.ThreeD || t === PropertyValueType.ThreeD_SPATIAL) return 3;
        return 1;
    }
    function rep(e, n) { var a = []; for (var i = 0; i < n; i++) a.push(e); return a; }
    function ehEspacial(prop) {
        return prop.propertyValueType === PropertyValueType.TwoD_SPATIAL || prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL;
    }
    // keys: [[t, valor, easeArray?]]
    function chaves(prop, keys, linear, escala) {
        for (var i = 0; i < keys.length; i++) {
            var v = keys[i][1];
            if (escala) v = [v, v, 100];
            prop.setValueAtTime(keys[i][0], v);
        }
        var n = ehEspacial(prop) ? 1 : nDims(prop);
        for (var j = 0; j < keys.length; j++) {
            var idx = prop.nearestKeyIndex(keys[j][0]);
            var e = keys[j][2];
            if (linear || !e) {
                prop.setInterpolationTypeAtKey(idx, KeyframeInterpolationType.LINEAR, KeyframeInterpolationType.LINEAR);
                continue;
            }
            prop.setTemporalEaseAtKey(idx, rep(new KeyframeEase(e[0], Math.max(0.1, e[1])), n),
                                           rep(new KeyframeEase(e[2], Math.max(0.1, e[3])), n));
        }
        if (ehEspacial(prop)) for (var k = 1; k <= prop.numKeys; k++) prop.setSpatialTangentsAtKey(k, [0, 0, 0], [0, 0, 0]);
    }
    function sombra(L, o) {
        var ds = L.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
        ds.property(1).setValue(DADOS.cor_sombra || [0, 0, 0]); ds.property(2).setValue(o.op); ds.property(3).setValue(180);
        ds.property(4).setValue(o.dist); ds.property(5).setValue(Math.min(250, o.soft));
    }
    function elipse(W, H, rx, ry) {
        var el = new Shape(), kx = rx * 0.5523, ky = ry * 0.5523;
        el.vertices = [[W / 2, H / 2 - ry], [W / 2 + rx, H / 2], [W / 2, H / 2 + ry], [W / 2 - rx, H / 2]];
        el.inTangents = [[-kx, 0], [0, -ky], [kx, 0], [0, ky]];
        el.outTangents = [[kx, 0], [0, ky], [-kx, 0], [0, -ky]];
        el.closed = true;
        return el;
    }
    var cache = {}, pastaAssets;
    function importar(c) {
        if (cache[c]) return cache[c];
        var it = app.project.importFile(new ImportOptions(new File(c)));
        it.parentFolder = pastaAssets; cache[c] = it; return it;
    }

    try {
        if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.newProject();
        app.beginUndoGroup("Montar bloco (bestiário)");
        pastaAssets = app.project.items.addFolder("assets");
        var W = DADOS.w, H = DADOS.h;
        var comp = app.project.items.addComp(DADOS.nome, W, H, 1, DADOS.dur, DADOS.fps);
        comp.bgColor = DADOS.cor_fundo;

        var fundo = comp.layers.addSolid(DADOS.cor_fundo, "Fundo", W, H, 1, DADOS.dur);
        var aud = comp.layers.add(importar(DADOS.audio)); aud.name = "Narração";
        aud.startTime = -(DADOS.audio_offset || 0);

        var criadas = {};
        for (var i = 0; i < DADOS.layers.length; i++) {
            var d = DADOS.layers[i], L;
            try {
                if (d.kind === "footage") {
                    L = comp.layers.add(importar(d.file));
                    L.startTime = d.start;
                    L.anchorPoint.setValue([d.src[0] / 2, d.src[1] / 2]);
                    if (d.timeremap) L.timeRemapEnabled = true;
                    if (d.blend === "screen") L.blendingMode = BlendingMode.SCREEN;
                    if (d.pb) {
                        var fx = L.property("ADBE Effect Parade");
                        fx.addProperty("ADBE Tint");                       // padrão: preto→preto, branco→branco, 100%
                        var bc = fx.addProperty("ADBE Brightness & Contrast 2");
                        bc.property(2).setValue(22);                              // só contraste: escurecer apagava o mar escuro (teste 2026-11-03)
                    }
                } else {
                    L = comp.layers.addText(d.text);
                    var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
                    var td = tp.value;
                    td.font = d.font || DADOS.fonte; td.fontSize = 100; td.applyFill = true; td.fillColor = d.color;
                    td.applyStroke = false; td.justification = ParagraphJustification.CENTER_JUSTIFY; td.leading = 112;
                    tp.setValue(td);
                    var r = L.sourceRectAtTime(0, false);
                    var tam = Math.min(d.max_size, 100 * d.max_w / r.width);
                    td = tp.value; td.fontSize = tam; td.leading = tam * 1.12; tp.setValue(td);
                    r = L.sourceRectAtTime(0, false);
                    var ay = d.anchor_mode === "top" ? r.top : (d.anchor_mode === "bottom" ? r.top + r.height : r.top + r.height / 2);
                    L.anchorPoint.setValue([r.left + r.width / 2, ay]);
                    if (d.shadow) sombra(L, d.shadow);
                }
                L.name = d.name;
                if (d.pos) L.position.setValue(d.pos);
                if (d.pos_keys) chaves(L.position, d.pos_keys);
                if (d.scale !== undefined) L.scale.setValue([d.scale, d.scale, 100]);
                if (d.scale_keys) chaves(L.scale, d.scale_keys, d.linear_scale, true);
                if (d.opacity_keys) chaves(L.opacity, d.opacity_keys, true);
                L.inPoint = d["in"];
                L.outPoint = d.out;
                criadas[d.id] = L;
            } catch (eL) {
                log("ERRO layer " + d.id + " (" + d.name + "): " + eL.toString() + " linha " + eL.line);
            }
        }

        // vinheta (bordas mais escuras) e grão leve por cima de tudo; o vídeo final ainda põe o ruído dele
        var vin = comp.layers.addSolid([0, 0, 0], "Vinheta", W, H, 1, DADOS.dur);
        var m = vin.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        m.property("ADBE Mask Shape").setValue(elipse(W, H, W / 2 + 120, H / 2 + 160));
        m.property("ADBE Mask Feather").setValue([520, 520]); m.inverted = true;
        vin.opacity.setValue(70);
        var grao = comp.layers.addSolid([0.5, 0.5, 0.5], "Grão", W, H, 1, DADOS.dur);
        grao.adjustmentLayer = true;
        var ns = grao.property("ADBE Effect Parade").addProperty("ADBE Noise");
        ns.property(1).setValue(3); ns.property(2).setValue(0);          // 3%, sem cor (grão de filme P&B)
        fundo.moveToEnd();
        fundo.locked = true; vin.locked = true; grao.locked = true;
        app.endUndoGroup();
        comp.openInViewer();
        app.project.save(new File(DADOS.salvar));
        log("OK comp=" + comp.name + " layers=" + comp.numLayers);
    } catch (e) {
        log("ERRO GERAL: " + e.toString() + " linha " + e.line);
    }
    salvarLog();
})();
