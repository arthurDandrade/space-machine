"""Conectores de busca. Cada função devolve uma lista de candidatos:
{"url": ..., "fonte": ..., "titulo": ..., "pagina": ..., "licenca": ..., "autor": ..., "w": int, "h": int}
"""
import json
import os
import random
import sys
import time
from pathlib import Path

from comum import caminhos, log, sessao

_ultimo_ddg = [0.0]
# A Wikimedia pede um User-Agent que identifique a ferramenta (senão pode bloquear).
UA_WIKIMEDIA = "SpaceMachineBuscadorAssets/1.0 (ferramenta pessoal de pesquisa de imagens)"


def _ddg_espera():
    dt = time.time() - _ultimo_ddg[0]
    if dt < 2.5:
        time.sleep(2.5 - dt + random.random())
    _ultimo_ddg[0] = time.time()


def web(consulta, n, orientacao=None, transparente=False):
    from ddgs import DDGS
    layout = {"retrato": "Tall", "paisagem": "Wide", "quadrado": "Square"}.get(orientacao)
    for tentativa in range(3):
        _ddg_espera()
        try:
            res = DDGS().images(consulta, max_results=n, safesearch="moderate",
                                size=None if transparente else "Large",
                                type_image="transparent" if transparente else None,
                                layout=layout)
            break
        except Exception as e:
            log(f"   ddg: {e} (tentativa {tentativa+1})")
            time.sleep(6 * (tentativa + 1))
    else:
        return []
    out = []
    for r in res:
        out.append({"url": r.get("image"), "fonte": "web", "titulo": r.get("title", ""),
                    "pagina": r.get("url", ""), "licenca": "desconhecida", "autor": r.get("source", ""),
                    "w": int(r.get("width") or 0), "h": int(r.get("height") or 0)})
    return out


def web_transparente(consulta, n, orientacao=None):
    return web(consulta, n, orientacao, transparente=True)


def google(consulta, n, orientacao=None, transparente=False):
    """Google Imagens pela API do Serper (2026-10-10). Chave SERPER_API_KEY (ambiente ou
    .env do canal); sem chave, pulado (o "web" do DuckDuckGo continua como reserva).
    Cada chamada gasta 1 crédito do Serper."""
    chave = chave_api("SERPER_API_KEY")
    if not chave:
        log("   google: sem SERPER_API_KEY (pulado)")
        return []
    tbs = ["ic:trans"] if transparente else ["isz:l"]
    if orientacao in ("retrato", "paisagem", "quadrado"):
        tbs.append({"retrato": "iar:t", "paisagem": "iar:w", "quadrado": "iar:s"}[orientacao])
    # NÃO usar "-site:" na consulta: a conta grátis do Serper recusa ("Query pattern not allowed", 2026-10-12).
    # Bancos com marca d'água saem no filtro do buscar.py (url, página, título e autor).
    corpo = {"q": consulta, "num": 20 if n <= 20 else 40, "tbs": ",".join(tbs)}
    try:
        r = sessao.post("https://google.serper.dev/images", json=corpo, timeout=25,
                        headers={"X-API-KEY": chave, "Content-Type": "application/json"})
        if r.status_code != 200:
            log(f"   google: HTTP {r.status_code} {r.text[:120]}")
            return []
        dados = r.json()
    except Exception as e:
        log(f"   google: {e}")
        return []
    out = []
    for h in dados.get("images", []):
        out.append({"url": h.get("imageUrl"), "fonte": "google", "titulo": h.get("title", ""),
                    "pagina": h.get("link", ""), "licenca": "desconhecida",
                    "autor": h.get("source") or h.get("domain", ""),
                    "w": int(h.get("imageWidth") or 0), "h": int(h.get("imageHeight") or 0)})
        if len(out) >= n:
            break
    return out


def google_transparente(consulta, n, orientacao=None):
    return google(consulta, n, orientacao, transparente=True)


def _get_com_espera(nome, url, **kw):
    """GET que espera e tenta de novo quando a fonte pede calma (429/503). Antes, o 429 do Commons
    com vários blocos buscando ao mesmo tempo virava "0 resultados" e a cena parava sem foto (2026-10-15)."""
    for tentativa in range(4):
        r = sessao.get(url, **kw)
        if r.status_code not in (429, 503) or tentativa == 3:
            return r
        try:
            espera = min(int(r.headers.get("Retry-After") or 0), 60)
        except ValueError:
            espera = 0
        espera = espera or 10 * (tentativa + 1) + random.random() * 5
        log(f"   {nome}: HTTP {r.status_code}, esperando {espera:.0f}s (tentativa {tentativa+1})")
        time.sleep(espera)


def commons(consulta, n, orientacao=None):
    params = {
        "action": "query", "format": "json", "generator": "search", "gsrsearch": consulta,
        "gsrnamespace": 6, "gsrlimit": min(n * 2, 50), "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 2400,
    }
    try:
        r = _get_com_espera("commons", "https://commons.wikimedia.org/w/api.php", params=params, timeout=20,
                            headers={"User-Agent": UA_WIKIMEDIA})
        if r.status_code != 200:
            log(f"   commons: HTTP {r.status_code}")
            return []
        dados = r.json()
    except Exception as e:
        log(f"   commons: {e}")
        return []
    paginas = sorted(dados.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in paginas:
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        # djvu = livro escaneado ("The Film Daily" no lugar de foto antiga de jogo, 2026-10-12)
        if not mime.startswith("image/") or "gif" in mime or "tiff" in mime or "djvu" in mime:
            continue
        meta = ii.get("extmetadata", {})
        url = ii.get("thumburl") if ("svg" in mime or ii.get("width", 0) > 2400) else ii.get("url")
        out.append({"url": url, "fonte": "commons", "titulo": p.get("title", ""),
                    "pagina": ii.get("descriptionurl", ""),
                    "licenca": meta.get("LicenseShortName", {}).get("value", ""),
                    "autor": _limpa_html(meta.get("Artist", {}).get("value", "")),
                    "w": ii.get("thumbwidth") or ii.get("width", 0),
                    "h": ii.get("thumbheight") or ii.get("height", 0)})
        if len(out) >= n:
            break
    return out


def openverse(consulta, n, orientacao=None):
    params = {"q": consulta, "page_size": min(n, 20), "mature": "false"}
    if orientacao in ("retrato", "paisagem", "quadrado"):
        params["aspect_ratio"] = {"retrato": "tall", "paisagem": "wide", "quadrado": "square"}[orientacao]
    try:
        dados = sessao.get("https://api.openverse.org/v1/images/", params=params, timeout=20).json()
    except Exception as e:
        log(f"   openverse: {e}")
        return []
    out = []
    for r in dados.get("results", []):
        out.append({"url": r.get("url"), "fonte": "openverse/" + (r.get("source") or ""),
                    "titulo": r.get("title", ""), "pagina": r.get("foreign_landing_url", ""),
                    "licenca": f"CC {r.get('license','').upper()} {r.get('license_version','')}".strip(),
                    "autor": r.get("creator", ""), "w": r.get("width") or 0, "h": r.get("height") or 0})
    return out


def smithsonian(consulta, n, orientacao=None):
    # Sem chave, pulado (2026-10-10): a DEMO_KEY só dá 10 buscas/hora e estourava calada.
    # Chave grátis: api.data.gov/signup → SI_API_KEY no .env do canal, e volta sozinho.
    chave = chave_api("SI_API_KEY")
    if not chave:
        log("   smithsonian: sem SI_API_KEY (pulado)")
        return []
    params = {"q": f'{consulta} AND online_media_type:"Images"', "rows": min(n * 2, 40), "api_key": chave}
    try:
        r = sessao.get("https://api.si.edu/openaccess/api/v1.0/search", params=params, timeout=25)
        if r.status_code != 200:
            log(f"   smithsonian: HTTP {r.status_code}")
            return []
        dados = r.json()
    except Exception as e:
        log(f"   smithsonian: {e}")
        return []
    out = []
    for row in dados.get("response", {}).get("rows", []):
        cont = row.get("content", {})
        dnr = cont.get("descriptiveNonRepeating", {})
        for m in dnr.get("online_media", {}).get("media", []):
            if m.get("type") != "Images":
                continue
            acesso = (m.get("usage") or {}).get("access", "")
            url = m.get("content")
            for res in m.get("resources", []):
                if "High-resolution JPEG" in res.get("label", ""):
                    url = res.get("url")
            if url:
                out.append({"url": url, "fonte": "smithsonian", "titulo": row.get("title", ""),
                            "pagina": dnr.get("record_link", ""),
                            "licenca": "CC0" if acesso == "CC0" else (acesso or "ver página"),
                            "autor": dnr.get("data_source", ""), "w": 0, "h": 0})
            break
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------------------------------------
# Vídeos (desde 2026-10-11 só estes; o YouTube foi removido): bancos livres que não bloqueiam IP. Cada candidato traz
# "url" (arquivo para o trecho final, até 1080p) e "url_preview" (versão leve para a folha).
# Chaves (grátis): PEXELS_API_KEY / PIXABAY_API_KEY no ambiente ou no .env do canal.
# ---------------------------------------------------------------------------------------------
def chave_api(nome):
    return caminhos.env(nome) or None


def _ate_1080(arquivos, chave_w="width", chave_h="height"):
    """Escolhe o maior arquivo com lado menor <= 1080 (e o menor de todos para o preview)."""
    ok = [f for f in arquivos if f.get(chave_w) and f.get(chave_h)]
    if not ok:
        return None, None
    lado = lambda f: min(f[chave_w], f[chave_h])
    finais = [f for f in ok if lado(f) <= 1080] or [min(ok, key=lado)]
    return max(finais, key=lado), min(ok, key=lado)


def pexels_video(consulta, n, duracao_max, orientacao=None):
    chave = chave_api("PEXELS_API_KEY")
    if not chave:
        log("   pexels: sem PEXELS_API_KEY (pulado)")
        return []
    params = {"query": consulta, "per_page": min(n * 2, 40)}
    if orientacao in ("retrato", "paisagem", "quadrado"):
        params["orientation"] = {"retrato": "portrait", "paisagem": "landscape", "quadrado": "square"}[orientacao]
    try:
        dados = sessao.get("https://api.pexels.com/videos/search", params=params, timeout=25,
                           headers={"Authorization": chave}).json()
    except Exception as e:
        log(f"   pexels: {e}")
        return []
    out = []
    for v in dados.get("videos", []):
        dur = v.get("duration") or 0
        final, prev = _ate_1080([f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4"])
        if not final or not dur or dur > duracao_max:
            continue
        out.append({"url": final["link"], "url_preview": prev["link"], "id": f"pexels-{v['id']}",
                    "fonte": "pexels", "titulo": v.get("url", "").rstrip("/").split("/")[-1][:90],
                    "canal": (v.get("user") or {}).get("name", ""), "autor": (v.get("user") or {}).get("name", ""),
                    "duracao": dur, "pagina": v.get("url", ""), "licenca": "Pexels License (uso livre)",
                    "w": final["width"], "h": final["height"]})
        if len(out) >= n:
            break
    return out


def pixabay_video(consulta, n, duracao_max, orientacao=None):
    chave = chave_api("PIXABAY_API_KEY")
    if not chave:
        log("   pixabay: sem PIXABAY_API_KEY (pulado)")
        return []
    try:
        dados = sessao.get("https://pixabay.com/api/videos/", timeout=25,
                           params={"key": chave, "q": consulta[:100], "per_page": max(3, min(n * 2, 50)),
                                   "safesearch": "true"}).json()
    except Exception as e:
        log(f"   pixabay: {e}")
        return []
    out = []
    for v in dados.get("hits", []):
        dur = v.get("duration") or 0
        arqs = [dict(f, nome=k) for k, f in (v.get("videos") or {}).items() if f.get("url")]
        final, prev = _ate_1080(arqs)
        if not final or not dur or dur > duracao_max:
            continue
        out.append({"url": final["url"], "url_preview": prev["url"], "id": f"pixabay-{v['id']}",
                    "fonte": "pixabay", "titulo": (v.get("tags") or "")[:90], "canal": v.get("user", ""),
                    "autor": v.get("user", ""), "duracao": dur, "pagina": v.get("pageURL", ""),
                    "licenca": "Pixabay Content License (uso livre)", "w": final["width"], "h": final["height"]})
        if len(out) >= n:
            break
    return out


def pixabay(consulta, n, orientacao=None):
    """Fotos livres do Pixabay (2026-10-10). Bom para genérico (estádio, bola, torcida, cidade);
    quase não tem jogador/lance real. largeImageURL tem no máximo 1280 px no lado maior."""
    chave = chave_api("PIXABAY_API_KEY")
    if not chave:
        log("   pixabay: sem PIXABAY_API_KEY (pulado)")
        return []
    params = {"key": chave, "q": consulta[:100], "image_type": "photo", "safesearch": "true",
              "per_page": max(3, min(n * 2, 200))}
    if orientacao in ("retrato", "paisagem"):
        params["orientation"] = {"retrato": "vertical", "paisagem": "horizontal"}[orientacao]
    try:
        dados = sessao.get("https://pixabay.com/api/", params=params, timeout=25).json()
    except Exception as e:
        log(f"   pixabay: {e}")
        return []
    out = []
    for h in dados.get("hits", []):
        url = h.get("largeImageURL")
        w, a = h.get("imageWidth") or 0, h.get("imageHeight") or 0
        if not url:
            continue
        if w and a and max(w, a) > 1280:  # tamanho real do largeImageURL
            f = 1280 / max(w, a)
            w, a = round(w * f), round(a * f)
        out.append({"url": url, "fonte": "pixabay", "titulo": (h.get("tags") or "")[:90],
                    "pagina": h.get("pageURL", ""), "licenca": "Pixabay Content License (uso livre)",
                    "autor": h.get("user", ""), "w": w, "h": a})
        if len(out) >= n:
            break
    return out


def commons_video(consulta, n, duracao_max, orientacao=None):
    params = {"action": "query", "format": "json", "generator": "search",
              "gsrsearch": f"{consulta} filetype:video", "gsrnamespace": 6, "gsrlimit": min(n * 3, 50),
              "prop": "videoinfo", "viprop": "url|size|mime|derivatives|extmetadata"}
    try:
        dados = _get_com_espera("commons_video", "https://commons.wikimedia.org/w/api.php", params=params,
                                timeout=25, headers={"User-Agent": UA_WIKIMEDIA}).json()
    except Exception as e:
        log(f"   commons_video: {e}")
        return []
    paginas = sorted(dados.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in paginas:
        vi = (p.get("videoinfo") or [{}])[0]
        dur = vi.get("duration") or 0
        if not vi.get("mime", "").startswith("video/") or not dur or dur > duracao_max:
            continue
        # só versões convertidas (transcodekey): o original no upload.wikimedia.org devolve 429
        derivs = [d for d in vi.get("derivatives", []) if d.get("src") and d.get("transcodekey")
                  and "webm" in d.get("type", "")]
        final, prev = _ate_1080(derivs)
        if not final:
            continue
        meta = vi.get("extmetadata", {})
        out.append({"url": final["src"], "url_preview": prev["src"], "id": f"commons-{p.get('pageid')}",
                    "fonte": "commons", "titulo": p.get("title", "").replace("File:", "")[:90],
                    "canal": "Wikimedia Commons", "autor": _limpa_html(meta.get("Artist", {}).get("value", "")),
                    "duracao": round(dur, 1), "pagina": vi.get("descriptionurl", ""),
                    "licenca": meta.get("LicenseShortName", {}).get("value", ""),
                    "w": final["width"], "h": final["height"]})
        if len(out) >= n:
            break
    return out


def _q_archive(consulta):
    """Todas as palavras no título, assunto ou descrição; sem o arquivo de TV (C-SPAN etc. poluem)."""
    t = " AND ".join(w for w in consulta.replace('"', "").split() if len(w) > 2)
    return (f"(title:({t}) OR subject:({t}) OR description:({t})) AND mediatype:movies "
            "AND NOT collection:(tvarchive OR tvnews)")


def archive_video(consulta, n, duracao_max, orientacao=None):
    """Internet Archive (filmes de época, cinejornais, governo dos EUA: muito domínio público)."""
    try:
        dados = _get_com_espera("archive", "https://archive.org/advancedsearch.php", timeout=25, params={
            "q": _q_archive(consulta), "fl[]": ["identifier", "title", "licenseurl", "creator"],
            "rows": n * 3, "output": "json"}).json()
    except Exception as e:
        log(f"   archive: {e}")
        return []
    out = []
    for d in dados.get("response", {}).get("docs", []):
        try:
            meta = sessao.get(f"https://archive.org/metadata/{d['identifier']}", timeout=25).json()
        except Exception:
            continue
        arqs = []
        for f in meta.get("files", []):
            if not f["name"].lower().endswith(".mp4"):
                continue
            try:
                arqs.append({"url": f"https://archive.org/download/{d['identifier']}/{f['name']}",
                             "width": int(f.get("width") or 0), "height": int(f.get("height") or 0),
                             "dur": float(f.get("length") or 0)})
            except ValueError:
                continue
        final, prev = _ate_1080(arqs)
        if not final or not final["dur"] or final["dur"] > duracao_max:
            continue
        lic = d.get("licenseurl") or ""
        out.append({"url": final["url"], "url_preview": prev["url"], "id": f"archive-{d['identifier']}",
                    "fonte": "archive", "titulo": str(d.get("title", ""))[:90],
                    "canal": "Internet Archive", "autor": str(d.get("creator", ""))[:80],
                    "duracao": round(final["dur"], 1), "pagina": f"https://archive.org/details/{d['identifier']}",
                    "licenca": ("CC0/domínio público" if "publicdomain" in lic else lic) or "ver página",
                    "w": final["width"], "h": final["height"]})
        if len(out) >= n:
            break
    return out


VIDEO_LIVRES = {"pexels": pexels_video, "pixabay": pixabay_video, "commons": commons_video,
                "archive": archive_video}


def _limpa_html(s):
    import re
    return re.sub(r"<[^>]+>", "", s or "").strip()[:120]


# ---------------------------------------------------------------------------------------------
# Cache global de buscas (2026-10-10): a mesma consulta na mesma fonte (outro asset, outro bloco,
# --refazer, outro vídeo) não vai de novo à internet por cache_busca_dias. Resultado vazio não
# é guardado (pode ter sido erro/limite de taxa). Pasta: <dados>/cache/busca/.
# ---------------------------------------------------------------------------------------------


def _dias_cache():
    try:
        return float(caminhos.config_busca().get("cache_busca_dias", 7))
    except Exception:
        return 7.0


def com_cache(nome, fn):
    import hashlib

    def envolvida(*args):
        chave = hashlib.sha1(json.dumps([nome, *args], ensure_ascii=False).encode()).hexdigest()
        arq = caminhos.cache() / "busca" / f"{chave}.json"
        if arq.exists() and time.time() - arq.stat().st_mtime < _dias_cache() * 86400:
            try:
                res = json.loads(arq.read_text())
                log(f"   {nome}: cache ({len(res)})")
                return [dict(c) for c in res]
            except Exception:
                pass
        res = fn(*args)
        if res:
            arq.parent.mkdir(parents=True, exist_ok=True)
            arq.write_text(json.dumps(res, ensure_ascii=False))
        return res
    envolvida.__name__ = fn.__name__
    return envolvida


VIDEO_LIVRES = {k: com_cache(k + "_video", f) for k, f in VIDEO_LIVRES.items()}

BUSCADORES = {
    "google": google, "google_transparente": google_transparente,
    "web": web, "web_transparente": web_transparente, "commons": commons,
    "openverse": openverse, "smithsonian": smithsonian, "pixabay": pixabay,
}
BUSCADORES = {k: com_cache(k, f) for k, f in BUSCADORES.items()}
