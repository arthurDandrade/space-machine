// O que está acontecendo AGORA numa produção: a etapa em palavras de gente, quanto dela já foi (quando dá para
// medir), há quanto tempo está nela, as últimas linhas do motor e o botão de parar. Aparece no topo da página do
// vídeo e do bloco enquanto algo roda. Aqui ficam também as peças que as duas trilhas de etapas dividem: o ícone de
// cada etapa, o texto curto debaixo do nome e o motivo de uma parada sem o trecho técnico.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Captions, Combine, FileText, Film, Images, LayoutList, LucideIcon, Mic, PackageCheck, Search, ShieldCheck, Square, Wrench,
} from "lucide-react";
import { Rodando, rota } from "../api";
import { haQuanto, useT } from "../textos";

type T = ReturnType<typeof useT>;

// uma etapa tem o mesmo ícone em todo lugar (trilha, painel ao vivo, barra lateral)
const ICONES: Record<string, LucideIcon> = {
  roteiro: FileText, narracao: Mic, transcrever: Captions, transcricao: Captions, juntar: Combine, storyboard: LayoutList,
  buscar: Search, busca: Search, escolher: Images, escolha: Images, montar: Film, editar: Film, edicao: Film,
  aprovado: ShieldCheck, entregar: PackageCheck, entregue: PackageCheck,
};
export function IconeEtapa({ etapa, size = 14 }: { etapa: string; size?: number }) {
  const Icone = ICONES[etapa] ?? Film;
  return <Icone size={size} />;
}

// "2026-11-11 16:40:02" (hora do Mac onde o painel roda) → segundos
const segundos = (quando: string) => (quando ? new Date(quando.replace(" ", "T")).getTime() / 1000 : 0);

function duracao(s: number) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
  return h ? `${h} h ${String(m).padStart(2, "0")} min` : m ? `${m} min ${String(seg).padStart(2, "0")} s` : `${seg} s`;
}

// o relógio anda sozinho: os dados do servidor só chegam quando um arquivo muda
function Decorrido({ desde }: { desde: number }) {
  const [agora, setAgora] = useState(Date.now() / 1000);
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now() / 1000), 1000);
    return () => clearInterval(id);
  }, []);
  return <>{duracao(agora - desde)}</>;
}

// "capítulo 03 (3/10)" → 3 de 10: o motor escreve assim quando sabe quanto falta
export function progressoDoDetalhe(detalhe: string) {
  const m = /\((\d+)\/(\d+)\)/.exec(detalhe || "");
  return m && +m[2] > 0 ? { feito: +m[1], total: +m[2] } : null;
}

// O motivo de uma parada, sem o rastro do Python que às vezes vem junto (fica nos detalhes técnicos).
export function motivoLimpo(motivo = "") {
  const linha = motivo.split("\n")[0];
  const corte = linha.search(/:?\s*(Traceback|File "|\S+\.py\b)/);
  return (corte > 20 ? linha.slice(0, corte) : linha).trim();
}

// O que vai debaixo do nome da etapa na trilha: o que está fazendo, se precisa de você, ou há quanto tempo ficou pronta.
export function resumoEtapa(t: T, status: string, e: { detalhe: string; quando: string }) {
  if (status === "rodando" || status === "corrigindo") return e.detalhe || t("app.rodando.comecando");
  if (status === "parado") return t("app.aovivo.precisa_de_voce");
  if (status === "ok" && e.quando) return haQuanto(t, segundos(e.quando));
  return "";
}

export function AoVivo({ etapa, rotulo, indice, total, detalhe, inicio, progresso, log, corrigindo, parar, parando }: {
  etapa: string; rotulo: string; indice: number; total: number; detalhe: string; inicio: string;
  progresso: { feito: number; total: number } | null; log: string; corrigindo?: boolean; parar: () => void; parando: boolean;
}) {
  const t = useT();
  const medido = progresso ?? progressoDoDetalhe(detalhe);
  const linhas = (log || "").split("\n").map((l) => l.trim()).filter(Boolean).slice(-3);
  return (
    <div className={`ao-vivo ${corrigindo ? "corrigindo" : ""}`}>
      <div className="icone">{corrigindo ? <Wrench size={22} /> : <IconeEtapa etapa={etapa} size={22} />}</div>
      <div className="meio">
        <span className="rotulo"><span className="pulso" />{t(corrigindo ? "app.aovivo.corrigindo" : "app.aovivo.agora")} · {t("app.rodando.etapa_de", { i: indice, n: total })}</span>
        <b>{rotulo}</b>
        <p>{t(`app.aovivo.${etapa}`, undefined, "")}</p>
        {medido ? (
          <div className="medida">
            <div className="barra"><i style={{ width: `${Math.min(100, (100 * medido.feito) / medido.total)}%` }} /></div>
            <span>{detalhe || t("app.aovivo.de", { feito: medido.feito, total: medido.total })}</span>
          </div>
        ) : (
          <div className="medida">
            <div className="barra solta"><i /></div>
            <span>{detalhe || t("app.rodando.comecando")}</span>
          </div>
        )}
        {linhas.length > 0 && (
          <details className="motor">
            <summary>{t("app.aovivo.motor")}</summary>
            {linhas.map((l, i) => <code key={i}>{l}</code>)}
          </details>
        )}
      </div>
      <div className="lado-direito">
        {inicio && <span className="tempo"><b><Decorrido desde={segundos(inicio)} /></b>{t("app.aovivo.nesta_etapa")}</span>}
        <button className="bt perigo pequeno" disabled={parando} onClick={parar}><Square size={13} />{t("app.bloco.parar")}</button>
      </div>
    </div>
  );
}

// Na barra lateral do canal: o que está rodando, visível de qualquer tela, com um clique para ir ver.
export function RodandoNaBarra({ canal, rodando }: { canal: string; rodando: Rodando[] }) {
  const t = useT();
  if (!rodando.length) return null;
  const r = rodando[0];
  return (
    <Link className="rodando-barra" to={r.nn ? rota.bloco(canal, r.video, r.nn) : rota.video(canal, r.video)}>
      <span className="topo"><span className="pulso" />{t(rodando.length > 1 ? "app.aovivo.barra_n" : "app.aovivo.barra", { n: rodando.length })}</span>
      <b>{r.nn ? `${r.nn} · ${r.topico}` : r.video_titulo}</b>
      <span className="etapa"><IconeEtapa etapa={r.etapa} size={13} />{r.etapa ? t(`app.etapa.${r.etapa}`, undefined, r.etapa) : t("app.rodando.comecando")}{r.indice ? ` · ${r.indice}/${r.total}` : ""}</span>
      <div className="passos">{Array.from({ length: r.total }, (_, i) => <i key={i} className={i + 1 < r.indice ? "ok" : i + 1 === r.indice ? "run" : ""} />)}</div>
    </Link>
  );
}
