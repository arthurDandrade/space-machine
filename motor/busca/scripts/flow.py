"""Ilustração gerada no Google Flow (flow.google.com) pela conta de quem usa, sem chave e sem pagar por imagem
(2026-11-09). Mesmas fontes do ilustrar.py, com outro gerador: "flow" (cenário cheio) e "flow_recorte"
(personagem/ícone em fundo liso, que o finalizar.py recorta). Estilo e cache são os mesmos (formato.json ›
ilustracao, com canal.json › ilustracao por cima).

Nenhum script gera sozinho no Flow. O Flow não tem API, e o Google recusa o login num navegador dirigido por
programa (testado em 2026-11-09 com o Playwright: "Esse navegador ou app pode não ser seguro"). Não contornar isso.
Quem gera é uma SESSÃO DO CLAUDE, no navegador do app, onde a pessoa já entrou na conta dela. Este script é só a fila:

1. A busca pede um desenho → flow() grava o pedido em <dados>/cache/flow/pedidos/<chave>/pedido.json e devolve
   vazio. O orquestrador para a etapa com o motivo ("N desenhos esperando o Flow").
2. A sessão do Claude lista a fila, gera cada pedido no Flow e guarda as imagens (passo a passo no CLAUDE.md):
       python -m space_machine flow                      # o que está esperando (JSON)
       python -m space_machine flow --guardar <chave> <url> [<url> ...]
       python -m space_machine flow --recusado <chave> "<motivo>"     # o Flow não quis gerar
3. A busca roda de novo: flow() acha as imagens na pasta do pedido e devolve como candidatas, e o resto (folha de
   contato, escolha do Claude, recorte, manifesto) segue igual ao de uma foto.

Medido em 2026-11-09 (plano Plus, Nano Banana 2.1, imagem 1:1): 3 opções em ~30 s, 0 créditos, 1024×1024.
Nunca pessoa real nem acontecimento real (regra do Space Machine), igual ao ilustrar.py.
"""
import argparse
import hashlib
import io
import json
import sys
import time
from urllib.parse import urlparse

from comum import caminhos, log, sessao

ASPECTO = {"paisagem": "16:9", "retrato": "3:4", "quadrado": "1:1"}
PADRAO_FLOW = {"por_asset": 3}
DE_ONDE_VEM = "flow-content.google"         # só baixa imagem deste endereço (o das imagens geradas do Flow)


def pedidos():
    p = caminhos.cache() / "flow" / "pedidos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _prontas(pasta):
    return sorted(pasta.glob("[0-9][0-9].jpg"))


def pendentes(canal=None):
    """Pedidos sem imagem e sem recusa, do mais antigo para o mais novo."""
    out = []
    for arq in sorted(pedidos().glob("*/pedido.json"), key=lambda a: a.stat().st_mtime):
        if _prontas(arq.parent) or (arq.parent / "recusado.txt").exists():
            continue
        ped = json.loads(arq.read_text())
        if canal in (None, ped.get("canal")):
            out.append(ped)
    return out


def flow(consulta, n, orientacao=None, estilo="estilo"):
    """Fonte de busca. Com as imagens do pedido já guardadas, devolve as candidatas; sem elas, põe o pedido na fila
    e devolve vazio (o orquestrador para e uma sessão do Claude gera)."""
    from ilustrar import _referencia, config
    cfg = config()
    texto = f"{cfg[estilo]}\n\nScene: {consulta}".strip() if cfg.get(estilo) else consulta
    aspecto = ASPECTO.get(orientacao, "16:9")
    chave = hashlib.sha1(f"{texto}|{aspecto}".encode()).hexdigest()[:16]
    pasta = pedidos() / chave
    prontas = _prontas(pasta)
    if not prontas:
        if (pasta / "recusado.txt").exists():
            log(f"   flow: pedido {chave} recusado pelo Flow ({(pasta / 'recusado.txt').read_text().strip()[:120]})")
            return []
        if not (pasta / "pedido.json").exists():
            pasta.mkdir(parents=True, exist_ok=True)
            ref = _referencia(cfg)
            por = int({**PADRAO_FLOW, **(cfg.get("flow") or {})}["por_asset"])
            (pasta / "pedido.json").write_text(json.dumps({
                "chave": chave, "canal": caminhos.canal().name, "pedido": consulta, "texto": texto, "aspecto": aspecto,
                "n": max(1, min(n, por, 4)), "referencia": str(ref) if ref else "",
                "quando": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False, indent=1))
        log(f"   flow: pedido {chave} na fila (esperando uma sessão do Claude gerar no Flow)")
        return []
    out = []
    for k, arq in enumerate(prontas):
        # URL de mentira, mas única e estável: o baixar_imagem() lê do cache por sha1(url)
        url = f"flow://{chave}-{k}.jpg"
        cache = caminhos.cache() / "img" / hashlib.sha1(url.encode()).hexdigest()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(arq.read_bytes())
        out.append({"url": url, "fonte": "flow", "titulo": consulta[:120], "pagina": "",
                    "licenca": "gerada (Google Flow)", "autor": "Google Flow", "w": 0, "h": 0})
    return out


def flow_recorte(consulta, n, orientacao=None):
    """Personagem/ícone num fundo liso (o finalizar.py recorta): o estilo_recorte da ficha."""
    return flow(consulta, n, "quadrado" if orientacao in (None, "qualquer") else orientacao, "estilo_recorte")


def guardar(chave, urls):
    """Baixa as imagens geradas (endereços assinados que a página do Flow mostra) para a pasta do pedido."""
    from PIL import Image
    pasta = pedidos() / chave
    if not (pasta / "pedido.json").exists():
        sys.exit(f"flow: não existe o pedido {chave}")
    k = len(_prontas(pasta))
    for url in urls:
        if urlparse(url).hostname != DE_ONDE_VEM or urlparse(url).scheme != "https":
            sys.exit(f"flow: só guardo imagem de https://{DE_ONDE_VEM}/ (veio {url[:60]})")
        r = sessao.get(url, timeout=(10, 60))
        if r.status_code != 200:
            sys.exit(f"flow: HTTP {r.status_code} ao baixar a imagem (o endereço assinado vence: pegue de novo na página)")
        k += 1
        Image.open(io.BytesIO(r.content)).convert("RGB").save(pasta / f"{k:02d}.jpg", "JPEG", quality=95)
        print(pasta / f"{k:02d}.jpg")
    with open(pedidos().parent / "geracoes.jsonl", "a") as f:
        f.write(json.dumps({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "chave": chave, "imagens": len(urls)}) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Fila de desenhos do Google Flow (sem argumento: lista o que espera).")
    ap.add_argument("--canal", help="só os pedidos deste canal (slug)")
    ap.add_argument("--guardar", nargs="+", metavar=("CHAVE", "URL"), help="baixa as imagens geradas para o pedido")
    ap.add_argument("--recusado", nargs=2, metavar=("CHAVE", "MOTIVO"), help="o Flow não gerou: tira o pedido da fila")
    a = ap.parse_args()
    if a.guardar:
        if len(a.guardar) < 2:
            ap.error("--guardar pede a chave e pelo menos um endereço de imagem")
        guardar(a.guardar[0], a.guardar[1:])
    elif a.recusado:
        pasta = pedidos() / a.recusado[0]
        if not (pasta / "pedido.json").exists():
            sys.exit(f"flow: não existe o pedido {a.recusado[0]}")
        (pasta / "recusado.txt").write_text(a.recusado[1] + "\n")
    else:
        print(json.dumps(pendentes(a.canal), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
