"""O que é do Space Machine inteiro, fora de um canal: consumo, primeiros passos, limpeza, atualização,
formatos, canal novo e as chaves que valem para todos.
"""
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile

from .. import atualizar, configuracao, estado, fichas, limpeza, primeiros_passos, textos
from ..motor_claude import _banco, canais
from ..sistema import DADOS, FORMATO_PADRAO, REPO, config, formatos
from .comum import IMAGENS, _cache_falta, _consumo_7d

api = APIRouter(prefix="/api")


# ---------------- configurações do produtor ----------------
@api.get("/consumo")
def consumo():
    con = _banco()
    por_etapa = con.execute("""select etapa, count(*), sum(equivalente),
                               sum(equivalente)*1.0/count(distinct coalesce(asset, bloco || etapa))
                               from chamadas where ok=1 and canal != 'teste' group by etapa order by 3 desc""").fetchall()
    por_video = con.execute("""select canal, video, count(*), sum(equivalente), max(quando) from chamadas
                               where canal != 'teste' group by 1, 2 order by 5 desc""").fetchall()
    linhas = con.execute("""select canal, video, bloco, etapa, modelo, count(*), sum(equivalente),
                            sum(case when ok=0 then 1 else 0 end), max(quando)
                            from chamadas where canal != 'teste' group by 1,2,3,4,5 order by max(quando) desc
                            limit 300""").fetchall()
    con.close()
    nomes = {s: c["nome"] for s, c in canais().items()}
    titulos = {}

    def titulo(canal, video):
        """O título do vídeo (se ele ainda existe); senão, a pasta dele como estava."""
        if not video:
            return ""
        if (canal, video) not in titulos:
            c = canais().get(canal)
            vd = Path(c["producoes"]) / video if c else None
            existe = vd and (vd.is_dir() or fichas.existe(vd))
            # vídeo que não existe mais (excluído ou de um canal apagado): a pasta dele, em palavras
            titulos[canal, video] = estado.titulo_video(vd) if existe else f"{video.replace('-', ' ').capitalize()} (excluído)"
        return titulos[canal, video]
    return {"total_7d": _consumo_7d()["total"],
            "por_etapa": [{"etapa": e, "chamadas": n, "tokens": t or 0, "media": round(m or 0)} for e, n, t, m in por_etapa],
            "por_video": [{"canal": nomes.get(c, c), "video": titulo(c, v), "chamadas": n, "tokens": t or 0, "ultima": q}
                          for c, v, n, t, q in por_video],
            "linhas": [{"canal": nomes.get(c, c), "video": titulo(c, v), "bloco": b or "", "etapa": e, "modelo": m,
                        "chamadas": n, "tokens": t or 0, "falhas": f or 0, "ultima": q}
                       for c, v, b, e, m, n, t, f, q in linhas]}


@api.get("/primeiros-passos")
def primeiros_passos_lista():
    itens = primeiros_passos.checar()
    _cache_falta.update(quando=time.time(), falta=any(not i["ok"] for i in itens))
    return {"itens": itens, "after_app": config().get("after_app", "")}


@api.post("/primeiros-passos/after")
def salvar_after(after_app: str = Body(..., embed=True)):
    """O nome do app do After Effects muda a cada versão anual; é da máquina, vale para todos os canais."""
    try:
        configuracao.salvar_after_app(after_app)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "after_app": config().get("after_app", "")}


@api.post("/primeiros-passos/testar-claude")
def testar_claude():
    from ..motor_claude import CHECAGEM, ErroClaude, MODELOS_DA_ETAPA, checar_claude
    CHECAGEM.unlink(missing_ok=True)
    try:
        checar_claude(list(MODELOS_DA_ETAPA))
    except ErroClaude as e:
        return {"ok": False, "mensagem": str(e)[:500]}
    return {"ok": True, "mensagem": textos.t("pp.claude_ok", config().get("idioma_painel", "pt"))}


@api.get("/limpeza")
def levantar_limpeza():
    """O que sairia na limpeza (nada é movido aqui), o espaço no disco e se a limpeza automática está ligada."""
    r = limpeza.levantar(cache=True)
    disco = shutil.disk_usage(DADOS)
    return {**r, "rotulos": limpeza.CATEGORIAS, "automatica": bool(config().get("limpeza_automatica", True)),
            "disco": {"livre": disco.free, "total": disco.total}}


@api.post("/limpeza")
def aplicar_limpeza(categorias: list = Body(..., embed=True)):
    cats = [c for c in categorias if c in limpeza.CATEGORIAS]
    if not cats:
        raise HTTPException(400, "Escolha o que limpar.")
    total, itens, pasta = limpeza.limpar(categorias=cats, cache="cache" in cats)
    no_lixo = str(pasta).startswith(str(Path.home() / ".Trash"))
    return {"ok": True, "bytes": total, "itens": itens, "pasta": pasta.name, "no_lixo_do_mac": no_lixo,
            "caminho": "" if no_lixo else str(pasta)}


@api.post("/limpeza/automatica")
def limpeza_automatica(ligada: bool = Body(..., embed=True)):
    from ..sistema import salvar_config
    salvar_config({"limpeza_automatica": bool(ligada)})
    return {"ok": True}


@api.post("/limpeza/abrir-lixo")
def abrir_lixo():
    subprocess.run(["open", str(Path.home() / ".Trash")], check=False)
    return {"ok": True}


# ---------------- atualizar o Space Machine ----------------
@api.get("/atualizacao")
def ver_atualizacao(conferir: bool = False):
    """Sua versão, o que tem de novo no GitHub e, se não der para atualizar agora, por quê.
    Sem conferir=1 responde com a última conferida (vale 6 h), sem ir à rede."""
    r = atualizar.conferir(forcar=conferir)
    motivo, detalhe = atualizar.impedimento()
    return {"local": atualizar.estado_local(), "atrasado": r.get("atrasado", 0), "commits": r.get("commits", []),
            "quando": r.get("quando", 0), "erro": r.get("erro", ""), "erro_detalhe": r.get("detalhe", ""),
            "impedimento": motivo, "detalhe": detalhe}


@api.post("/atualizacao")
def aplicar_atualizacao():
    """git pull e o que mais ficou para trás (Python, painel). Depois o painel se reinicia no código novo."""
    r = atualizar.aplicar()
    if r.get("reiniciar"):
        atualizar.reiniciar_painel(espera=1.5)   # depois desta resposta sair: o navegador espera e recarrega
    return {**r, "local": atualizar.estado_local()}


@api.post("/atualizacao/reiniciar")
def reiniciar_painel(repo: str = Body("", embed=True)):
    """Reinicia o painel no código que está em disco (quem atualizou pela linha de comando chama isto).
    Com repo, só reinicia se for o painel daquela instalação: outra pasta na mesma porta não é reiniciada."""
    if repo and Path(repo).resolve() != REPO.resolve():
        raise HTTPException(409, "este painel é de outra instalação")
    atualizar.reiniciar_painel(espera=1.0)
    return {"ok": True}


@api.get("/fontes")
def lista_fontes():
    return {"fontes": [{"arquivo": f, "nome": Path(f).stem} for f in configuracao.fontes()]}


@api.get("/formatos")
def lista_formatos():
    """Os formatos de vídeo do repo (formatos/<nome>/formato.json), para escolher o do canal."""
    return {"formatos": [{"slug": s, **f} for s, f in formatos().items()], "padrao": FORMATO_PADRAO}


@api.post("/canais/novo")
async def novo_canal(nome: str = Form(...), tema: str = Form(...), idioma: str = Form("en"),
                     formato: str = Form(""),
                     cor_fundo: str = Form(...), cor_texto: str = Form(...), cor_destaque: str = Form(...),
                     cor_caixa: str = Form(...), cor_sombra: str = Form(...), fonte: str = Form(...),
                     logo: UploadFile = File(None), fundo: UploadFile = File(None), banner: UploadFile = File(None)):
    cores = {"fundo": cor_fundo, "texto": cor_texto, "destaque": cor_destaque, "caixa": cor_caixa, "sombra": cor_sombra}
    if not nome.strip() or not tema.strip():
        raise HTTPException(400, "Dê um nome e um tema ao canal.")
    if not all(configuracao.COR.fullmatch(v) for v in cores.values()) or fonte not in configuracao.fontes():
        raise HTTPException(400, "Escolha as cores (#RRGGBB) e a fonte dos títulos.")
    DADOS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=DADOS) as tmp:
        arqs = {}
        for campo, up in (("logo", logo), ("fundo", fundo), ("banner", banner)):
            if up is not None and up.filename:
                ext = Path(up.filename).suffix.lower()
                if ext not in IMAGENS:
                    raise HTTPException(400, f"{campo}: envie PNG, JPG ou WEBP.")
                arqs[campo] = Path(tmp) / f"{campo}{ext}"
                arqs[campo].write_bytes(await up.read())
        try:
            slug, pasta = configuracao.criar_canal(nome.strip(), tema.strip(), idioma.strip() or "en", cores, fonte,
                                                   logo=arqs.get("logo"), fundo=arqs.get("fundo"),
                                                   formato=formato.strip() or None)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if arqs.get("banner"):
            shutil.copy2(arqs["banner"], Path(pasta) / "identidade" / arqs["banner"].name)
    _cache_falta["quando"] = 0
    return {"ok": True, "slug": slug}


@api.post("/config/chaves/{api_id}")
def salvar_chave_sistema(api_id: str, valor: str = Body("", embed=True)):
    """Chave que vale para todos os canais (hoje: Claude e YouTube), para não ter de entrar num canal só por isso."""
    try:
        mostrar = configuracao.salvar_chave_sistema(api_id, valor)
    except ValueError as e:
        raise HTTPException(404, str(e))
    _cache_falta["quando"] = 0
    return {"ok": True, "mostrar": mostrar}
