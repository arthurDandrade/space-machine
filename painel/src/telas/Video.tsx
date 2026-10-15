// Página de um vídeo: capa e andamento, a fila (produzir todos / parar), os blocos em grade e a publicação.
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clapperboard, FolderOpen, Play, Save } from "lucide-react";
import { BlocoDoVideo, DetalheVideo, enviar, pegar, Publicacao, rota, urlCapa } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { Capa } from "../componentes/Imagens";
import { compacto, haQuanto, useT } from "../textos";

export const useVideo = (canal: string, video: string) =>
  useQuery({ queryKey: ["video", canal, video], queryFn: () => pegar<DetalheVideo>(`/api/c/${canal}/v/${video}`) });

// etapas que aparecem na barra do card (o roteiro existe desde que o vídeo foi criado)
const BARRA = ["narracao", "transcricao", "storyboard", "busca", "escolha", "edicao", "aprovado", "entregue"];
type Filtro = "todos" | "run" | "fila" | "wait" | "ok" | "afazer";

function CartaoBloco({ canal, video, b, rotulos, atraso }: { canal: string; video: string; b: BlocoDoVideo; rotulos: Record<string, string>; atraso: number }) {
  const t = useT();
  const selo =
    b.estado === "run" ? <span className="selo run"><span className="pulso" />{t("app.estado.run")}</span>
    : b.estado === "fila" ? <span className="selo neutro">{t("app.bloco.na_fila")}</span>
    : b.estado === "wait" ? <span className="selo wait" title={b.parado?.motivo}>{t("app.bloco.parado_em", { etapa: t(`app.etapa.${b.parado?.etapa}`, undefined, b.parado?.etapa || "") })}</span>
    : b.estado === "ok" ? <span className="selo ok"><Check size={12} />{t("app.estado.ok")}</span>
    : null;
  return (
    <Link className="bloco-card" to={rota.bloco(canal, video, b.nn)} style={{ animationDelay: `${atraso}ms` }}>
      <div className="cv">
        <Capa src={urlCapa(canal, video, b.nn)} existe={b.tem_capa} vazio={<span className="sem-capa"><Clapperboard size={26} /></span>} />
        <span className="nn">{b.nn}</span>
      </div>
      <div className="info">
        <b>{b.topico}</b>
        <span className="sub">{rotulos[b.atual] ?? b.atual}{b.assets_total ? ` · ${t("app.bloco.assets", { p: b.assets_prontos, n: b.assets_total })}` : ""}</span>
        <div className="segmentos">{BARRA.map((e) => <i key={e} className={b.feito[e] ? "ok" : ""} title={rotulos[e]} />)}</div>
        <div className="selos">
          {selo}
          {b.conferir > 0 && b.estado !== "wait" && <span className="selo neutro">{t("app.bloco.conferir_n", { n: b.conferir })}</span>}
        </div>
      </div>
    </Link>
  );
}

function ControleFila({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const [maximo, setMaximo] = useState(3);
  const base = `/api/c/${canal}/v/${v.slug}/fila`;
  const acao = useMutation({
    mutationFn: (url: string) => enviar(url, { maximo }),
    onSettled: () => qc.invalidateQueries(),
  });
  const f = v.fila;
  const faltam = v.n_blocos - v.entregues - v.esperando - v.rodando;
  if (f?.ativa)
    return (
      <div className="fila-card ativa">
        <div className="linha-fila">
          <span className={`selo ${f.status === "pausada" ? "wait" : "run"}`}><span className="pulso" />{t(f.status === "pausada" ? "app.fila.pausada" : "app.fila.ativa")}</span>
          <button className="bt pequeno perigo" disabled={acao.isPending} onClick={() => acao.mutate(`${base}/parar`)}>{t("app.fila.parar")}</button>
        </div>
        <p className="sub">
          {t("app.fila.rodando_agora", { lista: f.rodando?.join(", ") || "—" })} · {t("app.fila.na_fila", { n: f.esperando?.length ?? 0 })} · {t("app.fila.max", { n: f.max })}
          {f.parados?.length ? ` · ${t("app.fila.esperando_voce", { lista: f.parados.join(", ") })}` : ""}
        </p>
        {f.status === "pausada" && f.motivo && <p className="aviso-fila">{f.motivo}</p>}
      </div>
    );
  return (
    <div className="fila-card">
      <div className="linha-fila">
        <button className="bt primario" disabled={acao.isPending || faltam <= 0} onClick={() => acao.mutate(base)}>
          <Play size={16} />{faltam > 0 ? t("app.fila.produzir_n", { n: faltam }) : t("app.fila.nada_a_produzir")}
        </button>
        <label className="sub">{t("app.fila.ate")}{" "}
          <select value={maximo} onChange={(e) => setMaximo(Number(e.target.value))}>
            {[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}
          </select>{" "}{t("app.fila.por_vez")}
        </label>
      </div>
      <p className="sub">{t("app.fila.explica")}</p>
      {f?.status && <p className="sub ultima">{t("app.fila.ultima", { status: f.status })}{f.motivo ? ` · ${f.motivo}` : ""}</p>}
      {acao.isError && <p className="erro">{acao.error.message}</p>}
    </div>
  );
}

function FormPublicacao({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const [form, setForm] = useState<Publicacao>(v.publicacao);
  useEffect(() => setForm(v.publicacao), [v.publicacao.atualizado]); // eslint-disable-line react-hooks/exhaustive-deps
  const salvar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${v.slug}/publicacao`, form),
    onSuccess: () => qc.invalidateQueries(),
  });
  const campo = (k: keyof Publicacao) => ({ value: form[k] ?? "", onChange: (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value }) });
  return (
    <form className="cartao form-pub" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
      <div className="duas-col">
        <div>
          <label className="campo">{t("app.pub.titulo")}<input {...campo("titulo_pub")} placeholder={v.titulo} /></label>
          <label className="campo">{t("app.pub.descricao")}<textarea rows={7} {...campo("descricao")} /></label>
          <label className="campo">{t("app.pub.tags")}<input {...campo("tags")} /></label>
        </div>
        <div>
          <label className="campo">{t("app.pub.status")}
            <select {...campo("status")}>
              <option value="">{t("app.pub.automatico")}</option>
              <option value="edicao_final">{t("app.coluna.edicao_final")}</option>
              <option value="agendado">{t("app.coluna.agendado")}</option>
              <option value="publicado">{t("app.coluna.publicado")}</option>
            </select>
          </label>
          <label className="campo">{t("app.pub.data")}<input type="date" {...campo("data_pub")} value={(form.data_pub || "").slice(0, 10)} /></label>
          <label className="campo">{t("app.pub.link")}<input {...campo("link")} placeholder="https://youtu.be/..." /></label>
          <label className="campo">{t("app.pub.notas")}<textarea rows={3} {...campo("notas")} /></label>
        </div>
      </div>
      <div className="rodape-form">
        <button className="bt primario" disabled={salvar.isPending}><Save size={16} />{t("comum.salvar")}</button>
        {salvar.isSuccess && <span className="selo ok"><Check size={12} />{t("app.salvo")}</span>}
        {salvar.isError && <span className="erro">{salvar.error.message}</span>}
        {v.publicacao.atualizado && <span className="sub">{t("app.pub.salvo_em", { quando: v.publicacao.atualizado })}</span>}
      </div>
    </form>
  );
}

export function VideoTela() {
  const { canal = "", video = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data: v, error } = useVideo(canal, video);
  const t = useT();
  const [params, setParams] = useSearchParams();
  const aba = params.get("aba") === "publicacao" ? "publicacao" : "blocos";
  const [filtro, setFiltro] = useState<Filtro>("todos");
  if (error) throw error;
  if (!v || !dc) return <div className="carregando">{t("app.carregando")}</div>;

  const rotulos = Object.fromEntries(v.etapas.map((e) => [e.id, e.rotulo]));
  const conta = (f: Filtro) => v.blocos.filter((b) => passa(b, f)).length;
  const passa = (b: BlocoDoVideo, f: Filtro) =>
    f === "todos" || (f === "afazer" ? b.estado === "todo" || b.estado === "meio" : b.estado === f);
  const filtros: Filtro[] = ["todos", "run", "fila", "wait", "ok", "afazer"];
  const pct = v.n_blocos ? Math.round((100 * v.entregues) / v.n_blocos) : 0;
  const abrir = () => enviar(`/api/c/${canal}/v/${video}/abrir`, {});

  return (
    <>
      <Cabecalho
        onde={<><Link to={rota.canal(canal)}>{dc.canal.nome}</Link> › <Link to={`/c/${canal}/videos`}>{t("app.nav.videos")}</Link> › <b>{t(`app.coluna.${v.coluna}`)}</b></>}
        titulo={v.titulo_pub || v.titulo}>
        <button className="bt" onClick={abrir} title={t("app.abrir_pasta_dica")}><FolderOpen size={16} />{t("app.abrir_pasta")}</button>
      </Cabecalho>

      <div className="video-topo">
        <Capa className="capa-grande" src={urlCapa(canal, video)} existe={v.tem_capa} />
        <div className="andamento cartao">
          <div className="pct"><b>{pct}%</b><span>{t("app.video.blocos_entregues", { e: v.entregues, n: v.n_blocos })}</span></div>
          <div className="segmentos grossos">{v.blocos.map((b) => <i key={b.nn} className={b.estado} title={`${b.nn} · ${b.topico}`} />)}</div>
          <div className="selos">
            {v.rodando > 0 && <span className="selo run"><span className="pulso" />{t("app.n_rodando", { n: v.rodando })}</span>}
            {v.na_fila > 0 && <span className="selo neutro">{t("app.n_na_fila", { n: v.na_fila })}</span>}
            {v.esperando > 0 && <span className="selo wait">{t("app.esperando_n", { n: v.esperando })}</span>}
          </div>
          <p className="sub">
            {t("app.video.claude", { n: v.consumo_detalhe.chamadas ?? 0, tokens: compacto(v.consumo_detalhe.equivalente ?? 0) })}
            {" · "}{t("app.video.mexido", { quando: haQuanto(t, v.mudou) })}
          </p>
          <ControleFila canal={canal} v={v} />
        </div>
      </div>

      <div className="abas">
        <button className={aba === "blocos" ? "on" : ""} onClick={() => setParams({})}>{t("app.video.aba_blocos")} <span>{v.n_blocos}</span></button>
        <button className={aba === "publicacao" ? "on" : ""} onClick={() => setParams({ aba: "publicacao" })}>{t("app.video.aba_publicacao")}</button>
      </div>

      {aba === "blocos" ? (
        <>
          <div className="pilulas" style={{ marginBottom: 16 }}>
            {filtros.map((f) => {
              const n = conta(f);
              if (f !== "todos" && !n) return null;
              return <button key={f} className={filtro === f ? "on" : ""} onClick={() => setFiltro(f)}>{t(`app.video.filtro_${f}`)} <span>{n}</span></button>;
            })}
          </div>
          <div className="blocos-grade">
            {v.blocos.filter((b) => passa(b, filtro)).map((b, i) => (
              <CartaoBloco key={b.nn} canal={canal} video={video} b={b} rotulos={rotulos} atraso={Math.min(i, 12) * 25} />
            ))}
          </div>
        </>
      ) : (
        <FormPublicacao canal={canal} v={v} />
      )}
    </>
  );
}
