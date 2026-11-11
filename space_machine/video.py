"""O vídeo inteiro como um projeto só (fluxo "video" do explained, 2026-11-05).

Antes cada tópico do roteiro era um bloco com storyboard, busca, escolha, edição no After, prévia e entrega próprios,
e o vídeo final juntava os blocos. Cada bloco era pensado sozinho, então o vídeo saía repetitivo (todo bloco com a
mesma cara). Agora os tópicos são CAPÍTULOS: a narração e a transcrição continuam por capítulo (<vídeo>/blocos/NN/,
para refazer só a voz de um), e daí em diante tudo é do vídeo inteiro, em <vídeo>/producao/ — uma pasta com a mesma
cara da de um bloco, então o motor (compilar_cenas, storyboard.py, buscar, escolher, gerar_ae2, qa_bloco) roda nela
do mesmo jeito:

  narracao.wav            as narrações dos capítulos emendadas (0,2 s antes da 1ª palavra, 0,6 s depois da última)
  roteiro.txt             os roteiros dos capítulos, em ordem
  _work/palavras.json     as palavras de todos os capítulos, no tempo do áudio junto
  _work/transcricao.txt   idem, com "## Capítulo NN: Nome" antes de cada capítulo
  capitulos.json          [{"nn", "nome", "tipo": "cold_open" | "capitulo" | "mudo", "ini", "fim"}] (s no áudio junto)
  cenas.json              o storyboard do vídeo inteiro: um item por capítulo (id = NN)
  edicao/                 plano_edicao_NN / plano_render_NN de cada capítulo, os pedaços renderizados e o QA

O vídeo pronto é um MP4 só (final/final.mp4); por dentro, cada capítulo é renderizado à parte e em paralelo (e só é
renderizado de novo se mudou), e o FFmpeg emenda sem recomprimir.
"""
import json
import re
import subprocess
from pathlib import Path

from .canal import gravar_json, ler_json

CABECA, RABO = 0.2, 0.6          # s de áudio antes da 1ª e depois da última palavra de cada capítulo
MARCA_COLD_OPEN = "#! cold open"
MARCA_CAPITULO = "#! capítulo"


def pasta(vd):
    return Path(vd) / "producao"


def fluxo_video(vd):
    """O vídeo nasceu no fluxo novo (estudio_video.json › fluxo = "video")? Os outros seguem bloco a bloco."""
    return (ler_json(Path(vd) / "estudio_video.json", {}) or {}).get("fluxo") == "video"


def capitulos(vd):
    """As pastas dos capítulos (<vídeo>/blocos/NN), em ordem."""
    b = Path(vd) / "blocos"
    return sorted(p for p in b.iterdir() if p.is_dir() and p.name.isdigit()) if b.is_dir() else []


def _tipo(roteiro):
    if MARCA_COLD_OPEN in roteiro:
        return "cold_open"
    if MARCA_CAPITULO in roteiro:
        return "mudo"
    return "capitulo"


def _nome(roteiro, nn):
    return next((l.lstrip("# ").strip() for l in roteiro.splitlines() if l.startswith("# ")), f"Capítulo {nn}")


def _duracao(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _narracao(b):
    return next((p for p in sorted(b.glob("narracao.*")) if p.stem == "narracao"), None)


def faltam(vd):
    """Capítulos sem narração ou sem transcrição: [(nn, o que falta)]."""
    out = []
    for b in capitulos(vd):
        if not _narracao(b):
            out.append((b.name, "narração"))
        elif not (b / "_work" / "palavras.json").exists():
            out.append((b.name, "transcrição"))
    return out


def atualizado(vd):
    """O projeto do vídeo já tem o áudio e as palavras de todos os capítulos, mais novos que eles?"""
    p = pasta(vd) / "capitulos.json"
    if not p.exists() or not (pasta(vd) / "narracao.wav").exists():
        return False
    juntos = [c["nn"] for c in ler_json(p, [])]
    caps = capitulos(vd)
    if juntos != [b.name for b in caps]:
        return False
    feito = p.stat().st_mtime
    for b in caps:
        for f in (_narracao(b), b / "_work" / "palavras.json", b / "roteiro.txt"):
            if f is None or not f.exists() or f.stat().st_mtime > feito:
                return False
    return True


def juntar(vd):
    """Emenda as narrações e as transcrições dos capítulos em <vídeo>/producao/. Devolve os capítulos (capitulos.json).
    ValueError com o motivo se faltar narração ou transcrição de algum."""
    vd = Path(vd)
    falta = faltam(vd)
    if falta:
        raise ValueError("falta " + ", ".join(f"{o} do capítulo {nn}" for nn, o in falta))
    destino = pasta(vd)
    (destino / "_work").mkdir(parents=True, exist_ok=True)
    # as palavras e os capítulos de ANTES ficam guardados: se a voz foi refeita depois do storyboard, é por eles que o
    # storyboard é realinhado às palavras novas (realinhar)
    for nome in ("_work/palavras.json", "capitulos.json"):
        f = destino / nome
        if f.exists():
            f.replace(f.with_name(f.stem + "_antes.json"))
    caps, palavras, transc, roteiros, entradas, filtros = [], [], [], [], [], []
    t = 0.0
    for k, b in enumerate(capitulos(vd)):
        pal = ler_json(b / "_work" / "palavras.json", []) or []
        if not pal:
            raise ValueError(f"a transcrição do capítulo {b.name} está vazia")
        audio = _narracao(b)
        dur = _duracao(audio)
        a, f = max(0.0, pal[0]["ini"] - CABECA), min(dur, pal[-1]["fim"] + RABO)
        desloc = t - a
        for w in pal:
            palavras.append({"i": len(palavras), "p": w["p"], "ini": round(w["ini"] + desloc, 2),
                             "fim": round(w["fim"] + desloc, 2)})
        roteiro = (b / "roteiro.txt").read_text()
        nome = _nome(roteiro, b.name)
        caps.append({"nn": b.name, "nome": nome, "tipo": _tipo(roteiro), "ini": round(t, 3),
                     "fim": round(t + f - a, 3), "palavras": len(pal)})
        tx = (b / "_work" / "transcricao.txt").read_text() if (b / "_work" / "transcricao.txt").exists() else ""
        tx = re.sub(r"\[(\d+(?:\.\d+)?)\]", lambda m: f"[{float(m.group(1)) + desloc:.2f}]", tx.strip())
        transc.append(f"## Capítulo {b.name}: {nome}\n{tx}")
        roteiros.append(roteiro.strip())
        entradas += ["-i", str(audio)]
        filtros.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,atrim={a:.3f}:{f:.3f},"
                       f"asetpts=PTS-STARTPTS[a{k}]")
        t += f - a
    n = len(caps)
    grafo = ";".join(filtros) + ";" + "".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[s]"
    wav = destino / "narracao.wav"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + entradas + ["-filter_complex", grafo, "-map", "[s]",
                       "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True)
    if r.returncode:
        raise ValueError(f"não consegui emendar as narrações: {r.stderr.strip()[-300:]}")
    gravar_json(destino / "_work" / "palavras.json", palavras)
    (destino / "_work" / "transcricao.txt").write_text("\n\n".join(transc) + "\n")
    (destino / "roteiro.txt").write_text("\n\n".join(roteiros) + "\n")
    gravar_json(destino / "capitulos.json", caps)
    return caps


def _norm(p):
    return re.sub(r"[^a-z0-9]", "", p.lower())


def _por_capitulo(palavras, caps):
    """As palavras de cada capítulo: {nn: [palavra]}. Pela contagem que o juntar gravou; num capitulos.json de antes
    dela, pelo tempo (a última palavra de um capítulo às vezes cai no tempo do seguinte)."""
    out, k = {}, 0
    if all("palavras" in c for c in caps):
        for c in caps:
            out[c["nn"]] = [w["p"] for w in palavras[k:k + c["palavras"]]]
            k += c["palavras"]
    else:
        for c in caps:
            out[c["nn"]] = [w["p"] for w in palavras if c["ini"] - 0.01 <= w["ini"] < c["fim"] - 0.01]
    return out


def _contem(seq, parte):
    n = len(parte)
    return any(seq[i:i + n] == parte for i in range(len(seq) - n + 1))


def realinhar(vd):
    """A voz foi refeita depois do storyboard (outro provedor, outra velocidade): a transcrição nova escreve algumas
    palavras de outro jeito ("Orang" → "Oaring", "Hogg's Road" → "Hoggsrod"; 19 em 1.626 no teste de 2026-11-11) e o
    compilador não acha mais os gatilhos e as falas. Alinha, capítulo a capítulo, as palavras de antes com as novas e
    troca no cenas.json SÓ os gatilhos e as falas (o texto que aparece na tela fica como está). Uma troca só vale se
    a forma antiga sumiu do capítulo: "pro team" → "protein" troca a expressão, mas não mexe nos outros "team" que a
    voz nova continua dizendo. Devolve quantas trocas fez; 0 se não há o que alinhar."""
    import difflib
    d = pasta(vd)
    antes, caps_a = ler_json(d / "_work" / "palavras_antes.json", []), ler_json(d / "capitulos_antes.json", [])
    novas, caps_n = ler_json(d / "_work" / "palavras.json", []), ler_json(d / "capitulos.json", [])
    cenas = ler_json(d / "cenas.json")
    if not (antes and novas and cenas and caps_a and caps_n):
        return 0
    de_antes, de_agora = _por_capitulo(antes, caps_a), _por_capitulo(novas, caps_n)
    limpa = lambda t: t.strip(" .,;:!?\"“”")
    feitas = [0]

    def trocar(txt, pares):
        for a, b in pares:
            novo = re.sub(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])", b, txt)
            if novo != txt:
                feitas[0] += 1
                txt = novo
        return txt

    def andar(o, pares):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if k in ("gatilho", "fala", "nome_fala", "clique") and isinstance(v, str):
                    o[k] = trocar(v, pares)
                elif k in ("acima", "legenda") and isinstance(v, list) and len(v) > 1 and isinstance(v[1], str):
                    v[1] = trocar(v[1], pares)
                elif k in ("textos", "sobre") and isinstance(v, list):
                    for x in v:
                        if isinstance(x, list) and len(x) > 1 and isinstance(x[1], str):
                            x[1] = trocar(x[1], pares)
                else:
                    andar(v, pares)
        elif isinstance(o, list):
            for v in o:
                andar(v, pares)

    for it, cn in zip(cenas.get("itens", []), caps_n):
        a, n = de_antes.get(cn["nn"]), de_agora.get(cn["nn"])
        if not a or not n:
            continue
        na, nn = [_norm(x) for x in a], [_norm(x) for x in n]
        pares = set()
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, na, nn, autojunk=False).get_opcodes():
            if tag != "replace":
                continue
            velho, novo = [limpa(x) for x in a[i1:i2]], [limpa(x) for x in n[j1:j2]]
            pares.add((" ".join(velho), " ".join(novo)))
            if len(velho) == len(novo):
                pares |= set(zip(velho, novo))
            elif len(novo) == 1:            # duas palavras viraram uma: o gatilho numa delas vai para a nova
                pares |= {(x, novo[0]) for x in velho}
        # só a forma que a voz nova não diz mais em lugar nenhum do capítulo
        pares = [p for p in pares if p[0] and p[1] and not _contem(nn, [_norm(x) for x in p[0].split()])]
        if pares:
            andar(it, sorted(pares, key=lambda p: -len(p[0])))
    if feitas[0]:
        gravar_json(d / "cenas.json", cenas)
    return feitas[0]
