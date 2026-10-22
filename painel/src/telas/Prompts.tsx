// Prompts do canal (ex.: o de fazer roteiros): arquivos .md na pasta do canal. Lista à esquerda, editor à direita
// (editar / visualizar), copiar o prompt inteiro, importar .md que você já tem (clicando ou arrastando), baixar e
// apagar (vai para prompts/_lixeira/). ⌘S salva.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Download, Eye, FileText, FolderOpen, PenLine, Plus, Save, Search, Trash2, Upload } from "lucide-react";
import { enviar, pegar } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { copiarTexto } from "../componentes/Copiar";
import { Markdown } from "../componentes/Markdown";
import { haQuanto, useT } from "../textos";

type Resumo = { nome: string; titulo: string; palavras: number; mudou: number; previa: string };
type Prompt = Resumo & { texto: string };
const NOVO = "__novo__";

function useImportar(canal: string, depois: (nomes: string[]) => void) {
  const qc = useQueryClient();
  const [erro, setErro] = useState("");
  const importar = useCallback(async (arquivos: File[]) => {
    setErro("");
    const md = arquivos.filter((f) => /\.(md|markdown|txt)$/i.test(f.name));
    if (!md.length) return setErro("Envie arquivos .md ou .txt.");
    const corpo = new FormData();
    md.forEach((f) => corpo.append("arquivos", f, f.name));
    const r = await fetch(`/api/c/${canal}/prompts-importar`, { method: "POST", body: corpo });
    const j = await r.json().catch(() => ({}));
    if (j.erros?.length) setErro(j.erros.join(" · "));
    qc.invalidateQueries({ queryKey: ["prompts", canal] });
    if (j.importados?.length) depois(j.importados);
  }, [canal, qc, depois]);
  return { importar, erro };
}

function Editor({ canal, nome, aoSalvar, aoApagar, setSujo }: {
  canal: string; nome: string; aoSalvar: (nome: string) => void; aoApagar: () => void; setSujo: (s: boolean) => void;
}) {
  const t = useT();
  const qc = useQueryClient();
  const novo = nome === NOVO;
  const { data } = useQuery({
    queryKey: ["prompt", canal, nome], enabled: !novo, refetchInterval: false,
    queryFn: () => pegar<Prompt>(`/api/c/${canal}/prompts/${encodeURIComponent(nome)}`),
  });
  const [titulo, setTitulo] = useState("");
  const [texto, setTexto] = useState("");
  const [modo, setModo] = useState<"editar" | "ver">(novo ? "editar" : "ver");
  const [copiado, setCopiado] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const base = useRef({ titulo: "", texto: "" });
  // preenche quando abre outro prompt (e não a cada atualização ao vivo: não apaga o que você está escrevendo)
  const carregado = useRef("");
  useEffect(() => {
    if (novo && carregado.current !== NOVO) {
      carregado.current = NOVO; base.current = { titulo: "", texto: "" }; setTitulo(""); setTexto(""); setModo("editar");
    } else if (data && carregado.current !== nome) {
      carregado.current = nome; base.current = { titulo: data.titulo, texto: data.texto };
      setTitulo(data.titulo); setTexto(data.texto); setModo("ver");
    }
  }, [data, nome, novo]);
  const sujo = titulo !== base.current.titulo || texto !== base.current.texto;
  useEffect(() => setSujo(sujo), [sujo, setSujo]);

  const salvar = useMutation({
    mutationFn: () => enviar<{ ok: boolean; nome: string }>(`/api/c/${canal}/prompts`, { titulo, texto, nome_antigo: novo ? "" : nome }),
    onSuccess: (r) => {
      base.current = { titulo, texto };
      carregado.current = r.nome;
      setSujo(false);
      qc.invalidateQueries({ queryKey: ["prompts", canal] });
      qc.setQueryData(["prompt", canal, r.nome], { ...(data ?? {}), nome: r.nome, titulo, texto });
      aoSalvar(r.nome);
    },
  });
  const apagar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/prompts/${encodeURIComponent(nome)}/apagar`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["prompts", canal] }); aoApagar(); },
  });

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (titulo.trim()) salvar.mutate(); }
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [titulo, salvar]);

  const copiar = async () => {
    await copiarTexto(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1300);
  };
  const baixar = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([texto], { type: "text/markdown;charset=utf-8" }));
    a.download = `${titulo || "prompt"}.md`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  if (!novo && !data) return <div className="cartao editor-prompt carregando">{t("app.carregando")}</div>;

  return (
    <div className="cartao editor-prompt">
      <input className="titulo-prompt" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={t("app.prompts.titulo_ex")} autoFocus={novo} />
      <div className="barra-prompt">
        <div className="pilulas">
          <button className={modo === "editar" ? "on" : ""} onClick={() => setModo("editar")}><PenLine size={14} /> {t("app.prompts.editar")}</button>
          <button className={modo === "ver" ? "on" : ""} onClick={() => setModo("ver")}><Eye size={14} /> {t("app.prompts.ver")}</button>
        </div>
        <span className="sub">{t("app.bloco.palavras", { n: texto.split(/\s+/).filter(Boolean).length })}</span>
        <div className="esp" />
        <button className={`bt pequeno ${copiado ? "" : "primario"}`} disabled={!texto} onClick={copiar}>
          {copiado ? <><Check size={14} />{t("app.copiar.feito")}</> : <><Copy size={14} />{t("app.prompts.copiar")}</>}
        </button>
        <button className="bt pequeno redondo" title={t("app.prompts.baixar")} disabled={!texto} onClick={baixar}><Download size={14} /></button>
        {!novo && (confirmar ? (
          <button className="bt pequeno perigo-cheio" onClick={() => apagar.mutate()} onMouseLeave={() => setConfirmar(false)}>{t("app.prompts.apagar_sim")}</button>
        ) : (
          <button className="bt pequeno redondo perigo" title={t("app.prompts.apagar")} onClick={() => setConfirmar(true)}><Trash2 size={14} /></button>
        ))}
      </div>
      {modo === "editar" ? (
        <textarea className="texto-prompt" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={t("app.prompts.texto_ex")} spellCheck={false} />
      ) : (
        <div className="ver-prompt" onDoubleClick={() => setModo("editar")}>
          {texto ? <Markdown texto={texto} /> : <p className="sub">{t("app.prompts.vazio_texto")}</p>}
        </div>
      )}
      <div className="rodape-form">
        <button className="bt primario" disabled={!titulo.trim() || salvar.isPending || (!sujo && !novo)} onClick={() => salvar.mutate()}>
          <Save size={16} />{t("comum.salvar")}
        </button>
        <span className="sub">{sujo ? t("app.prompts.nao_salvo") : salvar.isSuccess ? t("app.salvo") : ""} · ⌘S</span>
        {salvar.isError && <span className="erro">{salvar.error.message}</span>}
      </div>
    </div>
  );
}

export function PromptsTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const t = useT();
  const [params, setParams] = useSearchParams();
  const { data } = useQuery({ queryKey: ["prompts", canal], queryFn: () => pegar<{ prompts: Resumo[] }>(`/api/c/${canal}/prompts`) });
  const [busca, setBusca] = useState("");
  const [sujo, setSujo] = useState(false);
  const [sobre, setSobre] = useState(false);
  const campo = useRef<HTMLInputElement>(null);
  const lista = data?.prompts ?? [];
  const aberto = params.get("p") || (lista[0]?.nome ?? "");
  const abrir = useCallback((nome: string) => {
    if (sujo && nome !== aberto && !window.confirm(t("app.prompts.descartar"))) return;
    setSujo(false);
    setParams(nome ? { p: nome } : {});
  }, [sujo, aberto, setParams, t]);
  const { importar, erro } = useImportar(canal, (nomes) => abrir(nomes[0]));
  const termo = busca.trim().toLowerCase();
  const filtrados = useMemo(() => lista.filter((p) => !termo || `${p.titulo} ${p.previa}`.toLowerCase().includes(termo)), [lista, termo]);
  if (!dc) return null;

  return (
    <div className={`tela-prompts ${sobre ? "sobre" : ""}`}
         onDragOver={(e) => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); setSobre(true); } }}
         onDragLeave={(e) => { if (e.currentTarget === e.target) setSobre(false); }}
         onDrop={(e) => { e.preventDefault(); setSobre(false); importar([...e.dataTransfer.files]); }}>
      <Cabecalho titulo={t("app.prompts.titulo")} sub={t("app.prompts.explica")}>
        <button className="bt" onClick={() => campo.current?.click()}><Upload size={16} />{t("app.prompts.importar")}</button>
        <button className="bt redondo" title={t("app.abrir_pasta_dica")} onClick={() => enviar(`/api/c/${canal}/prompts-pasta`)}><FolderOpen size={16} /></button>
        <button className="bt primario" onClick={() => abrir(NOVO)}><Plus size={16} />{t("app.prompts.novo")}</button>
      </Cabecalho>
      <input ref={campo} type="file" multiple accept=".md,.markdown,.txt,text/markdown,text/plain" hidden
             onChange={(e) => { importar([...(e.target.files ?? [])]); e.target.value = ""; }} />
      {erro && <p className="erro" style={{ marginBottom: 12 }}>{erro}</p>}
      {!lista.length && aberto !== NOVO ? (
        <div className="nada-espera grande">
          <span className="ic"><FileText size={24} /></span>
          <b>{t("app.prompts.vazio")}</b>
          <span className="sub">{t("app.prompts.vazio_sub")}</span>
          <div className="acoes-final" style={{ marginTop: 10 }}>
            <button className="bt primario" onClick={() => abrir(NOVO)}><Plus size={16} />{t("app.prompts.novo")}</button>
            <button className="bt" onClick={() => campo.current?.click()}><Upload size={16} />{t("app.prompts.importar")}</button>
          </div>
        </div>
      ) : (
        <div className="prompts-grade">
          <aside className="lista-prompts">
            <label className="campo-busca"><Search size={16} /><input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder={t("app.prompts.buscar")} /></label>
            {aberto === NOVO && <div className="item-prompt on"><b>{t("app.prompts.novo")}</b><span className="sub">{t("app.prompts.nao_salvo")}</span></div>}
            {filtrados.map((p) => (
              <button key={p.nome} className={`item-prompt ${p.nome === aberto ? "on" : ""}`} onClick={() => abrir(p.nome)}>
                <b>{p.titulo}</b>
                {p.previa && <span className="previa">{p.previa}</span>}
                <span className="sub">{t("app.bloco.palavras", { n: p.palavras })} · {haQuanto(t, p.mudou)}</span>
              </button>
            ))}
            {!filtrados.length && termo && <p className="sub">{t("app.prompts.nada_busca")}</p>}
            <p className="dica-soltar">{t("app.prompts.dica_soltar")}</p>
          </aside>
          {aberto && (
            <Editor key={aberto} canal={canal} nome={aberto} setSujo={setSujo}
                    aoSalvar={(nome) => setParams({ p: nome }, { replace: true })}
                    aoApagar={() => { setSujo(false); setParams({}); }} />
          )}
        </div>
      )}
      {sobre && <div className="soltar-aqui"><Upload size={28} />{t("app.prompts.solte")}</div>}
    </div>
  );
}
