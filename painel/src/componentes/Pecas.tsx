// Peças das telas de canal: cartão de vídeo, item "esperando você", rodada em andamento e anel de consumo.
import { ChevronRight, Play, Square } from "lucide-react";
import { antiga, EstadoBloco, Esperando, Rodando, urlCapa, Video } from "../api";
import { compacto, haQuanto, useT } from "../textos";
import { Capa } from "./Imagens";

export function Segmentos({ estados, className = "segmentos" }: { estados: { nn: string; estado: EstadoBloco; topico?: string }[]; className?: string }) {
  return (
    <div className={className}>
      {estados.map((b) => (
        <i key={b.nn} className={b.estado} title={`${b.nn}${b.topico ? ` · ${b.topico}` : ""}`} />
      ))}
    </div>
  );
}

export function CartaoVideo({ canal, v, atraso = 0 }: { canal: string; v: Video; atraso?: number }) {
  const t = useT();
  const pct = v.n_blocos ? (100 * v.entregues) / v.n_blocos : 0;
  const detalhe =
    v.coluna === "producao" || v.coluna === "roteiro"
      ? t("app.video.blocos_de", { e: v.entregues, n: v.n_blocos })
      : t("app.video.blocos_pronto", { n: v.n_blocos });
  return (
    <a className="video" href={antiga.video(canal, v.slug)} style={{ animationDelay: `${atraso}ms` }}>
      <div className="cv">
        <Capa src={urlCapa(canal, v.slug)} />
        <span className={`st ${v.coluna === "producao" ? "p" : ""}`}>{t(`app.coluna.${v.coluna}`)}</span>
        {v.rodando > 0 && <span className="vivo"><span className="pulso" />{v.rodando}</span>}
        <span className="play"><Play size={16} /></span>
      </div>
      <div className="info">
        <b>{v.titulo_pub || v.titulo}</b>
        <span>{detalhe}{v.esperando > 0 && <em> · {t("app.esperando_n", { n: v.esperando })}</em>}</span>
        <div className="progresso">
          <i style={{ width: `${pct}%`, background: v.coluna === "producao" ? "var(--accent)" : undefined }} />
        </div>
      </div>
    </a>
  );
}

export function ItemEsperando({ canal, e }: { canal: string; e: Esperando }) {
  const t = useT();
  return (
    <a className="item" href={antiga.bloco(canal, e.video, e.nn)}>
      <Capa className="th" src={urlCapa(canal, e.video, e.nn)} />
      <div className="t">
        <b>{e.nn} · {e.topico}</b>
        <span><em>{t(`app.etapa.${e.etapa}`, undefined, e.etapa)}</em>{e.motivo ? ` · ${e.motivo}` : ""}</span>
        <span className="de">{e.video_titulo}</span>
      </div>
      <span className="vai"><ChevronRight size={18} /></span>
    </a>
  );
}

export function LinhaRodando({ canal, r, parar }: { canal: string; r: Rodando; parar: () => void }) {
  const t = useT();
  return (
    <div className="rod">
      <a href={antiga.bloco(canal, r.video, r.nn)}><Capa className="th" src={urlCapa(canal, r.video, r.nn)} /></a>
      <div className="t">
        <a href={antiga.bloco(canal, r.video, r.nn)}><b>{r.nn} · {r.topico}</b></a>
        <span>{r.etapa ? t(`app.etapa.${r.etapa}`, undefined, r.etapa) : t("app.rodando.comecando")}{r.detalhe ? ` · ${r.detalhe}` : ""}</span>
        <div className="passos">
          {Array.from({ length: r.total }, (_, i) => (
            <i key={i} className={i + 1 < r.indice ? "ok" : i + 1 === r.indice ? "run" : ""} />
          ))}
        </div>
      </div>
      <div className="tempo">
        <b>{haQuanto(t, r.desde).replace(/^há /, "")}</b>
        {r.indice ? t("app.rodando.etapa_de", { i: r.indice, n: r.total }) : ""}
      </div>
      <button className="x" onClick={parar} title={t("app.rodando.parar")}><Square size={14} /></button>
    </div>
  );
}

const CORES_CONSUMO = ["#6E4BFF", "#2F8CFF", "#19B3A6", "#F2A93B", "#E0679A", "#B7BAC6"];

export function AnelConsumo({ total, etapas }: { total: number; etapas: { etapa: string; tokens: number }[] }) {
  const t = useT();
  const principais = etapas.slice(0, 4);
  const resto = etapas.slice(4).reduce((s, e) => s + e.tokens, 0);
  const fatias = [...principais.map((e) => ({ rot: t(`app.consumo.${e.etapa}`, undefined, e.etapa), n: e.tokens })),
    ...(resto ? [{ rot: t("app.consumo.outros"), n: resto }] : [])];
  const R = 56, C = 2 * Math.PI * R;
  let ini = 0;
  return (
    <div className="anel">
      <div className="centro">
        <svg viewBox="0 0 140 140">
          <circle cx="70" cy="70" r={R} stroke="var(--raised)" />
          {total > 0 && fatias.map((f, i) => {
            const len = (C * f.n) / total;
            const el = <circle key={f.rot} cx="70" cy="70" r={R} stroke={CORES_CONSUMO[i]}
                               strokeDasharray={`${Math.max(len - 4, 1)} ${C}`} strokeDashoffset={-ini} />;
            ini += len;
            return el;
          })}
        </svg>
        <div><b>{compacto(total)}</b><span>{t("app.consumo.tokens")}</span></div>
      </div>
      <div className="leg">
        {fatias.map((f, i) => (
          <div key={f.rot}><i style={{ background: CORES_CONSUMO[i] }} />{f.rot}<b>{compacto(f.n)}</b></div>
        ))}
        {!fatias.length && <span className="sub">{t("app.consumo.nada")}</span>}
      </div>
    </div>
  );
}
