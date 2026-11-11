"""Thumbnail feita pelo sistema: você escolhe um MODELO e ele monta a thumbnail do vídeo (2026-11-11).

Os modelos são do FORMATO do canal (formato.json › thumbnail.modelos → formatos/<formato>/thumbs/modelos.json):
grade de fotos, grade de logos, grade de círculos, dupla com título, faixa e foto... Formato sem modelos não mostra
a opção no painel.

  python -m space_machine thumb <pasta do vídeo> --modelo grade_logos [--refazer] [--obs "..."] [--fundo "#FFE14D"]
  python -m space_machine thumb <pasta do vídeo> --modelos          # lista os modelos do formato do canal

O que acontece, em <vídeo>/thumb/<modelo>/ (uma pasta com a cara da de um bloco, para o motor rodar nela igual):
  1. planejar  o Claude lê o roteiro e a lista do que o vídeo JÁ TEM (desenhos do elenco, fotos e logos escolhidos na
               produção) e decide o que entra em cada lugar do modelo e o texto de cada um (prompts/thumbnail.md do
               formato). O que o vídeo já tem é reaproveitado; o que falta vira um pedido novo.
  2. buscar    os pedidos novos passam pela MESMA busca da produção (motor/busca/scripts/buscar.py): foto e logo
               reais nas fontes do formato; desenho, na fila do Google Flow. Com desenho na fila, para em
               "esperando o Flow" (quem gera é uma sessão do Claude, ver o CLAUDE.md) e continua quando você rodar
               de novo.
  3. escolher  a mesma escolha da produção (com a regra de imagem real certa ou nenhuma, se o formato tiver).
  4. compor    motor/thumb/compor_thumb.py desenha em 1280×720 e a imagem vira a thumbnail do vídeo
               (thumbnail.png na ficha do vídeo; a anterior vai para o Lixo do Mac).

O plano pede alguns itens de reserva: se uma imagem não for achada, a grade fecha com o seguinte.
A cor do fundo é sua: a do formato, uma das sugeridas ou qualquer outra (--fundo; no painel, as bolinhas de cor). A que
você usar fica como a do canal (canal.json › thumbnail.fundo). Trocar só a cor não refaz o plano: redesenha.
Nunca desenho de pessoa real: pessoa real entra por foto (regra do sistema, repetida no prompt).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import capas, estado
from . import motor_claude
from .canal import canal_do_bloco, contexto, rodar_script
from .sistema import DADOS, MOTOR, FORMATO_PADRAO, arquivo_formato, ficha_formato, gravar_json, ler_json

REAIS = ("foto", "historica", "logo")


# ---------------- modelos do formato ----------------
def _config(formato):
    """O modelos.json do formato ({"estilo", "modelos"}), ou None se o formato não faz thumbnail."""
    onde = (ficha_formato(formato or FORMATO_PADRAO).get("thumbnail") or {}).get("modelos")
    if not onde:
        return None
    arq = arquivo_formato(onde, formato, exigir=False)
    return ler_json(arq) if arq.is_file() else None


def modelos(c):
    """Os modelos de thumbnail do formato do canal: [{"id", "nome", "descricao", "quando", "itens"}]."""
    cfg = _config(c.get("formato")) or {}
    return [{k: m.get(k) for k in ("id", "nome", "descricao", "quando", "itens")} for m in cfg.get("modelos", [])]


def _modelo(c, modelo_id):
    cfg = _config(c.get("formato"))
    if not cfg:
        raise ValueError("o formato deste canal ainda não tem modelos de thumbnail")
    m = next((m for m in cfg.get("modelos", []) if m.get("id") == modelo_id), None)
    if not m:
        raise ValueError(f"o formato não tem o modelo de thumbnail \"{modelo_id}\"")
    return m, cfg.get("estilo") or {}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cor_valida(cor):
    """"#RRGGBB" em maiúsculas, ou "" se não for uma cor."""
    cor = str(cor or "").strip()
    return cor.upper() if re.fullmatch(r"#[0-9a-fA-F]{6}", cor) else ""


def estilo_com_fundo(estilo, fundo):
    """O estilo do formato com outra cor de fundo. O texto e as bordas continuam legíveis: sobre fundo escuro saem
    brancos; e o destaque, se ficar parecido com o fundo (vermelho sobre vermelho), vira amarelo ou branco."""
    fundo = cor_valida(fundo)
    if not fundo or fundo == cor_valida(estilo.get("fundo") or "#FFFFFF"):
        return dict(estilo)
    r, g, b = _rgb(fundo)
    escuro = (0.299 * r + 0.587 * g + 0.114 * b) < 140
    e = {**estilo, "fundo": fundo}
    if escuro:
        e.update(cor_texto="#FFFFFF", cor_borda="#FFFFFF")
    longe = lambda c: sum((x - y) ** 2 for x, y in zip(_rgb(c), (r, g, b))) ** 0.5
    if longe(e.get("cor_destaque") or "#E3120B") < 150:
        e["cor_destaque"] = max((x for x in ("#FFD400", "#FFFFFF", "#111111") if x != e.get("cor_texto")), key=longe)
    return e


def fundos(c):
    """As cores de fundo que o painel oferece e a que vale agora para o canal (a última que você usou nele; sem
    nenhuma, a do formato)."""
    cfg = _config(c.get("formato")) or {}
    do_formato = cor_valida((cfg.get("estilo") or {}).get("fundo")) or "#FFFFFF"
    lista = [x for x in (cor_valida(f) for f in cfg.get("fundos") or []) if x] or [do_formato]
    cj = ler_json(Path(c["raiz"]) / "canal.json", {}) or {}
    atual = cor_valida((cj.get("thumbnail") or {}).get("fundo")) or do_formato
    return {"cores": lista, "atual": atual, "do_formato": do_formato}


def _guardar_fundo(c, fundo):
    """A cor que você usou fica como a do canal (canal.json › thumbnail.fundo): o próximo vídeo já começa nela."""
    arq = Path(c["raiz"]) / "canal.json"
    cj = ler_json(arq, {}) or {}
    if (cj.get("thumbnail") or {}).get("fundo") != fundo:
        cj.setdefault("thumbnail", {})["fundo"] = fundo
        gravar_json(arq, cj)


def _compor(pedido, arq_pedido, c=None):
    gravar_json(arq_pedido, pedido)
    r = subprocess.run([sys.executable, str(MOTOR / "thumb" / "compor_thumb.py"), str(arq_pedido)],
                       capture_output=True, text=True)
    if r.returncode:
        raise ValueError("não consegui desenhar a thumbnail: " + (r.stderr.strip().splitlines() or ["?"])[-1][:300])
    return Path(r.stdout.strip().splitlines()[-1])


def previa(c, modelo_id):
    """A imagem de exemplo do modelo (os lugares em cinza), para o painel. Fica em cache/thumbs/ dos dados e é
    refeita quando o modelos.json ou o compositor mudam."""
    m, estilo = _modelo(c, modelo_id)
    formato = c.get("formato") or FORMATO_PADRAO
    fontes = [arquivo_formato((ficha_formato(formato).get("thumbnail") or {})["modelos"], formato),
              MOTOR / "thumb" / "compor_thumb.py"]
    versao = int(max(f.stat().st_mtime for f in fontes))
    pasta = DADOS / "cache" / "thumbs"
    saida = pasta / f"{formato}_{modelo_id}_{versao}.png"
    if not saida.exists():
        pasta.mkdir(parents=True, exist_ok=True)
        for velho in pasta.glob(f"{formato}_{modelo_id}_*"):
            velho.unlink()
        itens = [{"legenda": "LEGENDA", "titulo": "TÍTULO *DESTAQUE*", "tipo": (m.get("tipos") or ["foto"])[0]}
                 for _ in range(int(m.get("itens") or 1))]
        _compor({"modelo": m, "estilo": estilo, "itens": itens, "titulo": "TÍTULO DO *VÍDEO*", "saida": str(saida)},
                pasta / f"{formato}_{modelo_id}_{versao}.json")
    return saida


# ---------------- estado (o painel lê) ----------------
def pasta(vd):
    return Path(vd) / "thumb"


def ler_estado(vd):
    est = ler_json(pasta(vd) / "estado.json", {}) or {}
    pid = pasta(vd) / "pid"
    est["rodando"] = pid.exists() and estado._vivo(pid.read_text().strip())
    if est.get("status") == "rodando" and not est["rodando"]:
        est.update(status="erro", erro="parou no meio (o processo foi encerrado)")
    return est


def _marcar(vd, **campos):
    arq = pasta(vd) / "estado.json"
    arq.parent.mkdir(exist_ok=True)
    est = ler_json(arq, {}) or {}
    est.update(campos, atualizado=time.strftime("%Y-%m-%d %H:%M:%S"))
    gravar_json(arq, est)


# ---------------- o que o vídeo já tem ----------------
def _projetos(vd):
    """As pastas de produção do vídeo que têm manifesto: <vídeo>/producao (vídeo inteiro) ou os blocos."""
    vd = Path(vd)
    out = [vd / "producao"] if (vd / "producao" / "manifesto.json").exists() else []
    b = vd / "blocos"
    if b.is_dir():
        out += sorted(p for p in b.iterdir() if (p / "manifesto.json").exists())
    return out


def _do_elenco(vd):
    """{nome do elenco: (tipo, descrição, tópico)}, como o storyboard pediu (o manifesto não guarda o que entrou
    só como símbolo do tópico, e o arquivo do elenco não diz se é logo, foto ou desenho)."""
    out = {}

    def andar(o, topico):
        if isinstance(o, dict):
            if o.get("elenco") and o.get("tipo"):
                out.setdefault(o["elenco"], (o["tipo"], o.get("descricao") or "", topico))
            for v in o.values():
                andar(v, topico)
        elif isinstance(o, list):
            for v in o:
                andar(v, topico)
    for proj in _projetos(vd):
        for it in (ler_json(proj / "cenas.json", {}) or {}).get("itens", []):
            andar(it, it.get("nome", ""))
    return out


def inventario(vd):
    """Imagens que a produção já escolheu ou gerou: [{"ref", "tipo", "descricao", "topico", "arquivo"}], uma por
    arquivo. É daqui que a thumbnail sai sem buscar nada."""
    vistos, out = set(), []
    elenco = _do_elenco(vd)
    pasta_elenco = (Path(vd) / "elenco").resolve()

    def entra(arq, tipo, descricao, topico):
        if arq in vistos:
            return
        vistos.add(arq)
        if arq.parent == pasta_elenco and arq.stem in elenco:
            tipo, d, t = elenco[arq.stem]
            descricao, topico = d or descricao, t or topico
        out.append({"ref": f"v{len(out) + 1}", "tipo": tipo, "descricao": descricao, "topico": topico,
                    "arquivo": str(arq)})
    for proj in _projetos(vd):
        for m in (ler_json(proj / "manifesto.json", {}) or {}).get("assets", []):
            arq = (proj / m.get("arquivo", "")).resolve()
            if m.get("arquivo") and arq.is_file() and arq.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                entra(arq, m.get("tipo", ""), m.get("descricao", ""), m.get("item_nome", ""))
    # o que está no elenco e o manifesto não cita (o símbolo de cada tópico; desenhos de outro vídeo do canal)
    for arq in sorted(pasta_elenco.glob("*.png")):
        entra(arq.resolve(), "recorte", arq.stem.replace("-", " "), "")
    return out


def _topicos(vd):
    for proj in _projetos(vd):
        nomes = [it.get("nome", "") for it in (ler_json(proj / "plano.json", {}) or {}).get("itens", [])]
        if len(nomes) > 1:
            return [n for n in nomes if n]
    return []


def _roteiro(vd, limite=9000):
    vd = Path(vd)
    from . import fichas
    for arq in (fichas.roteiro(vd), vd / "producao" / "roteiro.txt"):
        if arq.exists():
            return arq.read_text()[:limite]
    partes = [b.read_text() for b in sorted((vd / "blocos").glob("*/roteiro.txt"))] if (vd / "blocos").is_dir() else []
    return "\n\n".join(partes)[:limite]


# ---------------- 1. planejar ----------------
SCHEMA = {"type": "object", "required": ["itens"], "properties": {
    "titulo": {"type": "string"},
    "itens": {"type": "array", "items": {"type": "object", "required": ["legenda"], "properties": {
        "legenda": {"type": "string"}, "titulo": {"type": "string"}, "usar": {"type": "string"},
        "tipo": {"type": "string", "enum": ["foto", "historica", "logo", "recorte"]},
        "descricao": {"type": "string"}, "buscas": {"type": "array", "items": {"type": "string"}}}}}}}


def planejar(vd, c, m, obs=""):
    inv = inventario(vd)
    tipos = m.get("tipos") or ["foto"]
    n, reservas = int(m.get("itens") or 1), int(m.get("reservas") or 0)
    pedido = {
        "video": estado.titulo_video(vd),
        "topicos": _topicos(vd),
        "modelo": {k: m.get(k) for k in ("nome", "descricao", "quando", "layout", "forma")},
        "quantos_itens": n, "reservas": reservas,
        "tipos_que_cabem": tipos,
        "pede_titulo_geral": bool(m.get("titulo")), "pede_titulo_por_item": bool(m.get("titulo_por_item")),
        "o_que_o_video_ja_tem": [f"{i['ref']} · {i['tipo']} · {i['topico']} · {i['descricao']}"[:200]
                                 for i in inv if i["tipo"] in tipos],
        "roteiro": _roteiro(vd),
    }
    if obs:
        pedido["observacao_de_quem_produz"] = obs
    r = motor_claude.chamar("thumbnail", motor_claude.prompt("thumbnail", c), json.dumps(pedido, ensure_ascii=False),
                            schema=SCHEMA, canal=c, ctx={**contexto(vd), "bloco": "thumb"})
    por_ref = {i["ref"]: i for i in inv}
    itens = []
    for it in (r.get("itens") or [])[:n + reservas]:
        novo = {"legenda": str(it.get("legenda") or "").strip(), "titulo": str(it.get("titulo") or "").strip()}
        usar = por_ref.get(str(it.get("usar") or "").strip())
        if usar:
            novo.update(usar=usar["ref"], imagem=usar["arquivo"], tipo=usar["tipo"], descricao=usar["descricao"])
        else:
            tipo = it.get("tipo") if it.get("tipo") in tipos else tipos[0]
            buscas = [str(b).strip() for b in (it.get("buscas") or []) if str(b).strip()][:4]
            if not buscas and str(it.get("descricao") or "").strip():
                buscas = [str(it["descricao"]).strip()]       # desenho: a descrição já é o pedido
            if not buscas:
                continue
            novo.update(tipo=tipo, descricao=str(it.get("descricao") or buscas[0]).strip(), buscas=buscas)
        itens.append(novo)
    if len(itens) < n:
        raise ValueError(f"o plano veio com {len(itens)} item(ns) e o modelo pede {n}")
    return {"modelo": m["id"], "titulo": str(r.get("titulo") or "").strip(), "itens": itens}


# ---------------- 2 e 3. buscar e escolher (o motor da produção, na pasta da thumbnail) ----------------
def _orientacao(m):
    if m.get("layout") == "faixa":
        return "paisagem"
    if m.get("layout") == "grade" and m.get("forma") == "moldura" and int(m.get("colunas") or 4) <= 3:
        return "paisagem"
    return "qualquer" if m.get("layout") == "grade" and m.get("forma") == "moldura" else "quadrado"


def _plano_do_motor(vd, m, plano):
    """O plano.json que o buscar.py e a escolha entendem: um item, e cada pedido novo numa cena só dele."""
    cenas = []
    for k, it in enumerate(plano["itens"]):
        if it.get("imagem"):
            continue
        aid = f"T-{k + 1:02d}-a"
        it["asset"] = aid
        cenas.append({"id": aid[:-2], "inicio": 0, "fim": 0,
                      "fala": f"Thumbnail do vídeo, item \"{it['legenda'] or it['titulo']}\": {it['descricao']}",
                      "assets": [{"id": aid, "tipo": it["tipo"], "papel": "card", "orientacao": _orientacao(m),
                                  "gatilho": it["legenda"] or it["titulo"] or "thumb", "tempo": 0,
                                  "descricao": it["descricao"], "buscas": it["buscas"]}]})
    return {"titulo": estado.titulo_video(vd), "itens": [{"id": "T", "nome": "Thumbnail", "inicio": 0, "fim": 0,
                                                           "cenas": cenas}]} if cenas else None


def _esperando_flow(c):
    from .rodar import esperando_flow
    return esperando_flow(c)


def _buscar(p, c):
    """Devolve quantos desenhos ficaram esperando o Flow (0 = pode seguir)."""
    cand = p / "_work" / "candidatos"
    plano = ler_json(p / "plano.json")
    ids = [a["id"] for it in plano["itens"] for ce in it["cenas"] for a in ce["assets"]]
    man = {x["id"] for x in (ler_json(p / "manifesto.json", {}) or {}).get("assets", [])}
    falta = [i for i in ids if i not in man and not (ler_json(cand / i / "candidatos.json") or {}).get("candidatos")]
    if not falta:
        return 0
    for i in falta:                                   # sem candidato da outra vez: busca de novo
        (cand / i / "candidatos.json").unlink(missing_ok=True)
    cod, saida = rodar_script(c, "buscar.py", p, timeout=3600, log=p / "log_buscar.txt")
    if cod != 0:
        raise ValueError("a busca das imagens falhou: " + saida.strip()[-300:])
    sem = [i for i in falta if not (ler_json(cand / i / "candidatos.json") or {}).get("candidatos")]
    gerados = {a["id"] for it in plano["itens"] for ce in it["cenas"] for a in ce["assets"] if a["tipo"] not in REAIS}
    if any(i in gerados for i in sem) and _esperando_flow(c):
        for i in sem:
            (cand / i / "candidatos.json").unlink(missing_ok=True)
        return sum(1 for i in sem if i in gerados)
    return 0


def _escolher(p):
    from .escolher import Bloco
    b = Bloco(p)
    feitos = b.rodar()
    if b.parou_por_limite:
        b.finalizar(feitos)
        raise ValueError("limite de uso da assinatura do Claude: rode de novo depois que ele passar")
    man = {x["id"] for x in ler_json(p / "manifesto.json", {"assets": []})["assets"]}
    pendentes = [aid for aid, e in b.escolhas.items() if not e.get("pular") and aid not in man and aid not in feitos]
    falhou = b.finalizar(feitos + pendentes)
    b.conferir([i for i in feitos + pendentes if i not in falhou])


# ---------------- tudo ----------------
def fazer(vd, modelo_id, refazer=False, obs="", fundo=""):
    vd = Path(vd).resolve()
    _, c = canal_do_bloco(vd / "thumb")
    try:
        m, estilo = _modelo(c, modelo_id)
        fundo = cor_valida(fundo) or fundos(c)["atual"]
        estilo = estilo_com_fundo(estilo, fundo)
        p = pasta(vd) / modelo_id
        if refazer and p.exists():
            import shutil
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
        _marcar(vd, status="rodando", modelo=modelo_id, modelo_nome=m.get("nome", modelo_id), erro="", aviso="",
                etapa="planejando o que entra na thumbnail", inicio=time.strftime("%Y-%m-%d %H:%M:%S"))
        plano = ler_json(p / "plano_thumb.json")
        if not plano:
            plano = planejar(vd, c, m, obs)
            gravar_json(p / "plano_thumb.json", plano)
        do_motor = _plano_do_motor(vd, m, plano)
        gravar_json(p / "plano_thumb.json", plano)
        if do_motor:
            if ler_json(p / "plano.json") != do_motor:
                gravar_json(p / "plano.json", do_motor)
            n_novos = len(do_motor["itens"][0]["cenas"])
            _marcar(vd, etapa=f"buscando {n_novos} imagem(ns) que o vídeo não tinha")
            fila = _buscar(p, c)
            if fila:
                _marcar(vd, status="esperando_flow", etapa="",
                        aviso=f"{fila} desenho(s) da thumbnail esperando o Google Flow. Peça para uma sessão do "
                              "Claude gerar a fila do Flow e depois clique em Continuar: ela segue daqui.")
                return 2
            _marcar(vd, etapa="escolhendo as imagens")
            _escolher(p)
        man = {x["id"]: x for x in (ler_json(p / "manifesto.json", {}) or {}).get("assets", [])}
        n = int(m.get("itens") or 1)
        prontos, faltou = [], []
        for it in plano["itens"]:
            arq = it.get("imagem") or (str(p / man[it["asset"]]["arquivo"]) if it.get("asset") in man else "")
            if arq and Path(arq).is_file():
                prontos.append({**it, "imagem": arq})
            else:
                faltou.append(it["legenda"] or it["titulo"] or it.get("descricao", ""))
        if len(prontos) < n:
            raise ValueError(f"só achei a imagem certa de {len(prontos)} dos {n} itens deste modelo (faltou: "
                             + ", ".join(faltou)[:200] + "). Tente outro modelo ou faça de novo com uma observação.")
        _marcar(vd, etapa="desenhando")
        feita = _compor({"modelo": m, "estilo": estilo, "titulo": plano.get("titulo", ""), "itens": prontos[:n],
                         "saida": str(p / "thumbnail.png")}, p / "pedido_compor.json", c)
        capas.salvar_thumbnail(vd, feita.read_bytes(), f"thumbnail {m.get('nome', modelo_id).lower()}{feita.suffix}")
        from . import fichas
        info = ler_json(fichas.pasta(vd) / "thumbnail.json", {}) or {}
        info.update(modelo=modelo_id, modelo_nome=m.get("nome", modelo_id), feita_pelo_sistema=True, fundo=fundo)
        gravar_json(fichas.pasta(vd) / "thumbnail.json", info)
        # um dos primeiros ficou sem imagem e uma reserva entrou no lugar: avisa qual
        fora = [it["legenda"] or it["titulo"] for it in plano["itens"][:n]
                if not any(pr is not None and pr.get("legenda") == it["legenda"] and pr.get("titulo") == it["titulo"]
                           for pr in prontos[:n])]
        _guardar_fundo(c, fundo)
        _marcar(vd, status="ok", etapa="", fundo=fundo, fim=time.strftime("%Y-%m-%d %H:%M:%S"),
                aviso=("Ficou de fora, sem a imagem certa: " + ", ".join(fora)[:200]) if fora else "")
        return 0
    except (ValueError, SystemExit) as e:
        _marcar(vd, status="erro", etapa="", erro=str(e)[:500])
        return 1
    finally:
        (pasta(vd) / "pid").unlink(missing_ok=True)


def lancar(vd, modelo_id, refazer=False, obs="", fundo=""):
    """Lança o `thumb` solto do painel (como o Reels e o vídeo final): fechar o painel não para nada."""
    vd = Path(vd)
    pasta(vd).mkdir(exist_ok=True)
    cmd = [sys.executable, "-m", "space_machine", "thumb", str(vd), "--modelo", modelo_id]
    cmd += ["--refazer"] if refazer else []
    cmd += ["--obs", obs] if obs else []
    cmd += ["--fundo", fundo] if cor_valida(fundo) else []
    _marcar(vd, status="rodando", modelo=modelo_id, etapa="começando", erro="", aviso="")
    sh = subprocess.run(["/bin/sh", "-c", '"$@" </dev/null >>"$LOG_THUMB" 2>&1 & echo $!', "sh", *cmd],
                        cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True,
                        start_new_session=True,
                        env={**os.environ, "PYTHONUNBUFFERED": "1", "LOG_THUMB": str(pasta(vd) / "log.txt")})
    pid = sh.stdout.strip()
    (pasta(vd) / "pid").write_text(pid)
    return pid


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m space_machine thumb", description=__doc__.split("\n")[0])
    ap.add_argument("video", help="pasta do vídeo")
    ap.add_argument("--modelo", help="id do modelo (veja com --modelos)")
    ap.add_argument("--modelos", action="store_true", help="lista os modelos do formato do canal")
    ap.add_argument("--refazer", action="store_true", help="joga fora o plano e as imagens deste modelo e faz de novo")
    ap.add_argument("--obs", default="", help="um pedido seu para o plano (ex.: \"use só os times de Ohio\")")
    ap.add_argument("--fundo", default="", help="cor do fundo, #RRGGBB (sem ela, a última usada no canal ou a do formato)")
    a = ap.parse_args(argv)
    vd = Path(a.video).resolve()
    _, c = canal_do_bloco(vd / "thumb")
    if a.modelos or not a.modelo:
        for m in modelos(c):
            print(f"{m['id']:<16} {m['nome']} — {m['descricao']}")
        return
    cod = fazer(vd, a.modelo, a.refazer, a.obs, a.fundo)
    est = ler_estado(vd)
    print({0: f"OK → {capas.thumbnail(vd)}", 2: est.get("aviso", "")}.get(cod, "ERRO: " + est.get("erro", "")))
    if est.get("aviso") and cod == 0:
        print(est["aviso"])
    sys.exit(cod)
