"""Trocar o formato de um canal e o prompt de roteiro dele.

Trocar o formato (canal.json › formato) muda de uma vez o motor inteiro dos PRÓXIMOS vídeos: prompts das etapas,
biblioteca de cenas, gerador, QA. O que já existe no canal foi feito para o formato de antes e não se converte
sozinho, então a troca passa por aqui:

  conferir(slug, novo)   o que a troca encontra, sem mexer em nada: o que IMPEDE (algo rodando, vídeo no meio da
                         produção — o storyboard pronto seria montado pelo gerador do outro formato) e o que ela
                         FAZ ou você precisa saber (vídeos só com roteiro são redivididos, prompt de roteiro, regras
                         do tema, chaves que o formato novo pede).
  trocar(slug, novo)     grava o formato, redivide os vídeos ainda não começados no jeito do formato novo (os blocos
                         de antes vão para o Lixo do Mac) e põe de lado o prompt de roteiro do formato antigo.

Prompt de roteiro: sem arquivo próprio, o canal usa o do formato (formato.json › roteiro.modelo), sempre o atual
do repo. Alterado em canal › Prompt de roteiro, vira <canal>/prompts/Roteiro do vídeo.md e passa a valer no lugar.
"""
import json
from pathlib import Path

from . import estado, gestao, meus_prompts, prontos
from .configuracao import ler_env, salvar_canal
from .sistema import CANAIS, FORMATO_PADRAO, canais, ficha_formato, formatos, ler_json

# fonte de imagem do formato → o que ela pede de quem usa
FONTES_COM_CHAVE = {"gemini": "GEMINI_API_KEY"}


# ---------------- prompt de roteiro ----------------
def _arquivo_prompt(slug):
    return meus_prompts.pasta(slug, criar=False) / gestao.PROMPT_ROTEIRO


def prompt_roteiro(slug):
    """O prompt de roteiro que vale para o canal agora, de onde ele vem ("canal" = você alterou, "formato" = o que
    o formato traz, "nenhum") e o do formato, para comparar ou voltar a ele."""
    c = canais()[slug]
    padrao = gestao.modelo_roteiro_do_formato(c.get("formato")) or ""
    arq = _arquivo_prompt(slug)
    proprio = arq.read_text(errors="replace") if arq.is_file() else ""
    seu = bool(proprio.strip()) and proprio.strip() != padrao.strip()
    texto = proprio if seu else padrao
    return {"texto": texto, "origem": "canal" if seu else "formato" if padrao else "nenhum", "padrao": padrao,
            "escreve": bool(padrao), "formato": c.get("formato") or FORMATO_PADRAO,
            "formato_nome": ficha_formato(c.get("formato")).get("nome", c.get("formato") or FORMATO_PADRAO),
            "palavras": len(texto.split()), "mudou": arq.stat().st_mtime if seu else None}


def salvar_prompt_roteiro(slug, texto):
    """Guarda o seu prompt de roteiro. Igual ao do formato (ou vazio) = volta a valer o do formato."""
    atual = prompt_roteiro(slug)
    if not texto.strip() or texto.strip() == atual["padrao"].strip():
        voltar_ao_do_formato(slug)
    else:
        arq = _arquivo_prompt(slug)
        meus_prompts.salvar(slug, Path(gestao.PROMPT_ROTEIRO).stem, texto, arq.name if arq.is_file() else "")
    return prompt_roteiro(slug)


def voltar_ao_do_formato(slug):
    """O seu prompt de roteiro sai de uso (vai para prompts/_lixeira/) e volta a valer o do formato."""
    if _arquivo_prompt(slug).is_file():
        meus_prompts.apagar(slug, gestao.PROMPT_ROTEIRO)
        return True
    return False


# ---------------- trocar o formato ----------------
def _situacao(slug, vd):
    """Onde o vídeo está para efeito da troca: "arquivado", "pronto", "roteiro" (nada produzido) ou "producao"."""
    v = estado.video(slug, vd.name)
    if v["arquivado"]:
        return "arquivado"
    prod = v.get("producao")
    if prontos.atual(vd) or (prod and prod["feito"]["entregar"]) or (not prod and v["n_blocos"] and v["entregues"] == v["n_blocos"]):
        return "pronto"
    ignora = {"roteiro.txt", ".DS_Store"}
    mexido = any(f.name not in ignora for b in (vd / "blocos").glob("*") if b.is_dir() for f in b.iterdir())
    mexido = mexido or ((vd / "producao").is_dir() and any((vd / "producao").iterdir()))
    mexido = mexido or any((vd / "edicao").glob("*.mp4"))
    return "producao" if mexido else "roteiro"


def _usa(ficha, fonte):
    return f'"{fonte}' in json.dumps(ficha)


def conferir(slug, novo):
    """O que a troca para o formato `novo` encontra neste canal. Não muda nada."""
    c = canais()[slug]
    atual = c.get("formato") or FORMATO_PADRAO
    if novo not in formatos():
        raise ValueError(f"não existe o formato \"{novo}\"")
    if novo == atual:
        raise ValueError("o canal já está neste formato")
    fa, fn = ficha_formato(atual), ficha_formato(novo)
    grupos = {"arquivado": [], "pronto": [], "roteiro": [], "producao": []}
    rodando = False
    prod = Path(c["producoes"])
    for vd in sorted(prod.iterdir()) if prod.is_dir() else []:
        if not vd.is_dir() or vd.name.startswith((".", "_")):
            continue
        rodando = rodando or bool(gestao._ocupado(vd))
        grupos[_situacao(slug, vd)].append({"slug": vd.name, "titulo": estado.titulo_video(vd),
                                            "tem_roteiro": (vd / "roteiro_completo.txt").is_file()})
    bloqueios = []
    if rodando:
        bloqueios.append("rodando")
    if grupos["producao"]:
        bloqueios.append("producao")
    p = prompt_roteiro(slug)
    env = ler_env(CANAIS / slug / ".env")
    cj = ler_json(CANAIS / slug / "canal.json", {}) or {}
    regras = cj.get("regras") or {}
    return {
        "de": atual, "de_nome": fa.get("nome", atual), "para": novo, "para_nome": fn.get("nome", novo),
        "bloqueios": bloqueios, "em_producao": grupos["producao"],
        "redividir": [v for v in grupos["roteiro"] if v["tem_roteiro"]],
        "sem_roteiro": [v for v in grupos["roteiro"] if not v["tem_roteiro"]],
        "prontos": len(grupos["pronto"]), "arquivados": len(grupos["arquivado"]),
        "prompt": p["origem"],                                         # "canal": você tem um prompt de roteiro seu
        "escreve_roteiro": bool(gestao.modelo_roteiro_do_formato(novo)),
        "regras": len(regras.get("storyboard") or []) + len(regras.get("escolha") or []),
        "chaves_faltando": [chave for fonte, chave in FONTES_COM_CHAVE.items() if _usa(fn, fonte) and not env.get(chave)],
        "usa_flow": _usa(fn, "flow") and not _usa(fa, "flow"),
        "perde_fundo": bool((fa.get("identidade") or {}).get("fundo_imagem")) and not (fn.get("identidade") or {}).get("fundo_imagem"),
    }


def redividir(c, vd):
    """Vídeo que ainda só tem roteiro: os blocos são refeitos a partir do roteiro_completo.txt no jeito do formato
    do canal (os de antes vão para o Lixo do Mac) e o fluxo do vídeo passa a ser o do formato."""
    from . import limpeza
    cold_open, partes = gestao.dividir_roteiro((vd / "roteiro_completo.txt").read_text())
    if not partes:
        return False
    if (vd / "blocos").is_dir():
        limpeza.mandar_para_o_lixo([(vd / "blocos", "formato")])
    gestao.escrever_blocos(c, vd, cold_open, partes)
    return True


def trocar(slug, novo, manter_prompt=False):
    """Troca o formato do canal. ValueError com o motivo se a conferência achou algo que impede."""
    conf = conferir(slug, novo)
    if "rodando" in conf["bloqueios"]:
        raise ValueError("tem produção rodando neste canal: espere terminar ou pare antes de trocar o formato")
    if "producao" in conf["bloqueios"]:
        raise ValueError("há vídeo no meio da produção: termine, arquive ou exclua antes de trocar o formato ("
                         + ", ".join(v["titulo"] for v in conf["em_producao"]) + ")")
    prompt_saiu = False
    if conf["prompt"] != "canal" or not manter_prompt:
        # a cópia do prompt do formato antigo (canais criados antes) ou o seu, escrito para o molde antigo
        prompt_saiu = voltar_ao_do_formato(slug) and conf["prompt"] == "canal"
    salvar_canal(slug, formato=novo)
    c = canais()[slug]
    refeitos = [v["titulo"] for v in conf["redividir"] if redividir(c, Path(c["producoes"]) / v["slug"])]
    return {**conf, "redivididos": refeitos, "prompt_saiu": prompt_saiu}
