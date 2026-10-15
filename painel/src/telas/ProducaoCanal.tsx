// Produção do canal (a tela de entrada de um canal): o vídeo em produção, o que espera você, o processo de
// produção com as capas, o que está rodando, as próximas publicações e o consumo do Claude na semana.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CalendarClock, CalendarPlus, CircleCheck, Clapperboard, Cog, FileText, Lightbulb, ListOrdered, Play, Scissors, Sparkles,
} from "lucide-react";
import { antiga, Coluna, enviar, PainelCanal, rota, urlCapa, Video } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { Capa } from "../componentes/Imagens";
import { AnelConsumo, CartaoVideo, ItemEsperando, LinhaRodando, Segmentos } from "../componentes/Pecas";
import { saudacao, useT } from "../textos";

const ICONES: Record<Coluna, typeof Cog> = {
  ideia: Lightbulb, roteiro: FileText, producao: Cog, edicao_final: Scissors, agendado: CalendarClock, publicado: CircleCheck,
};

function Heroi({ canal, v }: { canal: string; v: Video | null }) {
  const t = useT();
  const qc = useQueryClient();
  const acao = useMutation({
    mutationFn: (url: string) => enviar(url, { maximo: 3 }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["canal", canal] }),
  });
  if (!v)
    return (
      <div className="heroi vazio-heroi">
        <div className="txt">
          <span className="tag"><Clapperboard size={14} />{t("app.producao.nada_em_producao")}</span>
          <h2>{t("app.producao.comece")}</h2>
          <p>{t("app.producao.comece_sub")}</p>
          <div className="acoes"><a className="bt branco" href={antiga.novoVideo(canal)}>{t("app.novo_video")}</a></div>
        </div>
      </div>
    );
  const faltam = v.n_blocos - v.entregues - v.esperando - v.rodando;
  const filaAtiva = !!v.fila?.ativa;
  const ultimoEntregue = [...v.blocos].reverse().find((b) => b.estado === "ok");
  const resumo = [
    t("app.video.blocos_entregues", { e: v.entregues, n: v.n_blocos }),
    v.rodando ? t("app.n_rodando", { n: v.rodando }) : "",
    v.na_fila ? t("app.n_na_fila", { n: v.na_fila }) : "",
    v.esperando ? t("app.esperando_n", { n: v.esperando }) : "",
  ].filter(Boolean).join(" · ");
  const base = `/api/c/${canal}/v/${v.slug}/fila`;
  return (
    <div className="heroi">
      <div className="arte"><Capa src={urlCapa(canal, v.slug)} icone={false} existe={v.tem_capa} /></div>
      {ultimoEntregue && <div className="arte b"><Capa src={urlCapa(canal, v.slug, ultimoEntregue.nn)} icone={false} /></div>}
      <div className="txt">
        <span className="tag">{v.rodando > 0 && <span className="pulso branco" />}{t("app.coluna.producao")}</span>
        <h2>{v.titulo_pub || v.titulo}</h2>
        <p>{resumo}</p>
        <Segmentos estados={v.blocos} className="segs" />
        <div className="legenda">
          <span style={{ "--c": "#5BE39A" } as React.CSSProperties}>{t("app.estado.ok")}</span>
          <span style={{ "--c": "#fff" } as React.CSSProperties}>{t("app.estado.run")}</span>
          <span style={{ "--c": "#FFC24D" } as React.CSSProperties}>{t("app.estado.wait")}</span>
        </div>
        <div className="acoes">
          {filaAtiva ? (
            <button className="bt vidro" disabled={acao.isPending} onClick={() => acao.mutate(`${base}/parar`)}>
              <ListOrdered size={16} />{t("app.fila.parar")}
            </button>
          ) : faltam > 0 ? (
            <button className="bt branco" disabled={acao.isPending} onClick={() => acao.mutate(base)}>
              <Play size={16} />{acao.isPending ? t("app.fila.iniciando") : t("app.fila.produzir_n", { n: faltam })}
            </button>
          ) : null}
          <Link className="bt vidro" to={rota.video(canal, v.slug)}>{t("app.video.abrir")}</Link>
        </div>
        {acao.isError && <p className="erro-acao">{String(acao.error.message)}</p>}
      </div>
    </div>
  );
}

function Processo({ canal, dados }: { canal: string; dados: PainelCanal }) {
  const t = useT();
  const [filtro, setFiltro] = useState<Coluna | null>(null);
  const lista = filtro ? dados.videos.filter((v) => v.coluna === filtro) : dados.videos;
  return (
    <section className="processo">
      <div className="titulo-secao"><h3>{t("app.producao.processo")}</h3><a href={antiga.ideias(canal)}>{t("app.producao.abrir_quadro")}</a></div>
      <div className="etapas">
        {dados.colunas.map((c) => {
          const Icone = ICONES[c.id];
          return (
            <button key={c.id} className={`etapa ${c.n ? "" : "vazia"} ${filtro === c.id ? "on" : ""}`}
                    onClick={() => setFiltro(filtro === c.id ? null : c.id)}>
              <div className="n">{c.n}</div>
              <div className="r"><Icone size={15} />{t(`app.coluna.${c.id}`)}</div>
            </button>
          );
        })}
      </div>
      <div className="filtros">
        <span className="sub">
          {filtro ? `${t(`app.coluna.${filtro}`)} · ${lista.length}` : t("app.producao.todos_videos", { n: lista.length })}
        </span>
        {filtro && <button className="bt pequeno" onClick={() => setFiltro(null)}>{t("app.producao.ver_todos")}</button>}
      </div>
      {filtro === "ideia" ? (
        <div className="vazio"><Lightbulb size={18} />{t("app.producao.ideias_no_quadro")}<a className="bt pequeno" href={antiga.ideias(canal)}>{t("app.producao.abrir_quadro")}</a></div>
      ) : lista.length ? (
        <div className="videos">{lista.map((v, i) => <CartaoVideo key={v.slug} canal={canal} v={v} atraso={i * 40} />)}</div>
      ) : (
        <div className="vazio"><Clapperboard size={18} />{t("app.producao.nada_nesta_etapa")}</div>
      )}
    </section>
  );
}

function Semana({ dados }: { dados: PainelCanal }) {
  const t = useT();
  const hoje = new Date();
  const dias = Array.from({ length: 7 }, (_, i) => new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() + i));
  const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const nomes = t("app.dias_curtos").split(",");
  return (
    <>
      <div className="dias">
        {dias.map((d, i) => {
          const tem = dados.publicacoes.some((p) => p.data === iso(d));
          return (
            <div key={i} className={`dia ${i === 0 ? "hoje" : ""} ${tem ? "tem" : ""}`}>
              {nomes[d.getDay()]}<b>{d.getDate()}</b>
            </div>
          );
        })}
      </div>
      {dados.publicacoes.length ? (
        <div className="pubs">
          {dados.publicacoes.slice(0, 4).map((p) => (
            <Link key={p.video} className="pub" to={rota.video(dados.canal.slug, p.video)}>
              <span className="data">{p.data.slice(8, 10)}/{p.data.slice(5, 7)}</span>
              <span className="tit">{p.titulo}</span>
              <span className={`selo ${p.coluna === "publicado" ? "ok" : p.coluna === "agendado" ? "run" : "neutro"}`}>{t(`app.coluna.${p.coluna}`)}</span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="vazio"><CalendarPlus size={18} />
          {t("app.producao.sem_datas", { n: dados.canal.colunas.edicao_final })}
        </div>
      )}
    </>
  );
}

export function ProducaoCanal() {
  const { canal = "" } = useParams();
  const { data } = useCanal(canal);
  const t = useT();
  const qc = useQueryClient();
  const parar = useMutation({
    mutationFn: (url: string) => enviar(url),
    onSettled: () => qc.invalidateQueries({ queryKey: ["canal", canal] }),
  });
  if (!data) return null;
  const c = data.canal;

  return (
    <>
      <Cabecalho onde={<>{c.nome} › <b>{t("app.nav.producao")}</b></>} titulo={saudacao(t)} />

      <div className="g1">
        <Heroi canal={canal} v={data.destaque} />
        <div>
          <div className="titulo-secao">
            <h3>{t("app.esperando_voce_titulo")}{data.esperando.length > 0 && <span className="contador">{data.esperando.length}</span>}</h3>
            {data.esperando.length > 3 && <Link to={`/c/${canal}/esperando`}>{t("app.ver_tudo")}</Link>}
          </div>
          {data.esperando.length ? (
            <div className="espera">{data.esperando.slice(0, 3).map((e) => <ItemEsperando key={e.video + e.nn} canal={canal} e={e} />)}</div>
          ) : (
            <div className="nada-espera">
              <span className="ic"><CircleCheck size={22} /></span>
              <b>{t("app.esperando.nada")}</b>
              <span className="sub">{t("app.esperando.nada_sub")}</span>
            </div>
          )}
        </div>
      </div>

      <Processo canal={canal} dados={data} />

      <div className="g3">
        <div className="cartao">
          <div className="titulo-secao"><h3>{t("app.rodando.titulo")}</h3></div>
          {data.rodando.length ? (
            <div className="fila">
              {data.rodando.map((r) => (
                <LinhaRodando key={r.video + r.nn} canal={canal} r={r}
                              parar={() => parar.mutate(`/api/c/${canal}/v/${r.video}/b/${r.nn}/parar`)} />
              ))}
            </div>
          ) : (
            <div className="vazio"><Sparkles size={18} />{t("app.rodando.nada")}</div>
          )}
          {data.filas.map((f) => (
            <div className="resumo-fila" key={f.video}>
              <ListOrdered size={16} />
              <span>
                <b>{t("app.fila.na_fila", { n: f.esperando?.length ?? 0 })}</b> · {t("app.fila.max", { n: f.max })}
                {f.parados?.length ? ` · ${t("app.esperando_n", { n: f.parados.length })}` : ""}
                {data.filas.length > 1 && <> · {f.video_titulo}</>}
                {f.status === "pausada" && f.motivo && <em> · {f.motivo}</em>}
              </span>
              <button onClick={() => parar.mutate(`/api/c/${canal}/v/${f.video}/fila/parar`)}>{t("app.fila.parar")}</button>
            </div>
          ))}
        </div>
        <div className="cartao">
          <div className="titulo-secao"><h3>{t("app.producao.publicacoes")}</h3><a href={antiga.calendario(canal)}>{t("app.nav.calendario")}</a></div>
          <Semana dados={data} />
        </div>
        <div className="cartao">
          <div className="titulo-secao"><h3>{t("app.producao.claude_7d")}</h3><a href={antiga.consumo}>{t("app.produtor.consumo")}</a></div>
          <AnelConsumo total={data.consumo_7d.total} etapas={data.consumo_7d.etapas} />
        </div>
      </div>
    </>
  );
}
