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
       python -m space_machine flow --referencia <canal> <nome> <url>  # a opção escolhida como ficha do personagem
3. A busca roda de novo: flow() acha as imagens na pasta do pedido e devolve como candidatas, e o resto (folha de
   contato, escolha do Claude, recorte, manifesto) segue igual ao de uma foto.

PERSONAGEM (2026-11-09): o mesmo boneco em várias poses só sai igual se o pedido levar uma imagem de referência
(medido no quarterback do teste: sem ela, cada pose vinha com outro corpo e outro rosto; com ela, capacete,
proporção, chuteira e cores se mantêm). A busca diz de quem é o desenho no começo do pedido:
    "@quarterback{an American football quarterback in a plain blue jersey…} throwing the ball overhand, side view"
     └ nome        └ ficha física (a 1ª que chegar fica valendo para o canal)   └ a pose (vazia = a própria ficha)
A ficha de cada personagem fica em <dados>/cache/flow/personagens/<canal>/<nome>/ (ficha.json + referencia.jpg). A
sessão gera primeiro a ficha (o boneco parado, de frente), escolhe uma das opções como referência
(--referencia), anexa essa imagem no pedido do Flow e só então gera as poses.

Medido em 2026-11-09 (plano Plus, Nano Banana 2.1, imagem 1:1): 3 opções em ~30 s, 0 créditos, 1024×1024.
Nunca pessoa real nem acontecimento real (regra do Space Machine), igual ao ilustrar.py.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import time
from urllib.parse import urlparse

from comum import caminhos, log, sessao

ASPECTO = {"paisagem": "16:9", "retrato": "3:4", "quadrado": "1:1"}
PADRAO_FLOW = {"por_asset": 3}
DE_ONDE_VEM = "flow-content.google"         # só baixa imagem deste endereço (o das imagens geradas do Flow)
PERSONAGEM = re.compile(r"^@([a-z0-9][a-z0-9_-]*)\s*(?:\{([^}]*)\})?\s*:?\s*(.*)$", re.S)
POSE_FICHA = "standing in a relaxed neutral pose, facing the viewer, arms at the sides, full body"
COM_REFERENCIA = ("Draw the exact same character as in the reference image, with the same face, same body proportions, "
                  "same clothes and same colors, in a new pose. ")


def pedidos():
    p = caminhos.cache() / "flow" / "pedidos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _prontas(pasta):
    return sorted(pasta.glob("[0-9][0-9].jpg"))


def pasta_personagem(canal, nome):
    return pedidos().parent / "personagens" / canal / nome


def _baixar(url):
    """A imagem de um endereço assinado do Flow, como JPEG (bytes)."""
    from PIL import Image
    if urlparse(url).hostname != DE_ONDE_VEM or urlparse(url).scheme != "https":
        sys.exit(f"flow: só guardo imagem de https://{DE_ONDE_VEM}/ (veio {url[:60]})")
    r = sessao.get(url, timeout=(10, 60))
    if r.status_code != 200:
        sys.exit(f"flow: HTTP {r.status_code} ao baixar a imagem (o endereço assinado vence: pegue de novo na página)")
    buf = io.BytesIO()
    Image.open(io.BytesIO(r.content)).convert("RGB").save(buf, "JPEG", quality=95)
    return buf.getvalue()


def pendentes(canal=None):
    """O que a sessão precisa gerar, na ordem: primeiro a ficha de cada personagem que ainda não tem referência
    ("tipo": "ficha"), depois os pedidos, juntos por personagem (cada pedido de personagem leva a "referencia" dele:
    o id da imagem no Flow, para anexar)."""
    fichas, com, sem = [], [], []
    base = pedidos().parent / "personagens"
    for arq in sorted(base.glob("*/*/ficha.json")):
        f = json.loads(arq.read_text())
        if canal in (None, f.get("canal")) and not (arq.parent / "referencia.jpg").exists():
            fichas.append({"tipo": "ficha", "canal": f["canal"], "personagem": f["nome"], "texto": f["texto"],
                           "aspecto": "1:1", "n": 3})
    for arq in sorted(pedidos().glob("*/pedido.json"), key=lambda a: a.stat().st_mtime):
        if _prontas(arq.parent) or (arq.parent / "recusado.txt").exists():
            continue
        ped = json.loads(arq.read_text())
        if canal not in (None, ped.get("canal")):
            continue
        if ped.get("personagem"):
            f = json.loads((pasta_personagem(ped["canal"], ped["personagem"]) / "ficha.json").read_text())
            ped["referencia_flow"] = f.get("flow_id") or ""
            com.append(ped)
        else:
            sem.append(ped)
    com.sort(key=lambda p: p["personagem"])
    return fichas + com + sem


def _personagem(consulta, cfg, estilo):
    """("nome", ficha, pose) quando a consulta começa por @nome; cria a ficha do personagem na 1ª vez. A ficha
    física vem entre chaves; sem ela, de canal.json › personagens. None = pedido comum."""
    m = PERSONAGEM.match(consulta.strip())
    if not m:
        return None
    nome, ficha, pose = m.group(1), (m.group(2) or "").strip(), m.group(3).strip(" ,.")
    pasta = pasta_personagem(caminhos.canal().name, nome)
    arq = pasta / "ficha.json"
    if arq.exists():
        ficha = json.loads(arq.read_text())["ficha"]          # a 1ª ficha fica valendo: o boneco não muda no meio
    else:
        ficha = ficha or (caminhos.canal_json().get("personagens") or {}).get(nome, "")
        if not ficha:
            return None
        pasta.mkdir(parents=True, exist_ok=True)
        texto = f"{cfg[estilo]}\n\nScene: {ficha}, {POSE_FICHA}".strip()
        arq.write_text(json.dumps({"nome": nome, "canal": caminhos.canal().name, "ficha": ficha, "texto": texto,
                                   "flow_id": "", "quando": time.strftime("%Y-%m-%d %H:%M:%S")},
                                  ensure_ascii=False, indent=1))
    return nome, ficha, pose


def flow(consulta, n, orientacao=None, estilo="estilo"):
    """Fonte de busca. Com as imagens do pedido já guardadas, devolve as candidatas; sem elas, põe o pedido na fila
    e devolve vazio (o orquestrador para e uma sessão do Claude gera)."""
    from ilustrar import _referencia, config
    cfg = config()
    quem = _personagem(consulta, cfg, estilo) if cfg.get(estilo) else None
    if quem and not quem[2]:
        # o pedido é o próprio personagem, sem pose: a candidata é a referência dele (uma só, para o desenho do
        # título ser o mesmo boneco das poses)
        ref = pasta_personagem(caminhos.canal().name, quem[0]) / "referencia.jpg"
        if not ref.exists():
            log(f"   flow: personagem {quem[0]} sem referência ainda (esperando a sessão gerar a ficha no Flow)")
            return []
        url = f"flow://personagem-{caminhos.canal().name}-{quem[0]}.jpg"
        cache = caminhos.cache() / "img" / hashlib.sha1(url.encode()).hexdigest()
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(ref.read_bytes())
        return [{"url": url, "fonte": "flow", "titulo": consulta[:120], "pagina": "", "licenca": "gerada (Google Flow)",
                 "autor": "Google Flow", "w": 0, "h": 0}]
    if quem:
        texto = f"{COM_REFERENCIA}{cfg[estilo]}\n\nScene: {quem[1]}, {quem[2]}".strip()
    else:
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
                "personagem": quem[0] if quem else "",
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
    pasta = pedidos() / chave
    if not (pasta / "pedido.json").exists():
        sys.exit(f"flow: não existe o pedido {chave}")
    k = len(_prontas(pasta))
    for url in urls:
        k += 1
        (pasta / f"{k:02d}.jpg").write_bytes(_baixar(url))
        print(pasta / f"{k:02d}.jpg")
    _anotar(chave, len(urls))
    r = ritmo()
    log(f"ritmo: {r['no_lote']} de {r['lote']} neste lote" + (f"; lote cheio, o próximo a partir de {r['esperar_ate']}"
                                                              if not r["pode"] else f"; espere {r['espaco_s']} s antes do próximo"))


# O ritmo das gerações (2026-11-10). O Flow é a conta de uma pessoa: 108 pedidos seguidos, um a cada ~40 s, passaram
# na hora, mas horas depois o Google respondeu "atividade incomum" ao 1º pedido de uma fila nova. Agora a fila sai em
# LOTES pequenos com pausa entre eles; quem gera pergunta `--lote` e só faz o que ele devolver. Os números são de
# <dados>/space_machine.json › flow (lote, pausa_min, espaco_s, por_dia; por_dia = 0 não limita o dia).
RITMO = {"lote": 10, "pausa_min": 15, "espaco_s": 20, "por_dia": 0}


def _ritmo_cfg():
    return {**RITMO, **(caminhos.config_sistema().get("flow") or {})}


def _geracoes():
    """Os horários (epoch) de todas as gerações guardadas, em ordem."""
    arq = pedidos().parent / "geracoes.jsonl"
    out = []
    for linha in arq.read_text().splitlines() if arq.exists() else []:
        try:
            out.append(time.mktime(time.strptime(json.loads(linha)["quando"], "%Y-%m-%d %H:%M:%S")))
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    return sorted(out)


def ritmo(agora=None):
    """Quantos pedidos dá para gerar AGORA sem virar rajada: {"pode": n, "no_lote": feitos no lote atual, "hoje":
    gerações nas últimas 24 h, "esperar_ate": "HH:MM" quando o lote encheu (ou o dia), "espaco_s": pausa entre um
    pedido e o seguinte}. Um lote são gerações seguidas, sem um intervalo de pausa_min entre elas."""
    cfg, agora, ts = _ritmo_cfg(), agora or time.time(), _geracoes()
    pausa = cfg["pausa_min"] * 60
    hoje = [t for t in ts if agora - t < 86400]
    no_lote = 0
    if ts and agora - ts[-1] < pausa:
        no_lote = 1
        for k in range(len(ts) - 1, 0, -1):
            if ts[k] - ts[k - 1] >= pausa:
                break
            no_lote += 1
    pode, ate = max(0, cfg["lote"] - no_lote), None
    if pode == 0:
        ate = ts[-1] + pausa
    if cfg["por_dia"] and len(hoje) >= cfg["por_dia"]:
        pode, ate = 0, max(ate or 0, hoje[len(hoje) - cfg["por_dia"]] + 86400)
    elif cfg["por_dia"]:
        pode = min(pode, cfg["por_dia"] - len(hoje))
    return {"pode": pode, "no_lote": no_lote, "lote": cfg["lote"], "hoje": len(hoje), "por_dia": cfg["por_dia"],
            "pausa_min": cfg["pausa_min"], "espaco_s": cfg["espaco_s"],
            "esperar_ate": time.strftime("%Y-%m-%d %H:%M", time.localtime(ate)) if ate else None}


def _anotar(chave, imagens):
    with open(pedidos().parent / "geracoes.jsonl", "a") as f:
        f.write(json.dumps({"quando": time.strftime("%Y-%m-%d %H:%M:%S"), "chave": chave, "imagens": imagens}) + "\n")


def referencia(canal, nome, url):
    """A opção escolhida como ficha do personagem: guarda a imagem e o id dela no Flow (o que a sessão anexa nos
    pedidos de pose)."""
    pasta = pasta_personagem(canal, nome)
    arq = pasta / "ficha.json"
    if not arq.exists():
        sys.exit(f"flow: não existe o personagem {nome} no canal {canal}")
    (pasta / "referencia.jpg").write_bytes(_baixar(url))
    f = json.loads(arq.read_text())
    f["flow_id"] = urlparse(url).path.rsplit("/", 1)[-1]
    arq.write_text(json.dumps(f, ensure_ascii=False, indent=1))
    _anotar(f"ficha:{canal}:{nome}", 1)        # a ficha também é uma geração: conta no ritmo
    print(pasta / "referencia.jpg", f["flow_id"])


def main():
    ap = argparse.ArgumentParser(description="Fila de desenhos do Google Flow (sem argumento: lista o que espera).")
    ap.add_argument("--canal", help="só os pedidos deste canal (slug)")
    ap.add_argument("--lote", action="store_true",
                    help="o que dá para gerar AGORA sem rajada: {fila, agora: [pedidos deste lote], ritmo}")
    ap.add_argument("--guardar", nargs="+", metavar=("CHAVE", "URL"), help="baixa as imagens geradas para o pedido")
    ap.add_argument("--recusado", nargs=2, metavar=("CHAVE", "MOTIVO"), help="o Flow não gerou: tira o pedido da fila")
    ap.add_argument("--referencia", nargs=3, metavar=("CANAL", "NOME", "URL"),
                    help="a imagem escolhida como ficha do personagem (as poses dele são geradas com ela anexada)")
    a = ap.parse_args()
    if a.referencia:
        referencia(*a.referencia)
    elif a.guardar:
        if len(a.guardar) < 2:
            ap.error("--guardar pede a chave e pelo menos um endereço de imagem")
        guardar(a.guardar[0], a.guardar[1:])
    elif a.recusado:
        pasta = pedidos() / a.recusado[0]
        if not (pasta / "pedido.json").exists():
            sys.exit(f"flow: não existe o pedido {a.recusado[0]}")
        (pasta / "recusado.txt").write_text(a.recusado[1] + "\n")
    elif a.lote:
        fila, r = pendentes(a.canal), ritmo()
        print(json.dumps({"fila": len(fila), "agora": fila[:r["pode"]], "ritmo": r}, ensure_ascii=False, indent=1))
    else:
        print(json.dumps(pendentes(a.canal), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
