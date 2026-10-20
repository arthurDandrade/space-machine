// Telas de lista do canal: todos os vídeos (com busca por título) e tudo o que espera você.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Plus, RotateCcw, Search, Trash2 } from "lucide-react";
import { Coluna, enviar, pegar, rota } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { CartaoVideo, ItemEsperando } from "../componentes/Pecas";
import { useT } from "../textos";

type Excluido = {
  nome: string; tipo: "video" | "bloco"; video: string; nn: string; titulo: string; video_titulo: string;
  n_blocos: number; excluido: string; pode_restaurar: boolean;
};

function Lixeira({ canal }: { canal: string }) {
  const t = useT();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["lixeira", canal], queryFn: () => pegar<{ itens: Excluido[] }>(`/api/c/${canal}/lixeira`) });
  const restaurar = useMutation({
    mutationFn: (nome: string) => enviar(`/api/c/${canal}/lixeira/${encodeURIComponent(nome)}/restaurar`),
    onSettled: () => qc.invalidateQueries(),
  });
  if (!data?.itens.length) return null;
  return (
    <details className="cartao recolhe lixeira">
      <summary><h3><Trash2 size={15} /> {t("app.lixeira.titulo")}</h3><span className="sub">{t("app.lixeira.n", { n: data.itens.length })}</span></summary>
      <p className="sub">{t("app.lixeira.explica")}</p>
      <div className="lista-lixeira">
        {data.itens.map((x) => (
          <div key={x.nome} className="item-lixeira">
            <div className="t">
              <b>{x.titulo}</b>
              <span className="sub">
                {x.tipo === "bloco"
                  ? t("app.lixeira.detalhe_bloco", { nn: x.nn, video: x.video_titulo, quando: x.excluido })
                  : t("app.lixeira.detalhe", { n: x.n_blocos, quando: x.excluido })}
                {!x.pode_restaurar && ` · ${t("app.lixeira.sem_video")}`}
              </span>
            </div>
            <button className="bt pequeno" disabled={restaurar.isPending || !x.pode_restaurar} onClick={() => restaurar.mutate(x.nome)}><RotateCcw size={14} />{t("app.lixeira.restaurar")}</button>
          </div>
        ))}
      </div>
      {restaurar.isError && <p className="erro">{restaurar.error.message}</p>}
    </details>
  );
}

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
        <Link className="bt primario" to={rota.novoVideo(canal)}><Plus size={18} />{t("app.novo_video")}</Link>
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
      <Lixeira canal={canal} />
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
