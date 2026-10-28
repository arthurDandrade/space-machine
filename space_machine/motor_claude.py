"""Única porta de entrada do Space Machine para o Claude: `claude -p` enxuto, pela assinatura.

Cada chamada sai sem MCP, sem CLAUDE.md, sem memória e sem o system prompt padrão do Claude Code:
só o prompt da etapa (formatos/<formato>/prompts/*.md), os dados e as imagens (base64, sem turno extra de Read).
A resposta vem em JSON validado (--json-schema) e o consumo de cada chamada vai para <dados>/space_machine.sqlite.

Login: o `claude` do terminal precisa estar logado. Para rodar sem conversa (painel, launchd), gere um token
da assinatura com `claude setup-token` e grave no .env da pasta de dados (painel › APIs) a linha CLAUDE_CODE_OAUTH_TOKEN=...

Teste: python -m space_machine.motor_claude --teste [imagem.jpg]
"""
import base64
import io
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image

from . import plataforma
from .sistema import (DADOS, PACOTE, REPO as RAIZ, canais, config,  # noqa: F401  (usados por outros módulos)
                      config_canal)

BANCO = DADOS / "space_machine.sqlite"
ENV = DADOS / ".env"
# pasta neutra: sem CLAUDE.md em nenhum diretório acima (a pasta de dados fica fora do repo)
CWD = DADOS / "logs" / "claude"
PESOS = {"input_tokens": 1, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1, "output_tokens": 5}
_trava_banco = threading.Lock()


class ErroClaude(RuntimeError):
    pass


class LimiteDeUso(ErroClaude):
    """A assinatura bateu no limite: não adianta continuar chamando até o horário de reset."""


# etapa → regra do tema do canal (canal.json › regras) que vai junto no prompt
REGRA_DA_ETAPA = {"escolher_imagem": "escolha", "escolher_video": "escolha", "conferir_asset": "escolha",
                  "confirmar_trecho": "escolha", "storyboard": "storyboard", "qa": "storyboard"}


def arquivo_prompt(nome, formato=None):
    """formatos/<formato>/prompts/<nome>.md: o prompt de cada etapa é do FORMATO do vídeo."""
    from .sistema import arquivo_formato
    return arquivo_formato(f"prompts/{nome}.md", formato)


def prompt(nome, canal=None, formato=None):
    """Lê o prompt da etapa no formato do vídeo, sem o cabeçalho de comentário (linhas que começam com '<!--').
    Com o canal, acrescenta o tema e as regras do tema dele (o prompt da etapa é do FORMATO, igual para todos os
    canais dele). Sem o canal, diga o `formato` — senão vale o padrão."""
    if canal and not formato:
        formato = canal.get("formato")
    txt = arquivo_prompt(nome, formato).read_text()
    txt = "\n".join(l for l in txt.splitlines() if not l.startswith("<!--")).strip()
    if canal:
        cj = json.loads((Path(canal["raiz"]) / "canal.json").read_text())
        regra = cj.get("regras", {}).get(REGRA_DA_ETAPA.get(nome, ""), "")
        txt += f"\n\n# Canal: {cj.get('nome', '')}" + (f" — tema: {cj['tema']}" if cj.get("tema") else "")
        if isinstance(regra, list):
            regra = "\n".join(f"- {r}" for r in regra)
        if regra:
            txt += "\nRegras do tema deste canal (valem tanto quanto as de cima):\n" + regra
    return txt


# etapas do `rodar` que chamam o Claude → chaves de ["modelos"] (canal.json do canal) que elas usam
MODELOS_DA_ETAPA = {"storyboard": ["storyboard"],
                    "escolher": ["escolher_imagem", "escolher_video", "confirmar_trecho", "conferir"],
                    "editar": ["qa"]}
CHECAGEM = DADOS / "claude_checagem.json"
CHECAGEM_VALE_S = 15 * 60


def eh_limite(msg):
    """A assinatura bateu no limite? O texto muda com a versão do claude: "usage limit", "out of … usage",
    "You've hit your session limit · resets 1:40am" (este passou batido em 2026-10-12 e a fila queimou 15 blocos)."""
    m = str(msg).lower()
    return ("usage limit" in m or ("out of" in m and "usage" in m) or ("hit your" in m and "limit" in m)
            or "session limit" in m or "weekly limit" in m or "rate limit" in m or "limite de uso" in m)


def _versao_claude():
    try:
        r = subprocess.run([plataforma.claude(), "--version"], capture_output=True, text=True, env=_env(), timeout=30)
        return (r.stdout or r.stderr).strip().split(" ")[0] or "?"
    except FileNotFoundError:
        return None


def _ping(modelo):
    """Chamada mínima (sem raciocínio, sem ferramentas). Devolve None se respondeu, ou o texto do erro."""
    cmd = [plataforma.claude(), "-p", "--model", modelo, "--system-prompt", "Responda só: ok", "--strict-mcp-config",
           "--tools", "", "--setting-sources", "", "--no-session-persistence", "--output-format", "json", "ok"]
    env = _env()
    env["MAX_THINKING_TOKENS"] = "0"
    CWD.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=CWD, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        return "o claude não respondeu em 120 s"
    try:
        d = json.loads(r.stdout)
        if not d.get("is_error") and r.returncode == 0:
            return None
        return str(d.get("result") or r.stderr).strip()[:400]
    except json.JSONDecodeError:
        return (r.stderr or r.stdout).strip()[-400:] or f"saiu com código {r.returncode}"


def checar_claude(etapas, atualizar=True, canal=None):
    """Antes de rodar: o `claude` existe, está logado e aceita os modelos das etapas pedidas?

    Os modelos são os DESTE canal; sem canal (teste do painel, fila esperando o limite passar), testa os de
    todos os canais. Uma chamada mínima por modelo (resultado guardado por 15 min em dados/claude_checagem.json).
    Se o claude estiver velho demais para o modelo, roda `claude update` uma vez e testa de novo.
    Falha → ErroClaude (ou LimiteDeUso) com o que você precisa fazer.
    """
    cfgs = [config_canal(canal)] if canal else [config_canal(c) for c in canais().values()] or [config()]
    precisa = {}
    for cfg in cfgs:
        for etapa in etapas:
            for chave in MODELOS_DA_ETAPA.get(etapa, []):
                if chave in cfg["modelos"]:
                    precisa.setdefault(cfg["modelos"][chave], chave)
    if not precisa:
        return
    versao = _versao_claude()
    if versao is None:
        raise ErroClaude("o comando `claude` não foi encontrado. "
                         "Instale de novo: npm install -g @anthropic-ai/claude-code")
    try:
        cache = json.loads(CHECAGEM.read_text())
    except (OSError, json.JSONDecodeError):
        cache = {}
    agora = time.time()
    tem_token = "CLAUDE_CODE_OAUTH_TOKEN" in _env()
    for modelo, chave in precisa.items():
        if cache.get(f"{versao}|{modelo}", 0) > agora - CHECAGEM_VALE_S:
            continue
        erro = _ping(modelo)
        if erro and atualizar and ("newer is required" in erro or "claude update" in erro):
            print(f"[checagem] claude {versao} não aceita {modelo}: rodando `claude update`...", flush=True)
            subprocess.run([plataforma.claude(), "update"], capture_output=True, text=True, env=_env(), timeout=600)
            nova = _versao_claude()
            if nova and nova != versao:
                print(f"[checagem] claude atualizado: {versao} → {nova}", flush=True)
                versao = nova
                erro = _ping(modelo)
        if erro:
            baixo = erro.lower()
            if "newer is required" in baixo or "claude update" in baixo:
                raise ErroClaude(f"o claude do terminal (versão {versao}) é velho demais para o modelo {modelo} "
                                 f"e a atualização automática não resolveu. Rode `claude update` no Terminal. "
                                 f"({erro})")
            if any(s in baixo for s in ("authenticat", "oauth", "login", "401", "api key", "token")):
                if tem_token:
                    raise ErroClaude("o token da assinatura (CLAUDE_CODE_OAUTH_TOKEN em Estudio/.env) não vale "
                                     "mais. Gere outro com `claude setup-token` no Terminal e cole na página APIs "
                                     f"do painel. ({erro})")
                raise ErroClaude(f"o claude não está logado. Rode `claude /login` no Terminal. ({erro})")
            if eh_limite(baixo):
                raise LimiteDeUso(f"checagem: {erro}")
            if "model" in baixo and any(s in baixo for s in ("not found", "invalid", "not exist", "unknown")):
                raise ErroClaude(f"o modelo {modelo} (usado em {chave}) não existe para este claude. "
                                 f"Troque em Modelos do Claude, no canal, no painel. ({erro})")
            raise ErroClaude(f"o claude não respondeu ao teste com {modelo} (usado em {chave}): {erro}")
        cache[f"{versao}|{modelo}"] = agora
        DADOS.mkdir(parents=True, exist_ok=True)
        CHECAGEM.write_text(json.dumps(cache, indent=1))


def _env(etapa=None):
    """Ambiente limpo: o claude filho não herda proxy/sessão de quem chamou (ex.: o app desktop)."""
    env = {k: os.environ[k] for k in plataforma.VARIAVEIS_BASE if k in os.environ}
    env["PATH"] = plataforma.CAMINHO_SISTEMA
    # esforço low = sem raciocínio (MAX_THINKING_TOKENS=0): é o que deixa as escolhas baratas (saída de ~170
    # tokens em vez de 1,5–8,7 mil). De medium para cima, o Claude raciocina o quanto quiser.
    if etapa and config().get("esforco", {}).get(etapa, "low") == "low":
        env["MAX_THINKING_TOKENS"] = "0"
    if ENV.exists():
        for linha in ENV.read_text().splitlines():
            k, _, v = linha.partition("=")
            if k.strip() and not k.strip().startswith("#"):
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def imagem_b64(caminho, lado_max=None):
    """JPEG reduzido ao tamanho que a API usa de verdade (o resto seria jogado fora lá)."""
    lado_max = lado_max or config()["imagem_lado_max"]
    im = Image.open(caminho)
    im = im.convert("RGB")
    im.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _banco():
    DADOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(BANCO, timeout=30)
    con.execute("""create table if not exists chamadas (
        id integer primary key, quando text, canal text, video text, bloco text, etapa text, asset text,
        modelo text, entrada int, cache_escrita int, cache_leitura int, saida int, equivalente int,
        custo_usd real, duracao_ms int, ok int, erro text)""")
    return con


def registrar(ctx, etapa, modelo, uso, custo, duracao_ms, ok, erro=None):
    eq = int(sum((uso.get(k) or 0) * p for k, p in PESOS.items()))
    with _trava_banco:
        con = _banco()
        con.execute("insert into chamadas (quando, canal, video, bloco, etapa, asset, modelo, entrada, cache_escrita,"
                    " cache_leitura, saida, equivalente, custo_usd, duracao_ms, ok, erro)"
                    " values (datetime('now','localtime'),?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ctx.get("canal"), ctx.get("video"), ctx.get("bloco"), etapa, ctx.get("asset"), modelo,
                     uso.get("input_tokens"), uso.get("cache_creation_input_tokens"),
                     uso.get("cache_read_input_tokens"), uso.get("output_tokens"), eq, custo, duracao_ms,
                     int(ok), erro))
        con.commit()
        con.close()
    return eq


def _extrair_json(texto):
    texto = (texto or "").strip()
    if texto.startswith("```"):
        texto = texto.strip("`").removeprefix("json").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        ini, fim = texto.find("{"), texto.rfind("}")
        if ini >= 0 and fim > ini:
            return json.loads(texto[ini:fim + 1])
        raise


def chamar(etapa, sistema, texto, imagens=(), schema=None, modelo=None, ctx=None, timeout=None, sessao=None,
           texto_livre=False, canal=None):
    """Uma chamada isolada ao Claude. imagens: caminhos (ou (rotulo, caminho)). Devolve o JSON da resposta.

    canal: de quem saem o modelo e o esforço desta etapa (canal.json › modelos/esforco). Sem canal, valem os
    padrões do config_padrao.json. `modelo` força um modelo (ex.: --modelo na linha de comando).
    ctx: {canal, video, bloco, asset} só para o registro de consumo.
    sessao: (uuid, nova?) — conversa curta de uma etapa (ex.: voltas de correção do storyboard). A 1ª chamada
    cria a sessão com esse id; as seguintes retomam (--resume) e o prompt de sistema vem do cache.
    texto_livre: devolve {"texto": ...} sem exigir JSON (respostas grandes, como o cenas.json inteiro).
    """
    cfg = config_canal(canal) if canal else config()
    modelo = modelo or cfg["modelos"].get(etapa, "sonnet")
    ctx = ctx or {}
    conteudo = []
    for img in imagens:
        rotulo, caminho = img if isinstance(img, tuple) else (None, img)
        if rotulo:
            conteudo.append({"type": "text", "text": rotulo})
        conteudo.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                     "data": imagem_b64(caminho)}})
    conteudo.append({"type": "text", "text": texto})
    msg = json.dumps({"type": "user", "message": {"role": "user", "content": conteudo}})

    CWD.mkdir(parents=True, exist_ok=True)
    nome = "_".join(str(x) for x in ("ultima", etapa, ctx.get("video"), ctx.get("bloco"), ctx.get("asset")) if x)
    if plataforma.WINDOWS:
        # a linha de comando do Windows para em 32 mil caracteres e o prompt do storyboard passa disso: vai por arquivo
        arq_sistema = CWD / f"{nome}.sistema.md"
        arq_sistema.write_text(sistema, encoding="utf-8")
        opcao_sistema = ["--system-prompt-file", str(arq_sistema)]
    else:
        opcao_sistema = ["--system-prompt", sistema]
    cmd = [plataforma.claude(), "-p", "--model", modelo, *opcao_sistema,
           "--strict-mcp-config", "--tools", "", "--setting-sources", "",
           "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
    if sessao:
        sid, nova = sessao
        cmd += ["--session-id", sid] if nova else ["--resume", sid]
    else:
        cmd += ["--no-session-persistence"]
    esforco = cfg.get("esforco", {}).get(etapa)
    if esforco:
        cmd += ["--effort", esforco]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    t0 = time.time()
    try:
        # a saída vai para um arquivo enquanto chega (dados/claude_cwd/ultima_<etapa>.jsonl): dá para
        # acompanhar uma chamada longa (storyboard) e ver onde ela parou se estourar o tempo
        # um arquivo por chamada (chamadas paralelas da mesma etapa corrompiam um arquivo comum)
        # com vídeo e bloco no nome: dois blocos no storyboard/QA ao mesmo tempo escreviam no mesmo arquivo
        # e um podia ler a resposta do outro (2026-10-11)
        andamento, arq_erro = CWD / f"{nome}.jsonl", CWD / f"{nome}.err"
        with open(andamento, "w") as saida, open(arq_erro, "w") as erro:
            proc = subprocess.run(cmd, input=msg + "\n", stdout=saida, stderr=erro, text=True, cwd=CWD,
                                  env=_env(etapa), timeout=timeout or cfg["claude_timeout_s"])
        r = subprocess.CompletedProcess(cmd, proc.returncode, andamento.read_text(errors="replace"),
                                        arq_erro.read_text(errors="replace"))
    except subprocess.TimeoutExpired:
        registrar(ctx, etapa, modelo, {}, 0, int((time.time() - t0) * 1000), False, "timeout")
        raise ErroClaude(f"{etapa}: o claude não respondeu em {timeout or cfg['claude_timeout_s']} s")

    final = None
    for linha in r.stdout.splitlines():
        try:
            d = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if d.get("type") == "result":
            final = d
    if not final:
        erro = (r.stderr or r.stdout).strip()[-500:]
        registrar(ctx, etapa, modelo, {}, 0, int((time.time() - t0) * 1000), False, erro)
        raise ErroClaude(f"{etapa}: sem resposta do claude ({erro})")

    uso, custo, dur = final.get("usage") or {}, final.get("total_cost_usd") or 0, final.get("duration_ms") or 0
    if final.get("is_error"):
        registrar(ctx, etapa, modelo, uso, custo, dur, False, str(final.get("result"))[:500])
        msg = str(final.get("result"))
        if eh_limite(msg):
            # a checagem guardada (15 min) diria "ok" e a fila acharia que o limite já liberou (2026-10-13)
            CHECAGEM.unlink(missing_ok=True)
            raise LimiteDeUso(f"{etapa}: {msg}")
        raise ErroClaude(f"{etapa}: {msg}")
    resposta = final.get("structured_output")
    if texto_livre:
        resposta = {"texto": final.get("result") or ""}
    if resposta is None:
        try:
            resposta = _extrair_json(final.get("result"))
        except (json.JSONDecodeError, TypeError):
            registrar(ctx, etapa, modelo, uso, custo, dur, False, "resposta sem JSON")
            raise ErroClaude(f"{etapa}: resposta sem JSON: {str(final.get('result'))[:300]}")
    eq = registrar(ctx, etapa, modelo, uso, custo, dur, True)
    # deu certo: o andamento não serve mais (eram ~1.300 arquivos em claude_cwd); os das falhas ficam
    andamento.unlink(missing_ok=True)
    arq_erro.unlink(missing_ok=True)
    resposta = dict(resposta) if isinstance(resposta, dict) else {"valor": resposta}
    resposta["_uso"] = {"equivalente": eq, "custo_usd": custo, "modelo": modelo, "duracao_ms": dur}
    return resposta


def consumo(**filtros):
    """Soma do consumo registrado (filtros: canal, video, bloco, etapa)."""
    con = _banco()
    onde = " and ".join(f"{k} = ?" for k in filtros) or "1=1"
    lin = con.execute(f"select count(*), sum(equivalente), sum(custo_usd), sum(ok) from chamadas where {onde}",
                      tuple(filtros.values())).fetchone()
    con.close()
    return {"chamadas": lin[0], "equivalente": lin[1] or 0, "custo_usd": lin[2] or 0, "ok": lin[3] or 0}


if __name__ == "__main__":
    if "--teste" in sys.argv:
        imgs = [a for a in sys.argv[1:] if not a.startswith("--")]
        schema = {"type": "object", "properties": {"resposta": {"type": "string"}}, "required": ["resposta"]}
        texto = "Descreva a imagem em até 8 palavras." if imgs else "Responda: ok"
        r = chamar("teste", "Você responde só o JSON pedido.", texto, imagens=imgs, schema=schema,
                   modelo="haiku", ctx={"canal": "teste"})
        print(json.dumps(r, ensure_ascii=False, indent=1))
