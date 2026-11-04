// Bestiário (animação 2D): cria as layers de DADOS.layers, na ordem, cada uma por cima da anterior.
// Tipos de layer: "null", "solid" (com degradê opcional), "shape" (retângulos, elipses e linhas, com traço que se
// desenha), "footage" (imagem/vídeo) e "text" (tamanho fixo, encolhe para caber em max_w).
// Todos aceitam pai, posição, escala, rotação, opacidade (com chaves) e expressões (movimento contínuo: a criatura
// oscilando, os raios de luz balançando, as partículas subindo).
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
    // keys: [[t, valor, ease?]]; ease = [vel_entrada, influência_entrada, vel_saída, influência_saída]
    function chaves(prop, keys, linear, escala) {
        for (var i = 0; i < keys.length; i++) {
            var v = keys[i][1];
            if (escala && !(v instanceof Array)) v = [v, v, 100];
            else if (escala && v.length === 2) v = [v[0], v[1], 100];
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
        ds.property(1).setValue([0, 0, 0]); ds.property(2).setValue(o.op); ds.property(3).setValue(o.dir || 135);
        ds.property(4).setValue(o.dist); ds.property(5).setValue(Math.min(250, o.soft));
    }
    function caminho(pts, fechado) {
        var s = new Shape();
        s.vertices = pts; s.closed = !!fechado;
        return s;
    }
    var cache = {}, pastaAssets;
    function importar(c) {
        if (cache[c]) return cache[c];
        var it = app.project.importFile(new ImportOptions(new File(c)));
        it.parentFolder = pastaAssets; cache[c] = it; return it;
    }
    function formas(L, itens, trim) {
        var raiz = L.property("ADBE Root Vectors Group");
        for (var i = 0; i < itens.length; i++) {
            var it = itens[i];
            var g = raiz.addProperty("ADBE Vector Group");
            var v = g.property("ADBE Vectors Group");
            if (it.t === "rect") {
                var r = v.addProperty("ADBE Vector Shape - Rect");
                r.property("ADBE Vector Rect Size").setValue(it.size);
                r.property("ADBE Vector Rect Position").setValue(it.pos || [0, 0]);
                r.property("ADBE Vector Rect Roundness").setValue(it.radius || 0);
            } else if (it.t === "ellipse") {
                var el = v.addProperty("ADBE Vector Shape - Ellipse");
                el.property("ADBE Vector Ellipse Size").setValue(it.size);
                el.property("ADBE Vector Ellipse Position").setValue(it.pos || [0, 0]);
            } else {
                var p = v.addProperty("ADBE Vector Shape - Group");
                p.property("ADBE Vector Shape").setValue(caminho(it.pts, it.closed));
            }
            if (it.arco) {           // só um trecho da elipse (o arco do sonar): início e fim em %
                var ta = v.addProperty("ADBE Vector Filter - Trim");
                ta.property("ADBE Vector Trim Start").setValue(it.arco[0]);
                ta.property("ADBE Vector Trim End").setValue(it.arco[1]);
            } else if (trim && it.trim !== false) {
                var tr = v.addProperty("ADBE Vector Filter - Trim");
                chaves(tr.property("ADBE Vector Trim End"), trim, false);
            }
            if (it.fill) {
                var f = v.addProperty("ADBE Vector Graphic - Fill");
                f.property("ADBE Vector Fill Color").setValue(it.fill);
                if (it.fill_op !== undefined) f.property("ADBE Vector Fill Opacity").setValue(it.fill_op);
            }
            if (it.stroke) {
                var s = v.addProperty("ADBE Vector Graphic - Stroke");
                s.property("ADBE Vector Stroke Color").setValue(it.stroke);
                s.property("ADBE Vector Stroke Width").setValue(it.sw || 2);
                s.property("ADBE Vector Stroke Line Cap").setValue(2);
                if (it.stroke_op !== undefined) s.property("ADBE Vector Stroke Opacity").setValue(it.stroke_op);
                if (it.tracejado) {      // traço tracejado: [traço, espaço] em px
                    var ds = s.property("ADBE Vector Stroke Dashes");
                    ds.addProperty("ADBE Vector Stroke Dash 1").setValue(it.tracejado[0]);
                    ds.addProperty("ADBE Vector Stroke Gap 1").setValue(it.tracejado[1]);
                }
            }
        }
    }

    try {
        if (app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
        app.newProject();
        app.beginUndoGroup("Montar bloco (bestiário)");
        pastaAssets = app.project.items.addFolder("assets");
        var W = DADOS.w, H = DADOS.h;
        var comp = app.project.items.addComp(DADOS.nome, W, H, 1, DADOS.dur, DADOS.fps);
        comp.bgColor = DADOS.cor_fundo;
        comp.motionBlur = true;
        var aud = comp.layers.add(importar(DADOS.audio)); aud.name = "Narração";
        aud.startTime = -(DADOS.audio_offset || 0);

        var criadas = {};
        for (var i = 0; i < DADOS.layers.length; i++) {
            var d = DADOS.layers[i], L;
            try {
                if (d.kind === "null") {
                    L = comp.layers.addNull(DADOS.dur);
                    L.enabled = false;
                    L.anchorPoint.setValue([0, 0]);
                } else if (d.kind === "solid") {
                    L = comp.layers.addSolid(d.color, d.name, W, H, 1, DADOS.dur);
                    if (d.ramp) {
                        var rp = L.property("ADBE Effect Parade").addProperty("ADBE Ramp");
                        rp.property(1).setValue(d.ramp[0]); rp.property(2).setValue(d.ramp[1]);
                        rp.property(3).setValue(d.ramp[2]); rp.property(4).setValue(d.ramp[3]);
                    }
                } else if (d.kind === "shape") {
                    L = comp.layers.addShape();
                    formas(L, d.items, d.trim_keys);
                    L.anchorPoint.setValue([0, 0]);
                } else if (d.kind === "footage") {
                    L = comp.layers.add(importar(d.file));
                    L.startTime = d.start;
                    L.anchorPoint.setValue([d.src[0] / 2, d.src[1] / 2]);
                    if (d.timeremap) L.timeRemapEnabled = true;
                    if (d.motion_blur) L.motionBlur = true;
                } else {
                    L = comp.layers.addText(d.text);
                    var tp = L.property("ADBE Text Properties").property("ADBE Text Document");
                    var td = tp.value;
                    td.font = d.font; td.fontSize = d.size || 100; td.applyFill = true; td.fillColor = d.color;
                    td.applyStroke = false; td.tracking = d.tracking || 0;
                    td.justification = d.justify === "left" ? ParagraphJustification.LEFT_JUSTIFY :
                        (d.justify === "right" ? ParagraphJustification.RIGHT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY);
                    td.leading = (d.size || 100) * 1.15;
                    tp.setValue(td);
                    var r0 = L.sourceRectAtTime(0, false);
                    if (d.max_w && r0.width > d.max_w) {
                        var tam = (d.size || 100) * d.max_w / r0.width;
                        td = tp.value; td.fontSize = tam; td.leading = tam * 1.15; tp.setValue(td);
                    }
                    var r = L.sourceRectAtTime(0, false);
                    var ax = d.justify === "left" ? r.left : (d.justify === "right" ? r.left + r.width : r.left + r.width / 2);
                    var ay = d.anchor_mode === "top" ? r.top : (d.anchor_mode === "bottom" ? r.top + r.height : r.top + r.height / 2);
                    L.anchorPoint.setValue([ax, ay]);
                }
                L.name = d.name;
                if (d.grade) {           // a criatura dentro da água: tingida pela luz do fundo, mais escura, borda acesa
                    var fxg = L.property("ADBE Effect Parade");
                    if (d.grade.tint) {
                        var tn = fxg.addProperty("ADBE Tint");
                        tn.property(1).setValue(d.grade.tint[0]); tn.property(2).setValue(d.grade.tint[1]);
                        tn.property(3).setValue(d.grade.tint[2]);
                    }
                    if (d.grade.brilho) fxg.addProperty("ADBE Brightness & Contrast 2").property(1).setValue(d.grade.brilho);
                    if (d.grade.borda) {
                        var bv = fxg.addProperty("ADBE Bevel Alpha");
                        bv.property(1).setValue(d.grade.borda[0]); bv.property(2).setValue(-45);
                        bv.property(3).setValue(d.grade.borda[1]); bv.property(4).setValue(d.grade.borda[2]);
                    }
                }
                if (d.ondula) {          // o corpo ondula de leve (altura, largura da onda, velocidade)
                    var ww = L.property("ADBE Effect Parade").addProperty("ADBE Wave Warp");
                    ww.property(2).setValue(d.ondula[0]); ww.property(3).setValue(d.ondula[1]);
                    ww.property(5).setValue(d.ondula[2]);      // direção: a padrão (90°), a onda corre na horizontal
                }
                if (d.vinheta) {         // bordas escuras: elipse invertida e esfumada
                    var mk = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
                    var rx = d.vinheta[0], ry = d.vinheta[1], kx = rx * 0.5523, ky = ry * 0.5523, el = new Shape();
                    el.vertices = [[W / 2, H / 2 - ry], [W / 2 + rx, H / 2], [W / 2, H / 2 + ry], [W / 2 - rx, H / 2]];
                    el.inTangents = [[-kx, 0], [0, -ky], [kx, 0], [0, ky]];
                    el.outTangents = [[kx, 0], [0, ky], [-kx, 0], [0, -ky]];
                    el.closed = true;
                    mk.property("ADBE Mask Shape").setValue(el);
                    mk.property("ADBE Mask Feather").setValue([d.vinheta[2], d.vinheta[2]]); mk.inverted = true;
                }
                if (d.blend === "screen") L.blendingMode = BlendingMode.SCREEN;
                if (d.blend === "add") L.blendingMode = BlendingMode.ADD;
                if (d.shadow) sombra(L, d.shadow);
                if (d.blur) L.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2").property(1).setValue(d.blur);
                if (d.parent !== null && d.parent !== undefined) L.parent = criadas[d.parent];
                if (d.anchor) L.anchorPoint.setValue(d.anchor);
                if (d.pos) L.position.setValue(d.pos);
                if (d.pos_keys) chaves(L.position, d.pos_keys);
                if (d.rot !== undefined) L.rotation.setValue(d.rot);
                if (d.rot_keys) chaves(L.rotation, d.rot_keys);
                if (d.scale !== undefined) L.scale.setValue(d.scale instanceof Array ? d.scale : [d.scale, d.scale]);
                if (d.scale_keys) chaves(L.scale, d.scale_keys, d.linear_scale, true);
                if (d.opacity !== undefined) L.opacity.setValue(d.opacity);
                if (d.opacity_keys) chaves(L.opacity, d.opacity_keys, true);
                if (d.expr) {
                    if (d.expr.pos) L.position.expression = d.expr.pos;
                    if (d.expr.rot) L.rotation.expression = d.expr.rot;
                    if (d.expr.scale) L.scale.expression = d.expr.scale;
                    if (d.expr.opacity) L.opacity.expression = d.expr.opacity;
                }
                L.inPoint = d["in"];
                L.outPoint = d.out;
                criadas[d.id] = L;
            } catch (eL) {
                log("ERRO layer " + d.id + " (" + d.name + "): " + eL.toString() + " linha " + eL.line);
            }
        }
        aud.moveToEnd();
        app.endUndoGroup();
        comp.openInViewer();
        app.project.save(new File(DADOS.salvar));
        log("OK comp=" + comp.name + " layers=" + comp.numLayers);
    } catch (e) {
        log("ERRO GERAL: " + e.toString() + " linha " + e.line);
    }
    salvarLog();
})();
