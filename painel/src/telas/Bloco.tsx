// Página de um bloco: linha do tempo das etapas (clicar numa etapa roda a partir dela), prévia com as versões,
// o que conferir antes de entregar, QA e storyboard legíveis e, recolhidos, os logs.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle, Check, ChevronLeft, ChevronRight, ExternalLink, FolderOpen, Loader, Play, Square, Wrench, X,
} from "lucide-react";
import { DetalheBloco, enviar, pegar, rota } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { Markdown } from "../componentes/Markdown";
import { useT } from "../textos";

// etapa do motor (rodar.py) → "feito" do estado.py
const FEITO: Record<string, string> = {
  narracao: "narracao", transcrever: "transcricao", storyboard: "storyboard", buscar: "busca", escolher: "escolha",
  editar: "edicao", entregar: "entregue",
};

function statusEtapa(b: DetalheBloco, e: DetalheBloco["etapas"][number]) {
  if (b.rodando && b.etapa_atual === e.id) return e.status === "corrigindo" ? "corrigindo" : "rodando";
  if (!b.rodando && b.parado?.etapa === e.id) return "parado";
  if (e.status === "ok" || b.feito[FEITO[e.id]]) return "ok";
  return "";
}

function PainelRodar({ canal, b, de: deInicial, fechar }: { canal: string; b: DetalheBloco; de: string; fechar: () => void }) {
  const t = useT();
  const qc = useQueryClient();
  const [de, setDe] = useState(deInicial);
  const [ate, setAte] = useState("");
  const [obs, setObs] = useState("");
  const rodar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${b.video}/b/${b.nn}/rodar`, { de, ate, obs }),
    onSuccess: () => { qc.invalidateQueries(); fechar(); },
  });
  return (
    <div className="painel-rodar cartao">
      <div className="linha-rodar">
        <label className="campo">{t("app.bloco.de")}
          <select value={de} onChange={(e) => setDe(e.target.value)}>
            <option value="">{t("app.bloco.onde_parou")}</option>
            {b.etapas.map((e) => <option key={e.id} value={e.id}>{t(`app.etapa.${e.id}`)}</option>)}
          </select>
        </label>
        <label className="campo">{t("app.bloco.ate")}
          <select value={ate} onChange={(e) => setAte(e.target.value)}>
            <option value="">{t("app.bloco.o_fim")}</option>
            {b.etapas.map((e) => <option key={e.id} value={e.id}>{t(`app.etapa.${e.id}`)}</option>)}
          </select>
        </label>
        <label className="campo obs">{t("app.bloco.obs")}
          <input value={obs} onChange={(e) => setObs(e.target.value)} placeholder={t("app.bloco.obs_ex")} />
        </label>
      </div>
      <div className="linha-rodar">
        <button className="bt primario" disabled={rodar.isPending} onClick={() => rodar.mutate()}><Play size={16} />{t("app.bloco.rodar")}</button>
        <button className="bt" onClick={fechar}>{t("app.cancelar")}</button>
        <span className="sub">{t("app.bloco.rodar_explica")}</span>
      </div>
      {rodar.isError && <p className="erro">{rodar.error.message}</p>}
    </div>
  );
}

export function BlocoTela() {
  const { canal = "", video = "", nn = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const t = useT();
  const qc = useQueryClient();
  const { data: b, error } = useQuery({
    queryKey: ["bloco", canal, video, nn],
    queryFn: () => pegar<DetalheBloco>(`/api/c/${canal}/v/${video}/b/${nn}`),
  });
  const [rodarDe, setRodarDe] = useState<string | null>(null);
  const [versao, setVersao] = useState<string | null>(null);
  const acao = useMutation({ mutationFn: (url: string) => enviar(url, {}), onSettled: () => qc.invalidateQueries() });
  if (error) throw error;
  if (!b || !dc) return <div className="carregando">{t("app.carregando")}</div>;

  const base = `/api/c/${canal}/v/${video}/b/${nn}`;
  const fontes = [...b.previas.map((p) => ({ id: `v${p.v}`, rot: `v${p.v}`, url: p.url })),
    ...(b.entregue ? [{ id: "entregue", rot: t("app.estado.ok"), url: b.entregue }] : [])];
  const atual = fontes.find((f) => f.id === versao) ?? fontes[b.previas.length ? b.previas.length - 1 : 0];

  return (
    <>
      <Cabecalho
        onde={<><Link to={rota.canal(canal)}>{dc.canal.nome}</Link> › <Link to={rota.video(canal, video)}>{b.video_titulo}</Link> › <b>{t("app.bloco.bloco_n", { nn })}</b></>}
        titulo={<>{nn} · {b.topico}</>}>
        <div className="navega">
          {b.anterior ? <Link className="bt redondo" to={rota.bloco(canal, video, b.anterior)} title={t("app.bloco.anterior")}><ChevronLeft size={18} /></Link> : <span className="bt redondo apagado"><ChevronLeft size={18} /></span>}
          {b.proximo ? <Link className="bt redondo" to={rota.bloco(canal, video, b.proximo)} title={t("app.bloco.proximo")}><ChevronRight size={18} /></Link> : <span className="bt redondo apagado"><ChevronRight size={18} /></span>}
        </div>
        <button className="bt redondo" onClick={() => enviar(`/api/c/${canal}/v/${video}/abrir`, { nn })} title={t("app.abrir_pasta_dica")}><FolderOpen size={16} /></button>
        {b.rodando ? (
          <button className="bt perigo" disabled={acao.isPending} onClick={() => acao.mutate(`${base}/parar`)}><Square size={14} />{t("app.bloco.parar")}</button>
        ) : (
          <button className="bt primario" onClick={() => setRodarDe(rodarDe === null ? "" : null)}><Play size={16} />{t("app.bloco.rodar")}</button>
        )}
      </Cabecalho>

      {b.parado && !b.rodando && (
        <div className="aviso-parado">
          <AlertTriangle size={20} />
          <div><b>{t("app.bloco.parado_em", { etapa: t(`app.etapa.${b.parado.etapa}`, undefined, b.parado.etapa || "") })}</b><span>{b.parado.motivo}</span></div>
          <button className="bt pequeno" onClick={() => setRodarDe(b.parado?.etapa && FEITO[b.parado.etapa] ? b.parado.etapa : "")}>{t("app.bloco.rodar_de_novo")}</button>
        </div>
      )}

      <div className="trilha">
        {b.etapas.map((e, i) => {
          const s = statusEtapa(b, e);
          return (
            <button key={e.id} className={`passo ${s}`} disabled={b.rodando} onClick={() => setRodarDe(e.id)}
                    title={[e.detalhe, e.quando, b.rodando ? "" : t("app.bloco.rodar_daqui")].filter(Boolean).join("\n")}>
              <span className="bolinha">
                {s === "ok" ? <Check size={14} /> : s === "rodando" ? <Loader size={14} className="gira" /> : s === "parado" ? <AlertTriangle size={13} /> : s === "corrigindo" ? <Wrench size={13} /> : i + 1}
              </span>
              <span className="nome">{t(`app.etapa.${e.id}`)}</span>
              {e.detalhe && <span className="detalhe">{e.detalhe}</span>}
            </button>
          );
        })}
      </div>

      {rodarDe !== null && !b.rodando && <PainelRodar key={rodarDe} canal={canal} b={b} de={rodarDe} fechar={() => setRodarDe(null)} />}

      <div className="bloco-grade">
        <div className="coluna-esq">
          <div className="cartao player">
            <div className="titulo-secao">
              <h3>{t("app.bloco.previa")}</h3>
              {b.previas.length > 0 && (b.aprovado ? <span className="selo ok"><Check size={12} />{t("app.bloco.qa_ok")}</span> : <span className="selo bad"><X size={12} />{t("app.bloco.qa_nao")}</span>)}
            </div>
            {atual ? (
              <>
                <video key={atual.url} controls preload="metadata" src={atual.url} />
                {fontes.length > 1 && (
                  <div className="pilulas versoes">
                    {fontes.map((f) => <button key={f.id} className={f.id === atual.id ? "on" : ""} onClick={() => setVersao(f.id)}>{f.rot}</button>)}
                  </div>
                )}
              </>
            ) : (
              <div className="vazio">{t("app.bloco.sem_previa")}</div>
            )}
          </div>

          {b.conferir.length > 0 && (
            <div className="cartao conferir">
              <div className="titulo-secao">
                <h3>{t(b.travar_conferir ? "app.bloco.conferir_trava" : "app.bloco.conferir")}<span className="contador">{b.conferir.length}</span></h3>
                {b.revisao && <a href={b.revisao} target="_blank" rel="noreferrer">{t("app.bloco.revisao")} <ExternalLink size={12} /></a>}
              </div>
              <div className="lista-conferir">
                {b.conferir.map((c) => (
                  <div className="conf" key={c.id}>
                    <div className="mini-asset">
                      {c.arquivo ? (c.arquivo.endsWith(".mp4") ? <video src={`${c.arquivo}#t=1`} preload="metadata" muted /> : <img src={c.arquivo} alt="" loading="lazy" />) : <span>{c.tipo}</span>}
                    </div>
                    <div className="t"><b>{c.id}</b><span>{c.texto}</span>{c.descricao && <em>{c.descricao}</em>}</div>
                  </div>
                ))}
              </div>
              {!b.rodando && (
                <div className="rodape-form">
                  <button className={`bt ${b.travar_conferir ? "primario" : ""}`} disabled={acao.isPending} onClick={() => acao.mutate(`${base}/conferir`)}>
                    <Check size={16} />{t(b.travar_conferir ? "app.bloco.aprovei" : "app.bloco.marcar_visto")}
                  </button>
                  <button className="bt pequeno" onClick={() => setRodarDe("escolher")}>{t("app.bloco.algo_errado")}</button>
                </div>
              )}
            </div>
          )}
          {!b.conferir.length && b.conferidos > 0 && <p className="sub">{t("app.bloco.conferidos", { n: b.conferidos })}{b.revisao && <> · <a href={b.revisao} target="_blank" rel="noreferrer">{t("app.bloco.revisao")}</a></>}</p>}
        </div>

        <div className="coluna-dir">
          {b.qa && (
            <div className="cartao qa">
              <div className="titulo-secao"><h3>QA</h3>{b.qa_folha && <a href={b.qa_folha} target="_blank" rel="noreferrer">{t("app.bloco.folha")} <ExternalLink size={12} /></a>}</div>
              <Markdown texto={b.qa.split("\n").filter((l) => !l.startsWith("# ")).join("\n")} />
            </div>
          )}
          {b.roteiro && (
            <details className="cartao recolhe roteiro" open={!b.qa || undefined}>
              <summary><h3>{t("app.bloco.roteiro")}</h3><span className="sub">{t("app.bloco.palavras", { n: b.roteiro.split(/\s+/).length })}</span></summary>
              <p className="texto-roteiro">{b.roteiro}</p>
            </details>
          )}
          <details className="cartao recolhe" open={b.rodando || undefined}>
            <summary><h3>{t("app.bloco.detalhes")}</h3><span className="sub">{b.log_etapa?.nome ?? "log_rodar.txt"}</span></summary>
            {b.log_rodar && <><h4>log_rodar.txt</h4><pre>{b.log_rodar}</pre></>}
            {b.log_etapa && <><h4>{b.log_etapa.nome}</h4><pre>{b.log_etapa.texto}</pre></>}
            {!b.log_rodar && !b.log_etapa && <p className="sub">{t("app.bloco.sem_log")}</p>}
          </details>
        </div>
      </div>

      {b.storyboard && (
        <details className="cartao recolhe storyboard">
          <summary><h3>{t("app.bloco.storyboard")}</h3><span className="sub">{b.storyboard.split("\n").find((l) => l.startsWith("Narração"))}</span></summary>
          <Markdown texto={b.storyboard.split("\n").filter((l) => !l.startsWith("# ")).join("\n")} />
        </details>
      )}
    </>
  );
}
