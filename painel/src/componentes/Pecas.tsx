// Peças das telas de canal: cartão de vídeo, item "esperando você", rodada em andamento e anel de consumo.
import { Link } from "react-router-dom";
import { ChevronRight, Square } from "lucide-react";
import { EstadoBloco, Esperando, Rodando, rota, urlCapa, Video } from "../api";
import { compacto, haQuanto, useT } from "../textos";
import { TituloCopiavel } from "./Copiar";
import { Capa } from "./Imagens";
import { BarraThumb, useSoltar, useThumbnail } from "./Thumbnail";

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
  const { enviar } = useThumbnail(canal, v.slug);
  const soltar = useSoltar(enviar);
  const capa = urlCapa(canal, v.slug, undefined, v.capa_v);
  const detalhe =
    v.arquivado ? t("app.arquivar.selo")
    : v.fluxo === "video" ? t("app.video.capitulos_n", { n: v.n_blocos })     // o vídeo inteiro anda junto
    : v.coluna === "producao" || v.coluna === "roteiro"
      ? t("app.video.blocos_de", { e: v.entregues, n: v.n_blocos })
      : t("app.video.blocos_pronto", { n: v.n_blocos });
  return (
    <Link className="video" to={rota.video(canal, v.slug)} style={{ animationDelay: `${atraso}ms` }}>
      <div className={`cv ${soltar.sobre ? "sobre" : ""}`} {...soltar.props}>
        <Capa src={capa} existe={v.tem_capa} />
        <BarraThumb canal={canal} video={v.slug} thumb={v.thumb} capa={capa} />
        <span className={`st ${v.coluna === "producao" ? "p" : ""}`}>{t(`app.coluna.${v.coluna}`)}</span>
        {v.rodando > 0 && <span className="vivo"><span className="pulso" />{v.rodando}</span>}
      </div>
      <div className="info">
        <b>{v.numero > 0 && <span className="num-video">{String(v.numero).padStart(2, "0")}</span>}<TituloCopiavel texto={v.titulo_pub || v.titulo} /></b>
        <span>{detalhe}{v.esperando > 0 && <em> · {t("app.esperando_n", { n: v.esperando })}</em>}</span>
        <div className="progresso">
          <i style={{ width: `${v.arquivado ? 100 : pct}%`, background: v.coluna === "producao" ? "var(--accent)" : undefined }} />
        </div>
      </div>
    </Link>
  );
}

export function ItemEsperando({ canal, e }: { canal: string; e: Esperando }) {
  const t = useT();
  return (
    // nn vazio = o vídeo inteiro (fluxo "video"): vai para a página do vídeo
    <Link className="item" to={e.nn ? rota.bloco(canal, e.video, e.nn) : rota.video(canal, e.video)}>
      <Capa className="th" src={urlCapa(canal, e.video, e.nn || undefined)} existe={e.tem_capa} />
      <div className="t">
        <b>{e.nn ? `${e.nn} · ${e.topico}` : e.video_titulo}</b>
        <span><em>{t(`app.etapa.${e.etapa}`, undefined, e.etapa)}</em>{e.motivo ? ` · ${e.motivo}` : ""}</span>
        <span className="de">{e.video_titulo}</span>
      </div>
      <span className="vai"><ChevronRight size={18} /></span>
    </Link>
  );
}

export function LinhaRodando({ canal, r, parar }: { canal: string; r: Rodando; parar: () => void }) {
  const t = useT();
  return (
    <div className="rod">
      <Link to={r.nn ? rota.bloco(canal, r.video, r.nn) : rota.video(canal, r.video)}><Capa className="th" src={urlCapa(canal, r.video, r.nn || undefined)} existe={r.tem_capa} /></Link>
      <div className="t">
        <Link to={r.nn ? rota.bloco(canal, r.video, r.nn) : rota.video(canal, r.video)}><b>{r.nn ? `${r.nn} · ${r.topico}` : r.video_titulo}</b></Link>
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
