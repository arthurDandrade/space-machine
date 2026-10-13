// Editor v2: cria as layers descritas em DADOS.layers (nulls, footage, textos) com hierarquia por id.
(function () {
    var LOG = [];
    function log(s) { LOG.push(s); }
    function salvarLog() { var f = new File(DADOS.log); f.encoding = "UTF-8"; f.open("w"); f.write(LOG.join("\n")); f.close(); }

    function nDims(prop) {
        var t = prop.propertyValueType;
        if (t === PropertyValueType.TwoD) return 2;
        if (t === PropertyValueType.ThreeD) return 3;
        return 1;
    }
    function rep(e, n) { var a = []; for (var i = 0; i < n; i++) a.push(e); return a; }
    function ehEspacial(prop) {
        return prop.propertyValueType === PropertyValueType.TwoD_SPATIAL || prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL;
    }
    // keys: [[t, valor, easeArray?]]
    function chaves(prop, keys, linear, escala) {
        var n = nDims(prop);
        for (var i = 0; i < keys.length; i++) {
            var v = keys[i][1];
            if (escala) v = [v, v, 100];
            prop.setValueAtTime(keys[i][0], v);
        }
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
    function retArred(x0, y0, x1, y1, r) {
        var k = r * 0.5523, s = new Shape();
        s.vertices = [[x0 + r, y0], [x1 - r, y0], [x1, y0 + r], [x1, y1 - r], [x1 - r, y1], [x0 + r, y1], [x0, y1 - r], [x0, y0 + r]];
        s.inTangents = [[-k, 0], [0, 0], [0, -k], [0, 0], [k, 0], [0, 0], [0, k], [0, 0]];
        s.outTangents = [[0, 0], [k, 0], [0, 0], [0, k], [0, 0], [-k, 0], [0, 0], [0, -k]];
        s.closed = true;
        return s;
    }
    function sombra(L, o) {
        var ds = L.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
        ds.property(1).setValue(DADOS.cor_sombra || [0, 0, 0]); ds.property(2).setValue(o.op); ds.property(3).setValue(180);
        ds.property(4).setValue(o.dist); ds.property(5).setValue(Math.min(250, o.soft));
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
        app.beginUndoGroup("Montar bloco v2");
        pastaAssets = app.project.items.addFolder("assets");
        var comp = app.project.items.addComp(DADOS.nome, 1920, 1080, 1, DADOS.dur, DADOS.fps);
        comp.motionBlur = true; comp.shutterAngle = 180; comp.bgColor = DADOS.cor_fundo;

        // fundo de papel
        var fundo = comp.layers.addSolid(DADOS.cor_fundo, "Fundo", 1920, 1080, 1, DADOS.dur);
        if (DADOS.fundo_imagem && new File(DADOS.fundo_imagem.file).exists) {   // papel com adesivos nos cantos
            var fi = comp.layers.add(importar(DADOS.fundo_imagem.file));
            fi.name = "Fundo imagem"; fi.outPoint = DADOS.dur;
            fi.opacity.setValue(DADOS.fundo_imagem.opacidade);
            fi.scale.setValue([DADOS.fundo_imagem.escala, DADOS.fundo_imagem.escala]);
            fi.position.setValue(DADOS.fundo_imagem.pos);
        }
        var tex = comp.layers.addSolid([0.5, 0.5, 0.5], "Textura papel", 1920, 1080, 1, DADOS.dur);
        var fn = tex.property("ADBE Effect Parade").addProperty("ADBE Fractal Noise");
        fn.property("Contrast").setValue(260); fn.property("Brightness").setValue(-10);
        fn.property("ADBE Fractal Noise-0010").setValue(18);
        tex.blendingMode = BlendingMode.SOFT_LIGHT; tex.opacity.setValue(14);
        var vin = comp.layers.addSolid(DADOS.cor_sombra, "Vinheta", 1920, 1080, 1, DADOS.dur);
        var m = vin.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        var el = new Shape(), kx = 1150 * 0.5523, ky = 760 * 0.5523;
        el.vertices = [[960, -220], [2110, 540], [960, 1300], [-190, 540]];
        el.inTangents = [[-kx, 0], [0, -ky], [kx, 0], [0, ky]];
        el.outTangents = [[kx, 0], [0, ky], [-kx, 0], [0, -ky]];
        el.closed = true;
        m.property("ADBE Mask Shape").setValue(el); m.property("ADBE Mask Feather").setValue([650, 650]); m.inverted = true;
        vin.opacity.setValue(13);

        var aud = comp.layers.add(importar(DADOS.audio)); aud.name = "Narração";
        aud.startTime = -(DADOS.audio_offset || 0);   // bloco que começa no meio da narração

        var criadas = {};
        var caixas = [];
        for (var i = 0; i < DADOS.layers.length; i++) {
            var d = DADOS.layers[i], L;
            try {
                if (d.kind === "null") {
                    L = comp.layers.addNull(DADOS.dur);
                    L.enabled = false;
                    L.anchorPoint.setValue([0, 0]);
                } else if (d.kind === "footage") {
                    L = comp.layers.add(importar(d.file));
                    L.startTime = d.start;
                    L.anchorPoint.setValue([d.src[0] / 2, d.src[1] / 2]);
                    if (d.crop) {
                        var x0 = (d.src[0] - d.crop[0]) / 2, y0 = (d.src[1] - d.crop[1]) / 2;
                        var mk = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
                        mk.property("ADBE Mask Shape").setValue(retArred(x0, y0, x0 + d.crop[0], y0 + d.crop[1], d.radius));
                    }
                    if (d.shadow) sombra(L, d.shadow);
                    L.motionBlur = true;
                    if (d.timeremap) L.timeRemapEnabled = true;
                    if (d.blur_keys) {   // B11: composição de trás desfoca
                        var gb = L.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
                        chaves(gb.property(1), d.blur_keys, true);
                    }
                } else {
                    L = comp.layers.addText(d.text);
                    var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
                    var td = tp.value;
                    td.font = d.font || DADOS.fonte; td.fontSize = 100; td.applyFill = true; td.fillColor = d.color;
                    td.applyStroke = false; td.justification = ParagraphJustification.CENTER_JUSTIFY; td.leading = 108;
                    tp.setValue(td);
                    var r = L.sourceRectAtTime(0, false);
                    var tam = Math.min(d.max_size, 100 * d.max_w / r.width);
                    td = tp.value; td.fontSize = tam; td.leading = tam * 1.08; tp.setValue(td);
                    r = L.sourceRectAtTime(0, false);
                    var ay = d.anchor_mode === "top" ? r.top : (d.anchor_mode === "bottom" ? r.top + r.height : r.top + r.height / 2);
                    L.anchorPoint.setValue([r.left + r.width / 2, ay]);
                    if (d.shadow) sombra(L, d.shadow);
                    if (d.box) {
                        // caixa da identidade (fundo azul atrás do texto), presa ao mesmo pai do texto
                        var rb = L.sourceRectAtTime(0, false);
                        var px = tam * 0.20, py = tam * 0.10;
                        var C = comp.layers.addShape();
                        var g = C.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
                        var rc = g.property("ADBE Vectors Group").addProperty("ADBE Vector Shape - Rect");
                        rc.property("ADBE Vector Rect Size").setValue([rb.width + 2 * px, rb.height + 2 * py]);
                        var fl = g.property("ADBE Vectors Group").addProperty("ADBE Vector Graphic - Fill");
                        fl.property("ADBE Vector Fill Color").setValue(d.box);
                        C.name = "caixa " + d.name;
                        caixas.push([C, L, d]);
                    }
                    if (d.blur_keys) chaves(L.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2").property(1), d.blur_keys, true);
                }
                L.name = d.name;
                if (d.parent !== null && d.parent !== undefined) L.parent = criadas[d.parent];
                if (d.anchor) L.anchorPoint.setValue(d.anchor);
                if (d.pos) L.position.setValue(d.pos);
                if (d.pos_keys) chaves(L.position, d.pos_keys);
                if (d.rot_keys) chaves(L.rotation, d.rot_keys);   // M5: globo rolando
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
        // caixas: mesmo pai, posição, tempo e fade do texto; logo abaixo dele na pilha
        for (var cx = 0; cx < caixas.length; cx++) {
            var C = caixas[cx][0], T = caixas[cx][1], dd = caixas[cx][2];
            C.parent = T.parent;
            C.position.setValue(dd.pos);
            C.inPoint = dd["in"]; C.outPoint = dd.out;
            if (dd.opacity_keys) chaves(C.opacity, dd.opacity_keys, true);
            C.moveAfter(T);
        }
        vin.moveToEnd(); tex.moveToEnd(); fundo.moveToEnd();
        fundo.locked = true; tex.locked = true; vin.locked = true;
        app.endUndoGroup();
        comp.openInViewer();
        app.project.save(new File(DADOS.salvar));
        log("OK comp=" + comp.name + " layers=" + comp.numLayers);
    } catch (e) {
        log("ERRO GERAL: " + e.toString() + " linha " + e.line);
    }
    salvarLog();
})();
