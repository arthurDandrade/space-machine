"""Busca e baixa candidatos para cada asset do plano.

Uso:
  python scripts/buscar.py <projeto>                 # todos os assets ainda sem candidatos
  python scripts/buscar.py <projeto> --asset 02-05-a --asset 02-06-b
  python scripts/buscar.py <projeto> --item 03       # só um item
  python scripts/buscar.py <projeto> --refazer --asset 02-05-a --consulta "outra busca"

Saída por asset em <projeto>/_work/candidatos/<asset_id>/:
  01.jpg, 02.png ...      candidatos de imagem (numerados)
  folha.jpg               grade numerada para escolher
  v1_folha.jpg ...        (vídeo) frames de preview com o tempo de cada um
                          vídeos: só bancos livres (Pexels, Pixabay, Commons, Archive) — YouTube removido em 2026-10-11
  candidatos.json         metadados (url, fonte, licença, autor, tamanho)
"""
import argparse
import re
import shutil
import subprocess
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from comum import (baixar_imagem, limpar_cache, config, distancia_hash, dominio_bloqueado, folha_contato,
                   gravar_json, iter_assets, ler_json, log, phash)
from fontes import BUSCADORES, UA_WIKIMEDIA, VIDEO_LIVRES
from comum import caminhos
import requests

# No Commons a busca de texto traz fotos de jogos para "Eagles logo"; exigir a palavra no título resolve.
PALAVRA_TITULO_COMMONS = {"logo": "logo", "mapa": "map", "bandeira": "flag"}
# Jogadores menos famosos só têm fotos de ~600 px na web: aceitamos até 60% do mínimo,
# mas esses candidatos vão para o fim da folha e marcados como BAIXA.
RELAXADO = 0.6


def consultas_para(asset, fonte):
    por_fonte = asset.get("buscas_por_fonte", {})
    if fonte in por_fonte:
        return por_fonte[fonte]
    base = fonte.replace("_transparente", "")
    if base in por_fonte:
        return por_fonte[base]
    if base == "google" and "web" in por_fonte:   # cards antigos: google usa as buscas do "web"
        return por_fonte["web"]
    return asset.get("buscas") or [asset.get("descricao", "")]


def camadas_de_fontes(asset, cfg, tipo):
    """Rank de fontes (2026-10-10): lista de camadas, da melhor para a pior. Lista simples de
    nomes (ex.: "fontes" do card) = uma camada só."""
    fontes = asset.get("fontes") or cfg["fontes_por_tipo"].get(tipo, cfg["fontes_por_tipo"]["foto"])
    if all(isinstance(f, str) for f in fontes):
        return [fontes]
    return [[f] if isinstance(f, str) else f for f in fontes]


def buscar_imagens(asset, pasta, cfg):
    tipo = asset["tipo"]
    alvo = asset.get("quantidade", cfg["candidatos_por_asset"])
    lado_min = cfg["lado_menor_minimo"].get(tipo, cfg["lado_menor_minimo"]["foto"])
    orient = asset.get("orientacao")
    orient = None if orient in (None, "qualquer") else orient

    # Busca a 1ª camada do rank; só desce para a próxima se faltar candidato de tamanho bom.
    vistos, brutos = set(), []
    for nc, camada in enumerate(camadas_de_fontes(asset, cfg, tipo), 1):
        if nc > 1:
            bons = sum(1 for c in brutos if not c.get("w") or min(c["w"], c["h"]) >= lado_min)
            # fonte paga (Serper/Google): só se faltar mesmo (menos que o nº de candidatos da folha)
            paga = any(f in cfg.get("fontes_pagas", []) for f in camada)
            if bons >= (alvo if paga else alvo * 2):
                break
            log(f"   rank: só {bons} bons, descendo para a camada {nc} {camada}")
        brutos += _buscar_camada(asset, camada, alvo, orient, lado_min, tipo, vistos, cfg)

    tmp = pasta / "_baixando"
    tmp.mkdir(parents=True, exist_ok=True)

    def baixa(par):
        i, c = par
        r = baixar_imagem(c["url"], tmp / f"{i:03d}", int(lado_min * RELAXADO))
        return (c, r)

    # Prioriza quem já declarou tamanho bom; os pequenos só entram se faltar candidato.
    grandes = [c for c in brutos if not c.get("w") or min(c["w"], c["h"]) >= lado_min]
    pequenos = [c for c in brutos if c not in grandes]
    with ThreadPoolExecutor(8) as ex:
        resultados = list(ex.map(baixa, enumerate((grandes + pequenos)[: alvo * 4])))
    # Ordena: primeiro os que passam no mínimo normal, depois os de baixa resolução.
    resultados.sort(key=lambda cr: 0 if cr[1] and min(cr[1][1], cr[1][2]) >= lado_min else 1)
    return _escolher_e_folha(asset, pasta, resultados, tmp, alvo, lado_min)


def ajustar_consulta(q):
    """Trocas de termo do tema do canal (canal.json › regras.busca.trocar_termos). Ex. do Pro Football: "football"
    sozinho trazia futebol (Copa de 2022 com selo FIFA, 2026-10-12) e vira "american football", a não ser que a
    consulta já diga american/NFL/college/soccer. Cada troca: {"padrao", "por", "exceto"} (regex, sem maiúsculas)."""
    for tr in caminhos.regras().get("busca", {}).get("trocar_termos", []):
        ql = q.lower()
        if not re.search(tr["padrao"], ql) or (tr.get("exceto") and re.search(tr["exceto"], ql)):
            continue
        q = re.sub(tr["padrao"], tr["por"], q, count=1, flags=re.IGNORECASE)
    return q


def _buscar_camada(asset, fontes, alvo, orient, lado_min, tipo, vistos, cfg):
    """Busca as fontes de uma camada e intercala (1º da fonte A, 1º da B, 2º da A...)
    para nenhuma fonte ocupar todas as vagas."""
    por_fonte = []
    for fonte in fontes:
        fn = BUSCADORES.get(fonte)
        if not fn:
            continue
        lista = []
        for q in consultas_para(asset, fonte):
            if not q:
                continue
            q = ajustar_consulta(q)
            if fonte == "commons" and tipo in ("logo", "mapa", "bandeira") and "intitle:" not in q:
                q = f"{q} intitle:{PALAVRA_TITULO_COMMONS[tipo]}"
            res = fn(q, alvo * 2, orient)
            novos = 0
            for c in res:
                u = c.get("url")
                # título/autor também: sites como inspiredpencil hospedam arquivo da Vecteezy (com marca d'água) — 2026-10-12
                if (not u or u in vistos or dominio_bloqueado(u, cfg) or dominio_bloqueado(c.get("pagina"), cfg)
                        or dominio_bloqueado(c.get("titulo"), cfg) or dominio_bloqueado(c.get("autor"), cfg)):
                    continue
                if c.get("w") and c.get("h") and min(c["w"], c["h"]) < lado_min * RELAXADO:
                    continue
                vistos.add(u)
                c["consulta"] = q
                lista.append(c)
                novos += 1
            log(f"   {fonte:17s} '{q}': {novos} resultados")
            if len(lista) >= alvo * 2:   # a fonte já deu o bastante: não roda as buscas mais gerais
                break
        por_fonte.append(lista)
    brutos = []
    for k in range(max((len(l) for l in por_fonte), default=0)):
        brutos += [l[k] for l in por_fonte if k < len(l)]
    return brutos


def _escolher_e_folha(asset, pasta, resultados, tmp, alvo, lado_min):
    escolhidos, hashes = [], []
    for c, r in resultados:
        if not r:
            continue
        caminho, w, h = r
        try:
            hsh = phash(caminho)
        except Exception:
            continue
        if any(distancia_hash(hsh, x) <= 6 for x in hashes):
            continue
        hashes.append(hsh)
        n = len(escolhidos) + 1
        final = pasta / f"{n:02d}{caminho.suffix}"
        shutil.move(str(caminho), final)
        c.update({"n": n, "arquivo": final.name, "w": w, "h": h, "baixa_res": min(w, h) < lado_min})
        escolhidos.append(c)
        if len(escolhidos) >= alvo:
            break
    shutil.rmtree(tmp, ignore_errors=True)

    folha_contato([(pasta / c["arquivo"],
                    f"#{c['n']} {c['w']}x{c['h']} {'BAIXA ' if c['baixa_res'] else ''}{c['fonte'][:12]}")
                   for c in escolhidos], pasta / "folha.jpg",
                  titulo=f"{asset['id']} [{asset['tipo']}] {asset.get('descricao','')}")
    return escolhidos


DURACAO_MAX_S = 30 * 60
PREVIEW_MAX_S = 90        # tempo máximo para montar a folha de UM vídeo


def preview_direto(v, pasta, k, cfg):
    """Folha de um vídeo de banco livre (Pexels, Pixabay, Commons, Archive): quadros tirados direto do
    arquivo leve (url_preview) com o ffmpeg, pulando para cada tempo (sem baixar o vídeo inteiro)."""
    dur = float(v.get("duracao") or 0)
    if dur <= 0:
        return False
    if dur > DURACAO_MAX_S:
        # jogo/programa inteiro (Super Bowl X no Archive, horas): cada quadro estourava 120 s e não serve
        # para um card de poucos segundos
        log(f"   vídeo {v['id']}: {dur / 60:.0f} min, longo demais para card: pulado")
        return False
    n = min(36, max(6, int(dur)))
    passo = dur / n
    with tempfile.TemporaryDirectory() as tmp:
        origem = v["url_preview"]
        if v["fonte"] == "commons":
            # o servidor de mídia da Wikimedia devolve 429 com várias conexões: baixa a versão leve uma vez
            arq = Path(tmp) / "prev.webm"
            try:
                with requests.get(origem, headers={"User-Agent": UA_WIKIMEDIA}, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(arq, "wb") as fh:
                        for bloco in r.iter_content(1 << 20):
                            fh.write(bloco)
            except Exception as e:
                log(f"   vídeo {v['id']}: falhou o download do preview ({e})")
                return False
            origem = str(arq)

        limite = time.time() + PREVIEW_MAX_S

        def quadro(i):
            # prazo por vídeo: o Archive leva 1–2 min por quadro em arquivo longo (bloco 06 ficou 15 min num só
            # vídeo, 2026-10-12). Estourou o prazo, o vídeo fica com os quadros que deu (ou é pulado).
            resta = limite - time.time()
            if resta < 3:
                return None
            t = i * passo
            arq = Path(tmp) / f"{i:03d}.jpg"
            try:
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-user_agent", UA_WIKIMEDIA,
                                "-ss", f"{t:.2f}", "-i", origem, "-frames:v", "1", "-vf", "scale=400:-2", str(arq)],
                               capture_output=True, timeout=min(60, resta))
            except (subprocess.TimeoutExpired, OSError):
                # arquivo enorme/lento (ex.: jogo inteiro do Super Bowl X no Archive): perde só este quadro.
                # Antes o erro subia e derrubava a busca do bloco inteiro (9 blocos, 2026-10-12)
                return None
            return (arq, f"v{k}  t={t:.0f}s") if arq.exists() else None
        with ThreadPoolExecutor(3) as ex:
            itens = [x for x in ex.map(quadro, range(n)) if x]
        if len(itens) < 3:
            log(f"   vídeo {v['id']}: falhou o preview direto")
            return False
        folha_contato(itens, pasta / f"v{k}_folha.jpg", colunas=6, celula=(400, 240),
                      titulo=f"v{k}: {v['titulo'][:80]} ({dur:.0f}s) — {v['fonte']} / {v['canal'][:25]} [{v['w']}x{v['h']}]")
    v.update({"n": k, "folha": f"v{k}_folha.jpg", "passo_preview_s": round(passo, 1), "preview": "direto"})
    return True


def camadas_video(asset, cfg):
    """Camadas de fontes de vídeo, só bancos livres (Pexels, Pixabay, Commons, Archive).
    O YouTube foi REMOVIDO do sistema em 2026-10-11 (as buscas automáticas fizeram o Google bloquear o IP do
    Arthur e acusá-lo de fraude/proxy). "youtube" num card ou no config é ignorado."""
    fontes = asset.get("fontes") or cfg["fontes_por_tipo"]["video"]
    if all(isinstance(f, str) for f in fontes):
        camadas = [[f for f in fontes if f in VIDEO_LIVRES]]
    else:
        camadas = [[f for f in ([c] if isinstance(c, str) else c) if f in VIDEO_LIVRES] for c in fontes]
    camadas = [c for c in camadas if c]
    return camadas or [[f for f in cfg["fontes_por_tipo"]["video"][0] if f in VIDEO_LIVRES]]


def fontes_video(asset, cfg):
    return [f for camada in camadas_video(asset, cfg) for f in camada]


def _videos_livres(asset, fontes, maximo, pasta, proximo, vistos, cfg, orient):
    listas = []
    for f in fontes:
        if f not in VIDEO_LIVRES:
            continue
        if sum(len(x) for x in listas) >= maximo + 2:   # já tem o bastante (+2 de folga p/ preview que falha)
            break
        achados = []
        for q in consultas_para(asset, f):
            for v in VIDEO_LIVRES[f](q, cfg["videos_livres_max"], cfg["video_duracao_max_livre_s"], orient):
                if v["id"] not in vistos and v["id"] not in {x["id"] for x in achados}:
                    v["consulta"] = q
                    achados.append(v)
            log(f"   {f:<17} '{q}': {len(achados)} vídeos acumulados")
            if len(achados) >= maximo:
                break
        listas.append(achados)
    livres, ok = [], []
    for i in range(max([len(x) for x in listas] + [0])):      # intercala as fontes
        livres += [x[i] for x in listas if i < len(x)]
    for v in livres:
        if len(ok) >= maximo:
            break
        try:
            ok_prev = preview_direto(v, pasta, proximo, cfg)
        except Exception as e:      # um vídeo problemático não derruba a busca do bloco
            log(f"   vídeo {v.get('id')}: preview falhou ({type(e).__name__}): pulado")
            ok_prev = False
        if ok_prev:
            vistos.add(v["id"])
            ok.append(v)
            proximo += 1
    return ok


def buscar_videos(asset, pasta, cfg, ja=()):
    """Percorre as camadas de bancos livres (camadas_video); passa para a próxima só se ainda faltar vídeo
    (menos que videos_por_asset). Devolve (candidatos, False) — o 2º valor existia para o YouTube pendente."""
    alvo = asset.get("quantidade", cfg["videos_por_asset"])
    orient = asset.get("orientacao")
    orient = None if orient in (None, "qualquer") else orient
    vistos = {c.get("id") for c in ja}
    proximo = max([c.get("n", 0) for c in ja] + [0]) + 1
    ok = []
    for nc, camada in enumerate(camadas_video(asset, cfg), 1):
        if nc > 1 and len(ok) >= alvo:
            break
        if nc > 1:
            log(f"   rank: {len(ok)} vídeos, camada {nc} {camada}")
        maximo = cfg["videos_livres_max"] if nc == 1 else max(1, alvo - len(ok))
        novos = _videos_livres(asset, camada, min(maximo, cfg["videos_livres_max"]), pasta, proximo, vistos, cfg,
                               orient)
        ok += novos
        proximo += len(novos)
    return ok, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--asset", action="append", default=[])
    ap.add_argument("--item", action="append", default=[])
    ap.add_argument("--refazer", action="store_true", help="apaga candidatos anteriores do(s) asset(s)")
    ap.add_argument("--consulta", action="append", default=[], help="substitui as buscas do plano (use com --asset)")
    ap.add_argument("--tipo", help="busca este asset como outro tipo (ex.: foto no lugar de um vídeo que não existe "
                    "em banco livre); use com --asset")
    ap.add_argument("--fontes", help="substitui as fontes do card nesta busca, ex.: pexels,pixabay ou archive,commons"
                    " (use com --asset; ex.: busca específica num card que pedia bancos livres primeiro)")
    a = ap.parse_args()

    cfg = config()
    limpar_cache()
    proj = Path(a.projeto)
    plano = ler_json(proj / "plano.json")
    if not plano:
        raise SystemExit("plano.json não encontrado no projeto.")
    escolhas = ler_json(proj / "escolhas.json", {})
    base = proj / "_work" / "candidatos"

    feitos, sem = 0, []
    for item, cena, asset in iter_assets(plano):
        aid = asset["id"]
        if a.asset and aid not in a.asset:
            continue
        if a.item and item["id"] not in a.item:
            continue
        pasta = base / aid
        anterior = ler_json(pasta / "candidatos.json")
        if anterior and not a.refazer:
            continue
        if aid in escolhas and not a.asset:
            continue
        antes = pasta.with_name(aid + "_antes_refazer")
        if a.refazer and pasta.exists():
            # guarda os candidatos antigos: se a busca nova vier vazia, voltam
            shutil.rmtree(antes, ignore_errors=True)
            pasta.rename(antes)
        pasta.mkdir(parents=True, exist_ok=True)
        if a.consulta:
            asset = dict(asset, buscas=a.consulta, buscas_por_fonte={})
        if a.tipo:
            asset = dict(asset, tipo=a.tipo, fontes=None, buscas_por_fonte={})
        if a.fontes:
            asset = dict(asset, fontes=[f.strip() for f in a.fontes.split(",") if f.strip()], buscas_por_fonte={})
        log(f"[{aid}] {asset['tipo']}: {asset.get('descricao','')}")
        pendente = False
        if asset["tipo"] == "video":
            cands, pendente = buscar_videos(asset, pasta, cfg)
        else:
            cands = buscar_imagens(asset, pasta, cfg)
        if not cands and antes.exists():
            shutil.rmtree(pasta, ignore_errors=True)
            antes.rename(pasta)
            log("   -> busca nova vazia: mantive os candidatos antigos")
            continue
        shutil.rmtree(antes, ignore_errors=True)
        gravar_json(pasta / "candidatos.json", {"asset": asset, "candidatos": cands})
        feitos += 1
        if not cands:
            sem.append(aid)
        log(f"   -> {len(cands)} candidatos")

    log(f"\nConcluído: {feitos} assets buscados.")
    if sem:
        log("SEM CANDIDATOS (reformular busca ou gerar com IA): " + ", ".join(sem))


if __name__ == "__main__":
    main()
