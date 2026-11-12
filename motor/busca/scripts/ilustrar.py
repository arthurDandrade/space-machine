"""Ilustração gerada pelo Gemini (Nano Banana), para os tipos de asset "ilustracao" (cenário cheio) e "recorte" (criatura,
ícone, personagem: sai em fundo liso e o finalizar.py tira o fundo) do formato bestiário (2026-11-03).

Entra na busca como mais uma fonte ("gemini" e "gemini_recorte" no fontes.py): a consulta é o pedido da cena, o estilo
vem da ficha do formato (formato.json › ilustracao: "estilo" e "estilo_recorte") com o canal.json › ilustracao por cima,
e cada imagem gerada é gravada no
cache de imagens com uma URL "gemini://..." — o baixar_imagem() acha no cache e o resto da busca (folha de
contato, escolha do Claude, manifesto) segue igual ao de uma foto.

Chave: GEMINI_API_KEY no .env do canal (ou dos dados). Sem chave, a fonte é pulada.
Preço (2026-11, gemini-nano-banana-2.1): ~US$ 0,05 por imagem em 2K, sem cota grátis. Cada imagem gerada vai
para <dados>/cache/gemini/gastos.jsonl.

Pessoa real (regra de 2026-11-11): foto real primeiro; desenho de pessoa real só quando nenhuma foto serve, e o
pedido começa com "real:" (estilo_do_pedido troca a frase "Never depict a real person" do estilo pelo pedido de
caricatura). Sem "real:", o estilo da ficha continua dizendo ao modelo para não retratar ninguém real.

Uso à mão (teste): python ilustrar.py <pasta de saída> "<pedido>" [--n 1] [--orientacao paisagem]
"""
import argparse
import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from comum import caminhos, log, sessao

URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
REVISAO = "2026-05-20"
PADRAO = {"modelo": "gemini-nano-banana-2.1", "tamanho": "2K", "por_asset": 3, "preco_usd": 0.0504,
          "estilo": "", "estilo_recorte": "", "referencia": ""}
ASPECTO = {"paisagem": "16:9", "retrato": "3:4", "quadrado": "1:1"}


def config():
    """formato.json › ilustracao, com canal.json › ilustracao por cima."""
    return {**PADRAO, **caminhos.ficha().get("ilustracao", {}), **caminhos.canal_json().get("ilustracao", {})}


REAL = re.compile(r"^\s*real\s*:\s*", re.I)
SEM_REAL = re.compile(r"\s*Never depict a real, identifiable person[^.]*\.")
PESSOA_REAL = ("The scene names a real, famous person: draw them as a friendly, recognizable caricature in this "
               "same style, never photorealistic.")


def estilo_do_pedido(cfg, estilo, pedido):
    """(estilo, pedido) para o texto do gerador. Pedido que começa com "real:" é o desenho de uma pessoa real (regra
    de 2026-11-11: pode, desde que não tome o lugar de uma foto real que existe; quem decide é o storyboard): o
    prefixo sai e a frase "Never depict a real, identifiable person" do estilo vira o pedido de caricatura
    (formato.json › ilustracao › pessoa_real, ou o PESSOA_REAL). Sem "real:", o estilo fica igual — e a chave dos
    pedidos do Flow, que é o texto inteiro, também."""
    est = cfg.get(estilo) or ""
    if not REAL.match(pedido):
        return est, pedido
    est = SEM_REAL.sub("", est).strip()
    return f"{est} {cfg.get('pessoa_real') or PESSOA_REAL}".strip(), REAL.sub("", pedido, count=1)


def _referencia(cfg):
    """Imagem que trava o estilo: a do canal (identidade/estilo_ilustracao.*) ou a do formato (ficha)."""
    for p in sorted((caminhos.canal() / "identidade").glob("estilo_ilustracao.*")):
        return p
    if cfg.get("referencia"):
        p = caminhos.formato() / cfg["referencia"]
        return p if p.exists() else None
    return None


def _imagens(no):
    """Todos os blocos {"type": "image", "data": ...} da resposta, em ordem (a última é a final)."""
    if isinstance(no, dict):
        if no.get("type") == "image" and no.get("data"):
            yield no
        for v in no.values():
            yield from _imagens(v)
    elif isinstance(no, list):
        for v in no:
            yield from _imagens(v)


def gerar(pedido, orientacao=None, cfg=None, estilo="estilo"):
    """Uma imagem. Devolve os bytes (JPEG) ou None. `estilo` é a chave do estilo na config ("estilo_recorte")."""
    cfg = cfg or config()
    chave = caminhos.env("GEMINI_API_KEY")
    if not chave:
        log("   gemini: sem GEMINI_API_KEY (pulado)")
        return None
    est, pedido = estilo_do_pedido(cfg, estilo, pedido)
    texto = f"{est}\n\nScene: {pedido}".strip() if est else pedido
    partes = [{"type": "text", "text": texto}]
    ref = _referencia(cfg)
    if ref:
        partes[0]["text"] += "\n\nMatch the drawing style of the attached reference image exactly (not its subject)."
        mime = "image/png" if ref.suffix.lower() == ".png" else "image/jpeg"
        partes.append({"type": "image", "mime_type": mime, "data": base64.b64encode(ref.read_bytes()).decode()})
    corpo = {"model": cfg["modelo"], "input": partes,
             "response_format": {"type": "image", "mime_type": "image/jpeg",
                                 "aspect_ratio": ASPECTO.get(orientacao, "16:9"), "image_size": cfg["tamanho"]}}
    for tentativa in range(3):
        try:
            r = sessao.post(URL, json=corpo, timeout=(10, 180),
                            headers={"x-goog-api-key": chave, "Api-Revision": REVISAO})
        except Exception as e:
            log(f"   gemini: {e} (tentativa {tentativa + 1})")
            time.sleep(5 * (tentativa + 1))
            continue
        if r.status_code in (429, 500, 503):
            log(f"   gemini: HTTP {r.status_code} (tentativa {tentativa + 1})")
            time.sleep(15 * (tentativa + 1))
            continue
        if r.status_code != 200:
            log(f"   gemini: HTTP {r.status_code}: {r.text[:300]}")
            return None
        imgs = list(_imagens(r.json()))
        if not imgs:
            # recusa (filtro de segurança) ou resposta só de texto: não adianta repetir o mesmo pedido
            log(f"   gemini: resposta sem imagem: {r.text[:300]}")
            return None
        gasto = caminhos.cache() / "gemini" / "gastos.jsonl"
        gasto.parent.mkdir(parents=True, exist_ok=True)
        with open(gasto, "a") as f:
            f.write(json.dumps({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "canal": caminhos.canal().name,
                                "modelo": cfg["modelo"], "usd": cfg["preco_usd"], "pedido": pedido[:200]},
                               ensure_ascii=False) + "\n")
        return base64.b64decode(imgs[-1]["data"])
    return None


def gemini(consulta, n, orientacao=None, estilo="estilo"):
    """Fonte de busca: até `por_asset` imagens geradas para a consulta (o n da busca é alvo × 2: caro demais)."""
    cfg = config()
    out = []
    for k in range(min(n, int(cfg["por_asset"]))):
        dados = gerar(consulta, orientacao, cfg, estilo)
        if not dados:
            break
        # URL de mentira, mas única e estável: o baixar_imagem() lê do cache por sha1(url)
        url = f"gemini://{hashlib.sha1(f'{consulta}|{orientacao}|{k}|{time.time()}'.encode()).hexdigest()[:16]}.jpg"
        cache = caminhos.cache() / "img" / hashlib.sha1(url.encode()).hexdigest()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(dados)
        out.append({"url": url, "fonte": "gemini", "titulo": consulta[:120], "pagina": "",
                    "licenca": "gerada (Gemini)", "autor": cfg["modelo"], "w": 0, "h": 0})
    return out


def gemini_recorte(consulta, n, orientacao=None):
    """Criatura/ícone/personagem num fundo liso (o finalizar.py recorta): o estilo_recorte da ficha."""
    return gemini(consulta, n, "quadrado" if orientacao in (None, "qualquer") else orientacao, "estilo_recorte")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saida")
    ap.add_argument("pedido")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--orientacao", default="paisagem")
    ap.add_argument("--recorte", action="store_true", help="estilo de recorte (fundo liso)")
    a = ap.parse_args()
    pasta = Path(a.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    for k in range(a.n):
        dados = gerar(a.pedido, a.orientacao, estilo="estilo_recorte" if a.recorte else "estilo")
        if not dados:
            sys.exit(1)
        (pasta / f"ilustracao_{k + 1:02d}.jpg").write_bytes(dados)
        print(pasta / f"ilustracao_{k + 1:02d}.jpg")


if __name__ == "__main__":
    main()
