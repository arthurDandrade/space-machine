// Produção do VÍDEO INTEIRO (fluxo "video" do explained, 2026-11-05: space_machine/rodar_video.py). Os capítulos são
// narrados um a um; storyboard, busca, escolha, render e QA são do vídeo todo, e sai um MP4 só. A página tem a cara da
// página de um bloco: a linha das etapas (clicar numa roda a partir dela), o vídeo, o que conferir, o QA de cada
// capítulo, o storyboard e os logs.
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, ExternalLink, FolderOpen, Loader, Mic, Play, Square, Wrench, X } from "lucide-react";
import { AoVivo, IconeEtapa, motivoLimpo, resumoEtapa } from "../componentes/AoVivo";
import { DetalheVideo, enviar, ProducaoVideo as Producao } from "../api";
import { Markdown } from "../componentes/Markdown";
import { useT } from "../textos";

function statusEtapa(p: Producao, e: Producao["etapas"][number]) {
  if (p.rodando && p.etapa_atual === e.id) return e.status === "corrigindo" ? "corrigindo" : "rodando";
  if (!p.rodando && p.parado?.etapa === e.id) return "parado";
  if (p.feito[e.id]) return "ok";
  return "";
}

function PainelRodar({ canal, v, de: deInicial, fechar }: { canal: string; v: DetalheVideo; de: string; fechar: () => void }) {
  const t = useT();
  const qc = useQueryClient();
  const p = v.producao!;
  const [de, setDe] = useState(deInicial);
  const [ate, setAte] = useState("");
  const [obs, setObs] = useState("");
  const rodar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${v.slug}/produzir`, { de, ate, obs }),
    onSuccess: () => { qc.invalidateQueries(); fechar(); },
  });
  return (
    <div className="painel-rodar cartao">
      <div className="linha-rodar">
        <label className="campo">{t("app.bloco.de")}
          <select value={de} onChange={(e) => setDe(e.target.value)}>
            <option value="">{t("app.bloco.onde_parou")}</option>
            {p.etapas.map((e) => <option key={e.id} value={e.id}>{e.rotulo}</option>)}
          </select>
        </label>
        <label className="campo">{t("app.bloco.ate")}
          <select value={ate} onChange={(e) => setAte(e.target.value)}>
            <option value="">{t("app.bloco.o_fim")}</option>
            {p.etapas.map((e) => <option key={e.id} value={e.id}>{e.rotulo}</option>)}
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

// o resumo no cartão de andamento, no topo da página do vídeo
export function AndamentoVideo({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const p = v.producao!;
  const acao = useMutation({
    mutationFn: (url: string) => enviar(url, {}),
    onSettled: () => qc.invalidateQueries(),
  });
  const feitas = p.etapas.filter((e) => p.feito[e.id]).length;
  const etapa = p.etapas.find((e) => e.id === p.etapa_atual);
  return (
    <>
      <div className="parte">
        <div className="pct"><b>{Math.round((100 * feitas) / p.etapas.length)}%</b><span>{t("app.pv.etapas_feitas", { e: feitas, n: p.etapas.length })}</span></div>
        <div className="segmentos grossos">
          {p.etapas.map((e) => {
            const s = statusEtapa(p, e);
            return <i key={e.id} className={s === "ok" ? "ok" : s === "rodando" || s === "corrigindo" ? "run" : s === "parado" ? "wait" : ""} title={e.rotulo} />;
          })}
        </div>
        <div className="selos">
          {p.rodando && <span className="selo run"><span className="pulso" />{etapa ? etapa.rotulo : t("app.rodando.comecando")}</span>}
          {!p.rodando && p.parado && <span className="selo wait" title={motivoLimpo(p.parado.motivo)}>{t("app.bloco.parado_em", { etapa: p.etapas.find((e) => e.id === p.parado?.etapa)?.rotulo || p.parado.etapa || "" })}</span>}
          {p.feito.entregar && <span className="selo ok"><Check size={12} />{t("app.pv.pronto")}</span>}
        </div>
      </div>
      <div className="parte">
        <h4>{t("app.pv.titulo")}</h4>
        <div className="fila-card">
          <div className="linha-fila">
            {p.rodando ? (
              <button className="bt perigo" disabled={acao.isPending} onClick={() => acao.mutate(`/api/c/${canal}/v/${v.slug}/produzir/parar`)}><Square size={14} />{t("app.bloco.parar")}</button>
            ) : !p.feito.entregar ? (
              <button className="bt primario" disabled={acao.isPending} onClick={() => acao.mutate(`/api/c/${canal}/v/${v.slug}/produzir`)}>
                <Play size={16} />{t(p.atual ? "app.pv.continuar" : "app.pv.produzir")}
              </button>
            ) : null}
            {p.mp4 && <a className="bt pequeno" href={p.mp4} target="_blank" rel="noreferrer"><Play size={14} />{t("app.final.assistir", { gb: (p.mp4_tamanho / 1e9).toFixed(1).replace(".", ",") })}</a>}
            {p.mp4 && <button className="bt pequeno" onClick={() => enviar(`/api/c/${canal}/v/${v.slug}/abrir`, { sub: "final" })}><FolderOpen size={14} />{t("app.final.pasta")}</button>}
          </div>
          {!p.atual && !p.rodando && <p className="sub">{t("app.pv.explica")}</p>}
          {acao.isError && <p className="erro">{acao.error.message}</p>}
        </div>
      </div>
    </>
  );
}

// a aba "Produção": etapas, vídeo, conferir, QA por capítulo, capítulos, storyboard e logs
export function ProducaoVideo({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const p = v.producao!;
  const [rodarDe, setRodarDe] = useState<string | null>(null);
  const [qaDe, setQaDe] = useState<string | null>(null);
  const acao = useMutation({ mutationFn: (url: string) => enviar(url, {}), onSettled: () => qc.invalidateQueries() });
  const base = `/api/c/${canal}/v/${v.slug}/produzir`;
  const comQa = p.capitulos.filter((c) => c.qa);
  const qaAberto = comQa.find((c) => c.nn === qaDe) ?? comQa.find((c) => !c.aprovado) ?? comQa[0];
  const pronto = p.feito.entregar;                // vídeo entregue: o que foi conferência e QA vira histórico, recolhido
  const qaTodoOk = comQa.length > 0 && comQa.every((c) => c.aprovado);
  const agora = p.etapas.find((e) => e.id === p.etapa_atual);
  // quanto da etapa já foi: o motor diz no detalhe ("(3/10)"); onde não diz, os arquivos dizem
  const medida = !agora ? null
    : agora.id === "narracao" ? { feito: p.capitulos.filter((c) => c.narrado).length, total: p.capitulos.length }
    : agora.id === "transcrever" ? { feito: p.capitulos.filter((c) => c.transcrito).length, total: p.capitulos.length }
    : agora.id === "escolher" && p.assets_total ? { feito: p.assets_prontos, total: p.assets_total }
    : null;
  const motivo = p.parado?.motivo ?? "";

  return (
    <>
      {p.rodando && agora && (
        <AoVivo etapa={agora.id} rotulo={agora.rotulo} indice={p.etapas.indexOf(agora) + 1} total={p.etapas.length}
                detalhe={agora.detalhe} inicio={agora.inicio} progresso={medida && medida.total ? medida : null}
                log={p.log_etapa?.texto || p.log_rodar} corrigindo={agora.status === "corrigindo"}
                parar={() => acao.mutate(`${base}/parar`)} parando={acao.isPending} />
      )}
      {p.parado && !p.rodando && (
        <div className="aviso-parado">
          <AlertTriangle size={20} />
          <div>
            <b>{t("app.bloco.parado_em", { etapa: p.etapas.find((e) => e.id === p.parado?.etapa)?.rotulo || p.parado.etapa || "" })}</b>
            <span>{motivoLimpo(motivo)}</span>
            {motivoLimpo(motivo) !== motivo.trim() && <details className="tecnico"><summary>{t("app.aovivo.detalhe_tecnico")}</summary><pre>{motivo}</pre></details>}
          </div>
          <button className="bt pequeno" onClick={() => setRodarDe(p.parado?.etapa && p.feito[p.parado.etapa] !== undefined ? p.parado.etapa : "")}>{t("app.bloco.rodar_de_novo")}</button>
        </div>
      )}

      <div className="trilha">
        {p.etapas.map((e) => {
          const s = statusEtapa(p, e);
          return (
            <button key={e.id} className={`passo ${s}`} disabled={p.rodando} onClick={() => setRodarDe(e.id)}
                    title={[motivoLimpo(e.detalhe), e.quando, p.rodando ? "" : t("app.bloco.rodar_daqui")].filter(Boolean).join("\n")}>
              <span className="bolinha">
                {s === "ok" ? <Check size={14} /> : s === "rodando" ? <Loader size={14} className="gira" /> : s === "parado" ? <AlertTriangle size={13} /> : s === "corrigindo" ? <Wrench size={13} /> : <IconeEtapa etapa={e.id} />}
              </span>
              <span className="nome">{e.rotulo}</span>
              <span className="detalhe">{resumoEtapa(t, s, e)}</span>
            </button>
          );
        })}
      </div>

      {rodarDe !== null && !p.rodando && <PainelRodar key={rodarDe} canal={canal} v={v} de={rodarDe} fechar={() => setRodarDe(null)} />}

      <div className="bloco-grade">
        <div className="coluna-esq">
          <div className="cartao player">
            <div className="titulo-secao">
              <h3>{t("app.pv.video_final")}</h3>
              {p.feito.entregar ? <span className="selo ok"><Check size={12} />{t("app.pv.pronto")}</span>
                : p.feito.montar ? <span className="selo neutro">{t("app.pv.renderizado")}</span> : null}
            </div>
            {p.mp4 ? <video key={p.mp4} controls preload="metadata" src={p.mp4} /> : <div className="vazio">{t("app.pv.sem_video")}</div>}
          </div>

          {p.conferir.length > 0 && (
            <details className="cartao conferir recolhe" open={!pronto || undefined}>
              <summary>
                <h3>{t(p.travar_conferir ? "app.bloco.conferir_trava" : "app.bloco.conferir")}<span className="contador">{p.conferir.length}</span></h3>
                {pronto && <span className="sub">{t("app.aovivo.conferir_entregue")}</span>}
              </summary>
              <div className="lista-conferir">
                {p.conferir.map((c) => (
                  <div className="conf" key={c.id}>
                    <div className="mini-asset">
                      {c.arquivo ? (c.arquivo.includes(".mp4") ? <video src={`${c.arquivo}#t=1`} preload="metadata" muted /> : <img src={c.arquivo} alt="" loading="lazy" />) : <span>{c.tipo}</span>}
                    </div>
                    <div className="t"><b>{c.id}</b><span>{c.texto}</span>{c.descricao && <em>{c.descricao}</em>}</div>
                  </div>
                ))}
              </div>
              {!p.rodando && (
                <div className="rodape-form">
                  <button className={`bt ${p.travar_conferir ? "primario" : ""}`} disabled={acao.isPending} onClick={() => acao.mutate(`${base}/conferir`)}>
                    <Check size={16} />{t(p.travar_conferir ? "app.bloco.aprovei" : "app.bloco.marcar_visto")}
                  </button>
                  <button className="bt pequeno" onClick={() => setRodarDe("escolher")}>{t("app.bloco.algo_errado")}</button>
                </div>
              )}
            </details>
          )}
          {!p.conferir.length && p.conferidos > 0 && <p className="sub">{t("app.bloco.conferidos", { n: p.conferidos })}</p>}

          <div className="cartao capitulos">
            <div className="titulo-secao"><h3>{t("app.pv.capitulos")}<span className="contador">{p.capitulos.length}</span></h3>
              {p.assets_total > 0 && <span className="sub">{t("app.pv.assets", { p: p.assets_prontos, n: p.assets_total })}</span>}
            </div>
            <div className="lista-capitulos">
              {p.capitulos.map((c) => (
                <div className="cap" key={c.nn}>
                  <span className="nn">{c.nn}</span>
                  <b>{c.topico}</b>
                  <span className={`selo ${c.transcrito ? "ok" : c.narrado ? "neutro" : ""}`}>
                    <Mic size={12} />{t(c.transcrito ? "app.pv.transcrito" : c.narrado ? "app.pv.narrado" : "app.pv.sem_narracao")}
                  </span>
                  {c.qa ? (
                    <button className={`selo ${c.aprovado ? "ok" : "bad"}`} onClick={() => setQaDe(c.nn)}>
                      {c.aprovado ? <Check size={12} /> : <X size={12} />}{t(c.aprovado ? "app.pv.qa_ok" : "app.pv.qa_nao")}
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="coluna-dir">
          {qaAberto && (
            <details className="cartao qa recolhe" open={!(pronto && qaTodoOk) || undefined}>
              <summary>
                <h3>{t("app.aovivo.qa_titulo")}</h3>
                <span className={`selo ${qaTodoOk ? "ok" : "bad"}`}>{qaTodoOk ? <Check size={12} /> : <X size={12} />}{t("app.aovivo.qa_resumo", { ok: comQa.filter((c) => c.aprovado).length, n: comQa.length })}</span>
              </summary>
              <div className="titulo-secao">
                <h4>{qaAberto.nn} · {qaAberto.topico}</h4>
                {qaAberto.folha && <a href={qaAberto.folha} target="_blank" rel="noreferrer">{t("app.bloco.folha")} <ExternalLink size={12} /></a>}
              </div>
              {comQa.length > 1 && (
                <div className="pilulas versoes">
                  {comQa.map((c) => <button key={c.nn} className={`${c.nn === qaAberto.nn ? "on" : ""} ${c.aprovado ? "" : "ruim"}`} onClick={() => setQaDe(c.nn)}>{c.nn}</button>)}
                </div>
              )}
              <Markdown texto={qaAberto.qa.split("\n").filter((l) => !l.startsWith("# ")).join("\n")} />
            </details>
          )}
          <details className="cartao recolhe">
            <summary><h3>{t("app.bloco.detalhes")}</h3><span className="sub">{t("app.aovivo.logs")}</span></summary>
            {p.log_rodar && <><h4>log_rodar.txt</h4><pre>{p.log_rodar}</pre></>}
            {p.log_etapa && <><h4>{p.log_etapa.nome}</h4><pre>{p.log_etapa.texto}</pre></>}
            {!p.log_rodar && !p.log_etapa && <p className="sub">{t("app.bloco.sem_log")}</p>}
          </details>
        </div>
      </div>

      {p.storyboard && (
        <details className="cartao recolhe storyboard">
          <summary><h3>{t("app.pv.storyboard")}</h3><span className="sub">{p.storyboard.split("\n").find((l) => / capítulos, /.test(l))}</span></summary>
          <Markdown texto={p.storyboard.split("\n").filter((l) => !l.startsWith("# ")).join("\n")} />
        </details>
      )}
    </>
  );
}
