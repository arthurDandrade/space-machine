"""O vídeo inteiro sem After (fluxo "video" do explained, 2026-11-05): um MP4 só, a partir do projeto do vídeo
(<vídeo>/producao, ver space_machine/video.py).

Uso: python render_video.py <producao> [--meia] [--saida <arquivo.mp4>] [--trilha <áudio>] [--processos N]

Cada capítulo tem o plano dele (edicao/plano_render_NN.json, do gerar_ae2.py), com os tempos contados do começo do
capítulo. Por dentro o vídeo é renderizado em pedaços, um por capítulo, em paralelo e sem áudio
(edicao/pedacos/NN.mp4); um pedaço só é renderizado de novo se o plano dele, a duração ou algum arquivo que ele usa
mudou (a impressão digital fica em pedacos/NN.json). Cada pedaço vai do começo do capítulo até o começo do seguinte,
em quadros inteiros contados no vídeo todo, então emendados eles batem com a narração emendada. Com --saida, o
FFmpeg emenda os pedaços sem recomprimir e põe a narração (e a trilha, se vier) por cima.
Escreve edicao/pedacos.json: [{"nn", "ini", "dur", "arquivo"}] (s no vídeo final).
"""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
AMBIENTE_BASE_DB = -15.9        # RMS do ruído marrom do ffmpeg (amplitude 1) depois do filtro; medido, ver emendar


def _ler(p, padrao=None):
    try:
        return json.loads(Path(p).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def capitulos(proj):
    """[(nn, início no áudio emendado)] na ordem do plano.json."""
    plano = _ler(proj / "plano.json", {}) or {}
    return [(it["id"], float(it.get("inicio", 0))) for it in plano.get("itens", [])]


def _impressao(dados, meia):
    """O que decide se um pedaço precisa ser renderizado de novo: o plano, a resolução e os arquivos que ele usa."""
    h = hashlib.sha1(json.dumps(dados, sort_keys=True).encode())
    h.update(b"meia" if meia else b"cheia")
    h.update((AQUI / "compor.py").read_bytes())
    for f in sorted({L["file"] for L in dados["layers"] if L.get("file")}):
        try:
            st = os.stat(f)
        except FileNotFoundError:
            h.update(f"{f}|faltando".encode())
            continue
        # pelo conteúdo, não pela data: o compilar_cenas e o gerar_ae2 desenham de novo os mapas, tabelas e citações a
        # cada compilação (iguais byte a byte), e a correção do QA de UM capítulo renderizava de novo os 9 (2026-11-05)
        if st.st_size <= 64 << 20:
            h.update(f"{f}|".encode() + hashlib.sha1(Path(f).read_bytes()).digest())
        else:
            h.update(f"{f}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()


def preparar(proj, meia=False):
    """Os planos de cada pedaço com a duração certa. Devolve [{nn, ini, dur, plano, saida, impressao, feito}]."""
    caps = capitulos(proj)
    if not caps:
        raise SystemExit("o plano.json não tem capítulos: rode o storyboard antes")
    pasta = proj / "edicao" / "pedacos"
    pasta.mkdir(parents=True, exist_ok=True)
    out = []
    planos = {}
    for nn, _ in caps:
        p = proj / "edicao" / f"plano_render_{nn}.json"
        if not p.exists():
            raise SystemExit(f"falta o plano do capítulo {nn} (edicao/{p.name}): rode o gerar_ae2.py antes")
        planos[nn] = json.loads(p.read_text())
    fps = planos[caps[0][0]]["fps"]
    # fronteiras em quadros inteiros, contadas no vídeo todo (somar durações arredondadas escorregaria ~1 quadro
    # por capítulo em relação à narração)
    q0 = round(caps[0][1] * fps)
    for k, (nn, ini) in enumerate(caps):
        dados = dict(planos[nn], audio=None)
        qa = round(ini * fps)
        if k + 1 < len(caps):
            qb = round(caps[k + 1][1] * fps)
        else:
            qb = qa + math.ceil(dados["dur"] * fps)
        n = max(1, qb - qa)
        dados["dur"] = (n - 0.5) / fps          # o compor faz ceil(dur·fps) = n quadros
        imp = _impressao(dados, meia)
        saida = pasta / f"{nn}.mp4"
        feito = saida.exists() and (_ler(pasta / f"{nn}.json", {}) or {}).get("impressao") == imp
        arq_plano = pasta / f"{nn}.plano.json"
        if not feito:
            arq_plano.write_text(json.dumps(dados, ensure_ascii=False))
        out.append({"nn": nn, "ini": round((qa - q0) / fps, 3), "dur": round(n / fps, 3), "plano": arq_plano,
                    "saida": saida, "impressao": imp, "feito": feito})
    return out


def renderizar(proj, meia=False, processos=None, avisar=print):
    """Renderiza os pedaços que faltam, em paralelo. Devolve a lista de preparar(). SystemExit se algum falhar."""
    pedacos = preparar(proj, meia)
    faltam = [p for p in pedacos if not p["feito"]]
    processos = processos or max(1, min(4, (os.cpu_count() or 4) // 2))
    avisar(f"{len(pedacos)} capítulos: {len(pedacos) - len(faltam)} já renderizados, {len(faltam)} a renderizar "
           f"({processos} de cada vez)")
    erros = []

    def um(p):
        tmp = p["saida"].with_suffix(".tmp.mp4")
        cmd = [sys.executable, str(AQUI / "compor.py"), str(proj), "--plano", str(p["plano"]), "--saida", str(tmp)]
        if meia:
            cmd.append("--meia")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not tmp.exists():
            erros.append(f"capítulo {p['nn']}: {(r.stderr or r.stdout).strip()[-300:]}")
            return
        os.replace(tmp, p["saida"])
        (p["saida"].with_suffix(".json")).write_text(json.dumps({"impressao": p["impressao"], "dur": p["dur"]}))
        p["plano"].unlink(missing_ok=True)
        p["feito"] = True
        avisar(f"capítulo {p['nn']} renderizado ({sum(x['feito'] for x in pedacos)}/{len(pedacos)})")

    with ThreadPoolExecutor(processos) as ex:
        list(ex.map(um, faltam))
    if erros:
        raise SystemExit("o compositor falhou: " + " | ".join(erros))
    (proj / "edicao" / "pedacos.json").write_text(json.dumps(
        [{k: (str(v) if k == "saida" else v) for k, v in p.items() if k in ("nn", "ini", "dur", "saida")}
         for p in pedacos], ensure_ascii=False, indent=1))
    return pedacos


def medir_voz(audio, ini, total):
    """(volume integrado em LUFS, pico em dBFS) do trecho da narração que entra no vídeo."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{ini:.3f}", "-t", f"{total:.3f}", "-i", str(audio),
                        "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    fim = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", fim)
    pico = re.search(r"Peak:\s*(-?[\d.]+) dBFS", fim)
    return (float(i.group(1)) if i else None), (float(pico.group(1)) if pico else None)


def ganho_voz(audio, ini, total, alvo):
    """Quantos dB a narração sobe para chegar ao volume-alvo (LUFS). A voz sintética chega baixa (medido em
    2026-11-10: −29 e −26,6 LUFS em dois canais, contra −17,6 e −18,9 das referências; o YouTube abaixa vídeo alto,
    mas não aumenta vídeo baixo). O ganho é o mesmo do começo ao fim (não comprime a fala); o limitador só segura os
    picos, e o ganho para antes de pedir mais de 3 dB dele."""
    lufs, pico = medir_voz(audio, ini, total)
    if lufs is None or lufs < -60:
        return 0.0
    g = alvo - lufs
    if pico is not None:
        g = min(g, -1.5 - pico + 3.0)
    return round(max(-12.0, min(24.0, g)), 2)


def emendar(proj, pedacos, saida, trilha=None, voz_lufs=None, ambiente_dbfs=None):
    """Os pedaços emendados sem recomprimir + a narração emendada (desde o começo do 1º capítulo) + a trilha.
    voz_lufs: o volume em que a narração sai (None = como veio). ambiente_dbfs: sem trilha, um fundo de ruído bem
    baixo por baixo da voz, para a pausa entre as frases não cair no silêncio absoluto (nas referências do cartum
    as pausas ficam em −46 a −52 dBFS; a voz sintética vai a −99, e a fala soa mais picotada do que é)."""
    proj, saida = Path(proj), Path(saida)
    lista = proj / "edicao" / "pedacos.txt"
    lista.write_text("".join(f"file '{p['saida']}'\n" for p in pedacos))
    junto = proj / "edicao" / "_junto.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(junto)], check=True)
    total = sum(p["dur"] for p in pedacos)
    ini = capitulos(proj)[0][1]
    audio = next(p for p in sorted(proj.iterdir()) if p.stem == "narracao")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(junto), "-ss", f"{ini:.3f}", "-t", f"{total:.3f}", "-i", str(audio)]
    voz = "aresample=48000"
    if voz_lufs is not None:
        voz += f",volume={ganho_voz(audio, ini, total, float(voz_lufs))}dB,alimiter=limit=0.84:level=false"
    if trilha:
        cmd += ["-i", str(trilha), "-filter_complex",
                f"[1:a]{voz}[n];[n][2:a]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v",
                "-map", "[a]"]
    elif ambiente_dbfs is not None:
        # ruído marrom filtrado (parece o ar de uma sala): o anoisesrc com amplitude 1 tem −15,9 dBFS de RMS depois
        # do passa-baixa; o volume leva ao nível pedido
        cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anoisesrc=color=brown:amplitude=1:sample_rate=48000:seed=7",
                "-filter_complex",
                f"[1:a]{voz}[n];[2:a]highpass=f=80,lowpass=f=2500,volume={float(ambiente_dbfs) - AMBIENTE_BASE_DB:.1f}dB[r];"
                "[n][r]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]"]
    elif voz != "aresample=48000":
        cmd += ["-filter_complex", f"[1:a]{voz}[a]", "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart",
            str(saida)]
    saida.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    junto.unlink(missing_ok=True)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--meia", action="store_true", help="960×540 (rascunho)")
    ap.add_argument("--saida", help="emenda os pedaços neste MP4, com a narração")
    ap.add_argument("--trilha", help="áudio da trilha já no volume e na duração do vídeo (space_machine/final.trilha)")
    ap.add_argument("--processos", type=int)
    a = ap.parse_args()
    proj = Path(a.projeto).resolve()
    pedacos = renderizar(proj, a.meia, a.processos, avisar=lambda s: print(s, flush=True))
    if a.saida:
        total = emendar(proj, pedacos, a.saida, a.trilha)
        print(f"OK {a.saida} ({total:.1f} s)")


if __name__ == "__main__":
    main()
