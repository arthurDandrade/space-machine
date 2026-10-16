// Página de um vídeo: capa e andamento, a fila (produzir todos / parar), os blocos em grade e a publicação.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Clapperboard, Copy, ExternalLink, Film, FolderOpen, ImagePlus, Layers, Loader, Play, Save, Trash2, Wand2 } from "lucide-react";
import { BlocoDoVideo, DetalheVideo, enviar, pegar, Publicacao, rota, urlCapa } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { Dialogo } from "../componentes/Dialogo";
import { copiarTexto, TituloCopiavel } from "../componentes/Copiar";
import { Capa } from "../componentes/Imagens";
import { BarraThumb, soltarArquivo, useSoltar, useThumbnail } from "../componentes/Thumbnail";
import { compacto, haQuanto, useT } from "../textos";

export const useVideo = (canal: string, video: string) =>
  useQuery({ queryKey: ["video", canal, video], queryFn: () => pegar<DetalheVideo>(`/api/c/${canal}/v/${video}`) });

// etapas que aparecem na barra do card (o roteiro existe desde que o vídeo foi criado)
const BARRA = ["narracao", "transcricao", "storyboard", "busca", "escolha", "edicao", "aprovado", "entregue"];
type Filtro = "todos" | "run" | "fila" | "wait" | "ok" | "afazer";

function CartaoBloco({ canal, video, b, rotulos, atraso }: { canal: string; video: string; b: BlocoDoVideo; rotulos: Record<string, string>; atraso: number }) {
  const t = useT();
  const qc = useQueryClient();
  // produzir sem entrar no bloco: o mesmo "Rodar" da página do bloco (cada etapa pula o que já está feito)
  const produzir = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${video}/b/${b.nn}/rodar`, {}),
    onSettled: () => qc.invalidateQueries(),
  });
  const podeProduzir = b.estado === "todo" || b.estado === "meio";
  const comecando = produzir.isPending || produzir.isSuccess;
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
        {podeProduzir && (
          <button className="produzir-bloco" disabled={comecando}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); produzir.mutate(); }}>
            {comecando ? <Loader size={14} className="gira" /> : <Play size={14} />}
            {t(comecando ? "app.bloco.comecando" : b.estado === "meio" ? "app.bloco.continuar" : "app.bloco.produzir")}
          </button>
        )}
        {produzir.isError && <span className="erro-barra" onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>{produzir.error.message}</span>}
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
  // Gerar: resumo (Claude) + capítulos do vídeo final + convite para seguir; vai para o campo, quem salva é o Salvar
  const gerar = useMutation({
    mutationFn: () => enviar<{ descricao: string; avisos: string[] }>(`/api/c/${canal}/v/${v.slug}/descricao/gerar`),
    onSuccess: (r) => setForm((f) => ({ ...f, descricao: r.descricao })),
  });
  const [copiado, setCopiado] = useState(false);
  const copiar = async () => {
    await copiarTexto(form.descricao || "");
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1300);
  };
  return (
    <form className="cartao form-pub" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
      <div className="duas-col">
        <div>
          <label className="campo">{t("app.pub.titulo")}<input {...campo("titulo_pub")} placeholder={v.titulo} /></label>
          <div className="campo">
            <div className="rotulo-acoes">
              <label htmlFor="pub-descricao">{t("app.pub.descricao")}</label>
              <button type="button" className="bt pequeno" disabled={gerar.isPending} onClick={() => gerar.mutate()} title={t("app.pub.gerar_dica")}>
                {gerar.isPending ? <Loader size={14} className="gira" /> : <Wand2 size={14} />}{gerar.isPending ? t("app.regras.perguntando") : t("app.pub.gerar")}
              </button>
              <button type="button" className="bt pequeno" disabled={!form.descricao} onClick={copiar}>
                {copiado ? <Check size={14} /> : <Copy size={14} />}{copiado ? t("app.copiar.feito") : t("app.pub.copiar")}
              </button>
            </div>
            <textarea id="pub-descricao" rows={gerar.isSuccess ? 14 : 7} {...campo("descricao")} />
            {gerar.isError && <span className="erro">{gerar.error.message}</span>}
            {gerar.data?.avisos.map((a) => <span key={a} className="aviso-fila">{a}</span>)}
            {gerar.isSuccess && <span className="sub">{t("app.pub.gerada")}</span>}
          </div>
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

// ---------------- thumbnail ----------------
// a capa grande da página do vídeo também recebe a thumbnail: clicar, arrastar ou colar (⌘V) em qualquer lugar da página
function CapaVideo({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const { enviar, enviando, erro } = useThumbnail(canal, v.slug);
  const soltar = useSoltar(enviar);
  const capa = urlCapa(canal, v.slug, undefined, v.capa_v);
  useEffect(() => {
    const colar = (e: ClipboardEvent) => {
      if ((e.target as HTMLElement)?.closest?.("input, textarea, [contenteditable]")) return;
      const f = [...(e.clipboardData?.files ?? [])].find((x) => x.type.startsWith("image/"));
      if (f) { e.preventDefault(); enviar(f); }
    };
    window.addEventListener("paste", colar);
    return () => window.removeEventListener("paste", colar);
  }, [enviar]);
  return (
    <div className={`capa-video ${soltar.sobre ? "sobre" : ""}`} {...soltar.props}>
      <Capa className="capa-grande" src={capa} existe={v.tem_capa} />
      <span className="origem-capa">{enviando ? <><Loader size={12} className="gira" /> {t("app.enviando")}</> : t(v.thumbnail ? "app.thumb.e_thumb" : "app.thumb.e_quadro")}</span>
      <BarraThumb canal={canal} video={v.slug} thumb={v.thumb} capa={capa} />
      <span className="dica-capa">{t("app.thumb.dica")}</span>
      {erro && <p className="erro erro-capa">{erro}</p>}
    </div>
  );
}

function CampoThumbnail({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const { enviar, remover, enviando, erro } = useThumbnail(canal, v.slug);
  const campo = useRef<HTMLInputElement>(null);
  const th = v.thumbnail;
  const avisos = th ? [
    th.grande_demais && t("app.thumb.aviso_tamanho", { mb: (th.tamanho / 1048576).toFixed(1).replace(".", ",") }),
    th.largura && th.altura && Math.abs(th.largura / th.altura - 16 / 9) > 0.02 && t("app.thumb.aviso_proporcao", { l: th.largura, a: th.altura }),
    th.largura && th.largura < 1280 && t("app.thumb.aviso_pequena", { l: th.largura }),
  ].filter(Boolean) as string[] : [];
  return (
    <div className="cartao campo-thumb" onDragOver={(e) => e.preventDefault()} onDrop={(e) => soltarArquivo(e, enviar)}>
      <div className="titulo-secao"><h3>{t("app.thumb.titulo")}</h3>{th && <span className="sub">{t("app.thumb.enviada", { quando: th.enviada || "" })}</span>}</div>
      <div className="thumb-linha">
        <button type="button" className={`thumb-previa ${th ? "" : "vazia"}`} onClick={() => campo.current?.click()}>
          {th ? <img src={th.url} alt="" /> : <span><ImagePlus size={22} />{t("app.thumb.enviar")}</span>}
        </button>
        <div className="thumb-info">
          {th ? (
            <>
              <b>{th.nome}</b>
              <span className="sub">{[th.largura && `${th.largura}×${th.altura}`, `${(th.tamanho / 1048576).toFixed(1).replace(".", ",")} MB`].filter(Boolean).join(" · ")}</span>
              {avisos.map((a) => <span key={a} className="aviso-thumb"><AlertTriangle size={13} />{a}</span>)}
              {!avisos.length && <span className="selo ok"><Check size={12} />{t("app.thumb.ok_youtube")}</span>}
            </>
          ) : (
            <span className="sub">{t("app.thumb.vazia")}</span>
          )}
          <div className="acoes-final">
            <button type="button" className="bt pequeno primario" disabled={enviando} onClick={() => campo.current?.click()}>
              <ImagePlus size={14} />{t(enviando ? "app.enviando" : th ? "app.thumb.trocar" : "app.thumb.enviar")}
            </button>
            {th && <a className="bt pequeno" href={th.url} target="_blank" rel="noreferrer"><ExternalLink size={14} />{t("app.thumb.abrir")}</a>}
            {th && <button type="button" className="bt pequeno perigo" onClick={remover}><Trash2 size={14} />{t("app.thumb.remover")}</button>}
          </div>
          {erro && <span className="erro">{erro}</span>}
        </div>
      </div>
      <input ref={campo} type="file" accept="image/png,image/jpeg,image/webp" hidden
             onChange={(e) => { const f = e.target.files?.[0]; if (f) enviar(f); e.target.value = ""; }} />
    </div>
  );
}

function VideoFinal({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const [aberto, setAberto] = useState(false);
  const [render, setRender] = useState(false);
  const f = v.final;
  const juntar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${v.slug}/final`, { render }),
    onSuccess: () => { setAberto(false); qc.invalidateQueries(); },
  });
  if (!f.entregues) return null;
  const faltam = v.n_blocos - f.entregues;
  const gb = (n: number) => (n / 1e9).toFixed(1).replace(".", ",");
  return (
    <div className="final-card">
      <div className="linha-fila">
        <div className="t-final"><Layers size={16} /><b>{t("app.final.titulo")}</b>
          {f.rodando ? <span className="selo run"><Loader size={12} className="gira" />{t("app.final.rodando")}</span>
            : f.status === "ok" ? <span className="selo ok"><Check size={12} />{t("app.final.pronto")}</span>
            : f.status === "erro" ? <span className="selo bad">{t("app.final.erro")}</span> : null}
        </div>
        <button className={`bt pequeno ${faltam ? "" : "primario"}`} disabled={f.rodando} onClick={() => setAberto(true)}>
          <Layers size={14} />{t(f.tem_aep ? "app.final.juntar_de_novo" : "app.final.juntar")}
        </button>
      </div>
      {f.rodando && <p className="sub">{f.etapa}</p>}
      {f.status === "erro" && !f.rodando && <p className="erro">{f.etapa}{f.erro ? `: ${f.erro}` : ""}</p>}
      {!f.rodando && (f.tem_aep || f.mp4_url) && (
        <div className="acoes-final">
          {f.tem_aep && <button className="bt pequeno" onClick={() => enviar(`/api/c/${canal}/v/${v.slug}/final/abrir`)}><Film size={14} />{t("app.final.abrir_after")}</button>}
          {f.mp4_url && <a className="bt pequeno" href={f.mp4_url} target="_blank" rel="noreferrer"><Play size={14} />{t("app.final.assistir", { gb: gb(f.mp4_tamanho) })}</a>}
          <button className="bt pequeno" onClick={() => enviar(`/api/c/${canal}/v/${v.slug}/abrir`, { sub: "final" })}><FolderOpen size={14} />{t("app.final.pasta")}</button>
        </div>
      )}
      {aberto && (
        <Dialogo titulo={t("app.final.dialogo_titulo")} fechar={() => setAberto(false)}
          acoes={<>
            <button className="bt" onClick={() => setAberto(false)}>{t("app.cancelar")}</button>
            <button className="bt primario" disabled={juntar.isPending} onClick={() => juntar.mutate()}><Layers size={16} />{t(render ? "app.final.confirmar_render" : "app.final.confirmar")}</button>
          </>}>
          <p>{t("app.final.explica", { n: f.entregues })}</p>
          {faltam > 0 && <p className="aviso-texto">{t("app.final.faltam", { n: faltam })}</p>}
          <p>{t("app.final.aviso_after")}</p>
          <label className="marcar"><input type="checkbox" checked={render} onChange={(e) => setRender(e.target.checked)} /> {t("app.final.render")}</label>
          {juntar.isError && <p className="erro">{juntar.error.message}</p>}
        </Dialogo>
      )}
    </div>
  );
}

function ExcluirVideo({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const navegar = useNavigate();
  const [aberto, setAberto] = useState(false);
  const excluir = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/v/${v.slug}/excluir`),
    onSuccess: () => { qc.invalidateQueries(); navegar(`/c/${canal}/videos`); },
  });
  return (
    <>
      <button className="bt redondo perigo" onClick={() => setAberto(true)} title={t("app.excluir.botao")}><Trash2 size={16} /></button>
      {aberto && (
        <Dialogo titulo={t("app.excluir.titulo", { titulo: v.titulo_pub || v.titulo })} fechar={() => setAberto(false)}
          acoes={<>
            <button className="bt" onClick={() => setAberto(false)}>{t("app.cancelar")}</button>
            <button className="bt perigo-cheio" disabled={excluir.isPending} onClick={() => excluir.mutate()}><Trash2 size={16} />{t("app.excluir.confirmar")}</button>
          </>}>
          <p>{t("app.excluir.explica", { n: v.n_blocos })}</p>
          {excluir.isError && <p className="erro">{excluir.error.message}</p>}
        </Dialogo>
      )}
    </>
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
        titulo={<TituloCopiavel texto={v.titulo_pub || v.titulo} />}>
        <button className="bt" onClick={abrir} title={t("app.abrir_pasta_dica")}><FolderOpen size={16} />{t("app.abrir_pasta")}</button>
        <ExcluirVideo canal={canal} v={v} />
      </Cabecalho>

      <div className="video-topo">
        <CapaVideo canal={canal} v={v} />
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
          <VideoFinal canal={canal} v={v} />
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
        <>
          <CampoThumbnail canal={canal} v={v} />
          <FormPublicacao canal={canal} v={v} />
        </>
      )}
    </>
  );
}
