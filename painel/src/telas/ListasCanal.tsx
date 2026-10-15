// Telas de lista do canal: todos os vídeos (com busca por título) e tudo o que espera você.
import { useState } from "react";
import { useParams } from "react-router-dom";
import { CircleCheck, Plus, Search } from "lucide-react";
import { antiga, Coluna } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { CartaoVideo, ItemEsperando } from "../componentes/Pecas";
import { useT } from "../textos";

export function VideosCanal() {
  const { canal = "" } = useParams();
  const { data } = useCanal(canal);
  const t = useT();
  const [busca, setBusca] = useState("");
  const [coluna, setColuna] = useState<Coluna | "">("");
  if (!data) return null;
  const termo = busca.trim().toLowerCase();
  const lista = data.videos.filter(
    (v) => (!coluna || v.coluna === coluna) && (!termo || `${v.titulo} ${v.titulo_pub}`.toLowerCase().includes(termo)),
  );
  return (
    <>
      <Cabecalho onde={<>{data.canal.nome} › <b>{t("app.nav.videos")}</b></>} titulo={t("app.videos.titulo", { n: data.videos.length })}>
        <a className="bt primario" href={antiga.novoVideo(canal)}><Plus size={18} />{t("app.novo_video")}</a>
      </Cabecalho>
      <div className="barra-filtros">
        <label className="campo-busca"><Search size={16} />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder={t("app.videos.buscar")} />
        </label>
        <div className="pilulas">
          <button className={coluna === "" ? "on" : ""} onClick={() => setColuna("")}>{t("app.videos.todos")}</button>
          {data.colunas.filter((c) => c.id !== "ideia" && c.n > 0).map((c) => (
            <button key={c.id} className={coluna === c.id ? "on" : ""} onClick={() => setColuna(c.id)}>
              {t(`app.coluna.${c.id}`)} <span>{c.n}</span>
            </button>
          ))}
        </div>
      </div>
      {lista.length ? (
        <div className="videos">{lista.map((v, i) => <CartaoVideo key={v.slug} canal={canal} v={v} atraso={i * 30} />)}</div>
      ) : (
        <div className="vazio">{t("app.videos.nenhum")}</div>
      )}
    </>
  );
}

export function EsperandoCanal() {
  const { canal = "" } = useParams();
  const { data } = useCanal(canal);
  const t = useT();
  if (!data) return null;
  return (
    <>
      <Cabecalho onde={<>{data.canal.nome} › <b>{t("app.nav.esperando")}</b></>} titulo={t("app.esperando_voce_titulo")} />
      <p className="sub intro">{t("app.esperando.explica")}</p>
      {data.esperando.length ? (
        <div className="espera larga">{data.esperando.map((e) => <ItemEsperando key={e.video + e.nn} canal={canal} e={e} />)}</div>
      ) : (
        <div className="nada-espera grande">
          <span className="ic"><CircleCheck size={26} /></span>
          <b>{t("app.esperando.nada")}</b>
          <span className="sub">{t("app.esperando.nada_sub")}</span>
        </div>
      )}
    </>
  );
}
