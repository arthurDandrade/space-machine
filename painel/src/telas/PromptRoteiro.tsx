// Prompt de roteiro do canal: o que o Claude segue para escrever o roteiro de um vídeo novo a partir do título.
// Sem alteração sua, vale o que o formato traz (sempre o atual). Alterou e salvou: passa a valer o seu, guardado em
// <canal>/prompts/Roteiro do vídeo.md. "Voltar ao do formato" tira o seu de uso (vai para prompts/_lixeira/).
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Eye, PenLine, RotateCcw, Save } from "lucide-react";
import { enviar, pegar } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { copiarTexto } from "../componentes/Copiar";
import { Dialogo } from "../componentes/Dialogo";
import { Markdown } from "../componentes/Markdown";
import { haQuanto, useT } from "../textos";

interface PromptRoteiro {
  texto: string; origem: "canal" | "formato" | "nenhum"; padrao: string; escreve: boolean;
  formato: string; formato_nome: string; palavras: number; mudou: number | null;
}

export function PromptRoteiroTela() {
  const { canal = "" } = useParams();
  const t = useT();
  const qc = useQueryClient();
  const chave = ["roteiro-prompt", canal];
  const { data } = useQuery({ queryKey: chave, refetchInterval: false, queryFn: () => pegar<PromptRoteiro>(`/api/c/${canal}/roteiro-prompt`) });
  const [texto, setTexto] = useState("");
  const [modo, setModo] = useState<"editar" | "ver">("ver");
  const [copiado, setCopiado] = useState(false);
  const [voltar, setVoltar] = useState(false);
  // preenche quando chega do servidor (abrir a tela, salvar, voltar ao do formato), não enquanto você escreve
  const base = useRef<string | null>(null);
  useEffect(() => {
    if (data && base.current !== data.texto) { base.current = data.texto; setTexto(data.texto); }
  }, [data]);
  const recebeu = (r: PromptRoteiro) => { base.current = null; qc.setQueryData(chave, r); };
  const salvar = useMutation({
    mutationFn: () => enviar<PromptRoteiro>(`/api/c/${canal}/roteiro-prompt`, { texto }),
    onSuccess: recebeu,
  });
  const padrao = useMutation({
    mutationFn: () => enviar<PromptRoteiro>(`/api/c/${canal}/roteiro-prompt/padrao`),
    onSuccess: (r) => { setVoltar(false); recebeu(r); },
  });
  const sujo = !!data && texto !== data.texto;
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (sujo) salvar.mutate(); }
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [sujo, salvar]);
  if (!data) return <div className="carregando">{t("app.carregando")}</div>;

  const copiar = async () => { await copiarTexto(texto); setCopiado(true); setTimeout(() => setCopiado(false), 1300); };
  return (
    <>
      <Cabecalho titulo={t("app.roteiro_prompt.titulo")} sub={t("app.roteiro_prompt.explica")} />
      <div className="cartao editor-prompt">
        <div className="selos" style={{ marginBottom: 10 }}>
          {data.origem === "canal" ? <span className="selo wait">{t("app.roteiro_prompt.seu")}</span>
            : data.origem === "formato" ? <span className="selo ok">{t("app.roteiro_prompt.do_formato", { formato: data.formato_nome })}</span>
            : <span className="selo neutro">{t("app.roteiro_prompt.nenhum")}</span>}
          {data.origem === "canal" && data.mudou && <span className="sub">{t("app.video.mexido", { quando: haQuanto(t, data.mudou) })}</span>}
        </div>
        {!data.escreve && <p className="aviso-texto">{t("app.roteiro_prompt.nao_escreve", { formato: data.formato_nome })}</p>}
        <div className="barra-prompt">
          <div className="pilulas">
            <button className={modo === "editar" ? "on" : ""} onClick={() => setModo("editar")}><PenLine size={14} /> {t("app.prompts.editar")}</button>
            <button className={modo === "ver" ? "on" : ""} onClick={() => setModo("ver")}><Eye size={14} /> {t("app.prompts.ver")}</button>
          </div>
          <span className="sub">{t("app.bloco.palavras", { n: texto.split(/\s+/).filter(Boolean).length })}</span>
          <div className="esp" />
          <button className="bt pequeno" disabled={!texto} onClick={copiar}>
            {copiado ? <><Check size={14} />{t("app.copiar.feito")}</> : <><Copy size={14} />{t("app.prompts.copiar")}</>}
          </button>
          {data.origem === "canal" && data.padrao && (
            <button className="bt pequeno" onClick={() => setVoltar(true)}><RotateCcw size={14} />{t("app.roteiro_prompt.voltar")}</button>
          )}
        </div>
        {modo === "editar" ? (
          <textarea className="texto-prompt" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={t("app.roteiro_prompt.vazio")} spellCheck={false} autoFocus />
        ) : (
          <div className="ver-prompt" onDoubleClick={() => setModo("editar")}>
            {texto ? <Markdown texto={texto} /> : <p className="sub">{t("app.roteiro_prompt.vazio")}</p>}
          </div>
        )}
        <div className="rodape-form">
          <button className="bt primario" disabled={!sujo || salvar.isPending} onClick={() => salvar.mutate()}><Save size={16} />{t("comum.salvar")}</button>
          <span className="sub">{sujo ? t("app.prompts.nao_salvo") : salvar.isSuccess ? t("app.salvo") : ""} · ⌘S</span>
          {salvar.isError && <span className="erro">{salvar.error.message}</span>}
        </div>
      </div>
      {voltar && (
        <Dialogo titulo={t("app.roteiro_prompt.voltar_titulo")} fechar={() => setVoltar(false)}
          acoes={<>
            <button className="bt" onClick={() => setVoltar(false)}>{t("app.cancelar")}</button>
            <button className="bt primario" disabled={padrao.isPending} onClick={() => padrao.mutate()}><RotateCcw size={16} />{t("app.roteiro_prompt.voltar")}</button>
          </>}>
          <p>{t("app.roteiro_prompt.voltar_explica", { formato: data.formato_nome })}</p>
        </Dialogo>
      )}
    </>
  );
}
