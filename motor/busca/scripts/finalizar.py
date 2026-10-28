"""Aplica as escolhas: copia/processa os assets finais e gera manifesto + página de revisão.

Uso: python scripts/finalizar.py <projeto> [--asset ID ...]

escolhas.json (gravado pelo Claude na curadoria):
  {"02-05-a": {"n": 3},                       imagem nº 3 da folha
   "02-06-b": {"n": 1, "inicio": 42.0},       vídeo v1 a partir de 42 s (dura asset.duracao)
   "02-07-a": {"arquivo": "/caminho/gerado.png", "fonte": "IA (Higgsfield)"},
   "02-08-a": {"pular": true}}

Saída:
  <projeto>/assets/<item>/<cena>/<NN>_<gatilho>.<ext>
  <projeto>/manifesto.json   (o que o agente de edição vai ler)
  <projeto>/creditos.txt
  <projeto>/revisao.html     (galeria: escolhido + alternativas)
"""
import argparse
import html
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from comum import config, gravar_json, iter_assets, ler_json, log, slug

_sessao_rembg = [None]


def recortar(origem, destino):
    im = Image.open(origem)
    tem_alpha = im.mode in ("RGBA", "LA", "P") and im.convert("RGBA").getchannel("A").getextrema()[0] < 250
    if not tem_alpha:
        from rembg import new_session, remove
        if _sessao_rembg[0] is None:
            _sessao_rembg[0] = new_session("isnet-general-use")
        im = remove(im.convert("RGB"), session=_sessao_rembg[0])
    im = im.convert("RGBA")
    a = im.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    box = a.getbbox()
    if box:
        pad = 12
        box = (max(0, box[0] - pad), max(0, box[1] - pad), min(im.width, box[2] + pad), min(im.height, box[3] + pad))
        im = im.crop(box)
    im.save(destino)


def baixar_trecho_direto(url, inicio, dur, destino):
    """Vídeo de banco livre (Pexels, Pixabay, Commons, Archive): o ffmpeg lê só o trecho do arquivo
    remoto e já entrega H.264 até 1080p, sem áudio."""
    ua = "SpaceMachineBuscadorAssets/1.0 (ferramenta pessoal de pesquisa de imagens)"   # a Wikimedia exige
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-user_agent", ua,
                    "-ss", f"{inicio:.2f}", "-i", url,
                    "-t", f"{dur:.2f}", "-an", "-vf", "scale=-2:'min(1080,ih)':flags=lanczos,setsar=1",
                    "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(destino)], check=True, timeout=3600)


def baixar_trecho(url, inicio, dur, destino):
    raise RuntimeError("YouTube removido do sistema em 2026-10-11 (bloqueio de IP / acusação de fraude): este caminho não baixa mais nada do YouTube. Escolha um vídeo de banco livre ou uma imagem.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--asset", action="append", default=[])
    a = ap.parse_args()
    cfg = config()
    proj = Path(a.projeto).resolve()
    plano = ler_json(proj / "plano.json")
    escolhas = ler_json(proj / "escolhas.json", {})
    manif_ant = {m["id"]: m for m in ler_json(proj / "manifesto.json", {"assets": []})["assets"]}
    cand_dir = proj / "_work" / "candidatos"

    manifesto, faltando = [], []
    ordem_cena = {}
    for item, cena, asset in iter_assets(plano):
        aid = asset["id"]
        pasta_item = f"{item['id']}_{slug(item.get('nome', ''), 30)}"
        if cena is None:
            pasta, prefixo = proj / "assets" / pasta_item, "00_titulo"
        else:
            pasta = proj / "assets" / pasta_item / cena["id"]
            ordem_cena[cena["id"]] = ordem_cena.get(cena["id"], 0) + 1
            prefixo = f"{ordem_cena[cena['id']]:02d}_{slug(asset.get('gatilho', 'asset'), 24)}"
        esc = escolhas.get(aid)
        base = {"id": aid, "item": item["id"], "item_nome": item.get("nome"),
                "cena": cena["id"] if cena else None, "tipo": asset["tipo"],
                "gatilho": asset.get("gatilho"), "tempo": asset.get("tempo"),
                "papel": asset.get("papel"), "descricao": asset.get("descricao")}
        if not esc:
            faltando.append(aid)
            continue
        if esc.get("pular"):
            continue
        if a.asset and aid not in a.asset and aid in manif_ant:
            manifesto.append(manif_ant[aid])
            continue
        pasta.mkdir(parents=True, exist_ok=True)
        meta = ler_json(cand_dir / aid / "candidatos.json", {"candidatos": []})
        cand = next((c for c in meta["candidatos"] if c.get("n") == esc.get("n")), None)
        try:
            if esc.get("arquivo"):
                origem = Path(esc["arquivo"]).expanduser()
                info = {"fonte": esc.get("fonte", "arquivo local"), "url": str(origem), "licenca": esc.get("licenca", "")}
            elif cand is None:
                raise ValueError(f"candidato n={esc.get('n')} não existe")
            else:
                info = {k: cand.get(k) for k in ("fonte", "url", "pagina", "licenca", "autor", "titulo")}
            if asset["tipo"] == "video" and not esc.get("arquivo"):
                dur = float(esc.get("duracao", asset.get("duracao", 4.0))) + cfg["video_margem_s"]
                destino = pasta / f"{prefixo}.mp4"
                log(f"[{aid}] baixando trecho {esc.get('inicio', 0)}s +{dur:.1f}s de {cand['url']}")
                if cand.get("fonte", "youtube") == "youtube" or "youtube.com" in str(cand.get("url")):
                    baixar_trecho(cand["url"], float(esc.get("inicio", 0)), dur, destino)
                else:
                    baixar_trecho_direto(cand["url"], float(esc.get("inicio", 0)), dur, destino)
                info["trecho"] = [esc.get("inicio", 0), esc.get("inicio", 0) + dur]
            else:
                origem = origem if esc.get("arquivo") else cand_dir / aid / cand["arquivo"]
                if asset["tipo"] in ("recorte", "bandeira") or esc.get("recortar"):
                    destino = pasta / f"{prefixo}.png"
                    log(f"[{aid}] recortando fundo")
                    recortar(origem, destino)
                else:
                    destino = pasta / f"{prefixo}{origem.suffix.lower()}"
                    shutil.copy2(origem, destino)
            if destino.suffix != ".mp4":
                w, h = Image.open(destino).size
            else:
                r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", str(destino)],
                                   capture_output=True, text=True).stdout.strip().split(",")
                w, h = int(r[0]), int(r[1])
            base.update({"arquivo": destino.relative_to(proj).as_posix(), "w": w, "h": h, "origem": info})
            manifesto.append(base)
        except Exception as e:
            log(f"[{aid}] ERRO: {e}")
            faltando.append(aid)

    gravar_json(proj / "manifesto.json", {"projeto": plano.get("titulo"), "assets": manifesto})
    creditos = sorted({f"{m['origem'].get('titulo') or ''} — {m['origem'].get('autor') or ''} — "
                       f"{m['origem'].get('licenca') or ''} — {m['origem'].get('pagina') or m['origem'].get('url')}"
                       for m in manifesto})
    (proj / "creditos.txt").write_text("\n".join(creditos) + "\n")
    gerar_revisao(proj, plano, manifesto, cand_dir, escolhas)
    log(f"\n{len(manifesto)} assets prontos em {proj/'assets'}")
    if faltando:
        log(f"Sem escolha ou com erro ({len(faltando)}): " + ", ".join(faltando))


def gerar_revisao(proj, plano, manifesto, cand_dir, escolhas):
    por_id = {m["id"]: m for m in manifesto}
    rel = lambda p: os.path.relpath(p, proj)
    h = ["<!doctype html><meta charset=utf-8><title>Revisão de assets</title><style>",
         "body{font-family:-apple-system,Helvetica,sans-serif;background:#f3f3f3;margin:24px;color:#111}",
         "h2{margin-top:40px}.cena{background:#fff;border-radius:10px;padding:14px 18px;margin:12px 0}",
         ".fala{color:#555;font-size:14px}.asset{display:flex;gap:10px;align-items:flex-start;margin:10px 0;flex-wrap:wrap}",
         ".ok img,.ok video{max-height:220px;border:3px solid #1a7f37;border-radius:6px}",
         ".alt img{max-height:90px;opacity:.75;border-radius:4px}.tag{font-size:12px;color:#444;width:220px}",
         ".falta{color:#b00020;font-weight:bold}</style>",
         f"<h1>{html.escape(plano.get('titulo',''))}</h1>",
         "<p>Verde = escolhido. Miniaturas = alternativas (nº entre parênteses). Para trocar, diga ao Claude: "
         "<i>“no asset X usa a nº N”</i>.</p>"]
    for item in plano.get("itens", []):
        h.append(f"<h2>{html.escape(item['id'])} — {html.escape(item.get('nome',''))}</h2>")
        blocos = ([{"id": "título", "fala": item.get("nome", ""), "assets": [item["titulo_asset"]]}]
                  if item.get("titulo_asset") else []) + item.get("cenas", [])
        for cena in blocos:
            if not cena.get("assets"):
                continue
            h.append(f"<div class=cena><b>{html.escape(cena['id'])}</b> "
                     f"<span class=fala>{html.escape(cena.get('fala',''))}</span>")
            for asset in cena["assets"]:
                m = por_id.get(asset["id"])
                h.append("<div class=asset>")
                h.append(f"<div class=tag><b>{asset['id']}</b> [{asset['tipo']}]<br>gatilho: "
                         f"{html.escape(str(asset.get('gatilho')))} @ {asset.get('tempo')}s<br>"
                         f"{html.escape(asset.get('descricao',''))}</div>")
                if m:
                    src = html.escape(m["arquivo"])
                    tag = (f"<video src='{src}' muted loop autoplay></video>" if src.endswith(".mp4")
                           else f"<img src='{src}'>")
                    h.append(f"<div class=ok>{tag}<div class=tag>{html.escape(str(m['origem'].get('fonte')))} "
                             f"{m['w']}x{m['h']}</div></div>")
                else:
                    h.append("<div class=falta>SEM ASSET</div>")
                esc = escolhas.get(asset["id"], {})
                aviso = esc.get("conferir") or esc.get("motivo")
                if aviso:
                    h.append(f"<div class='tag falta'>⚠ {html.escape(aviso)}</div>")
                meta = ler_json(cand_dir / asset["id"] / "candidatos.json", {"candidatos": []})
                for c in meta["candidatos"]:
                    arq = c.get("arquivo") or c.get("folha")
                    if arq:
                        h.append(f"<div class=alt><img src='{html.escape(rel(cand_dir/asset['id']/arq))}'>"
                                 f"<div class=tag>({c['n']})</div></div>")
                h.append("</div>")
            h.append("</div>")
    (proj / "revisao.html").write_text("\n".join(h))


if __name__ == "__main__":
    main()
