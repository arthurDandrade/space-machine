// Mineração: área própria do produtor. Você escreve o nicho, o Claude monta as buscas e o garimpo devolve uma
// grade dos VÍDEOS que estouraram (space_machine/mineracao.py, pela API oficial do YouTube). O canal que te
// interessar vai para a Modelagem num clique. Nada abre nem baixa vídeo: os links são links comuns, que só vão
// ao YouTube quando VOCÊ clica; a thumbnail é a imagem que a própria API devolveu, guardada no cache.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink, KeyRound, Pickaxe, Play, RefreshCw, Sparkles, Target, Trash2, Undo2, X,
} from "lucide-react";
import {
  EstadoMina, FiltrosMina, Nicho, VideoMinerado, enviar, pegar, urlLogoMinerado, urlThumbMinerada,
} from "../api";
import { CabecaTela, TopoProdutor } from "../casca/TopoProdutor";
import { compacto, useT } from "../textos";

type Aba = "novo" | "descartado" | "modelo";
const CHAVE = ["mineracao"];

function Thumb({ v }: { v: VideoMinerado }) {
  const t = useT();
  const [falhou, setFalhou] = useState(false);
  return (
    <a className="thumb-mina" href={v.video_url} target="_blank" rel="noreferrer noopener" title={t("app.mina.abrir_video")}>
      {v.tem_thumb && !falhou
        ? <img src={urlThumbMinerada(v.id)} alt="" loading="lazy" onError={() => setFalhou(true)} />
        : <span className="sem"><Play size={22} /></span>}
      <span className="x-vezes" title={t("app.mina.nota_de", { n: Math.round(v.nota), vistas: compacto(v.vistas_dia), termo: v.termo })}>
        {v.surto >= 10 ? Math.round(v.surto) : v.surto}x
      </span>
      <span className="views">{compacto(v.vistas)}</span>
    </a>
  );
}

function CartaoVideoMinerado({ v, aba }: { v: VideoMinerado; aba: Aba }) {
  const t = useT();
  const qc = useQueryClient();
  const [notas, setNotas] = useState(v.notas);
  const [logoRuim, setLogoRuim] = useState(false);
  const recarregar = () => qc.invalidateQueries({ queryKey: CHAVE });
  const salvarNotas = useMutation({ mutationFn: (texto: string) => enviar(`/api/mineracao/${v.id}/notas`, { notas: texto }) });
  const modelar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${v.id}/modelar`), onSettled: recarregar });
  const descartar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${v.id}/descartar`), onSettled: recarregar });
  const voltar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${v.id}/voltar`), onSettled: recarregar });
  const excluir = useMutation({ mutationFn: () => enviar(`/api/mineracao/${v.id}/excluir`), onSettled: recarregar });
  // guarda sozinho um instante depois de você parar de escrever
  useEffect(() => {
    if (notas === v.notas) return;
    const id = setTimeout(() => salvarNotas.mutate(notas), 800);
    return () => clearTimeout(id);
  }, [notas, v.notas]);

  return (
    <div className="achado">
      <Thumb v={v} />
      <div className="corpo">
        <a className="titulo" href={v.video_url} target="_blank" rel="noreferrer noopener">{v.titulo}</a>
        <a className="dono" href={v.canal_url} target="_blank" rel="noreferrer noopener" title={t("app.mina.abrir_canal")}>
          {v.tem_logo && !logoRuim
            ? <img src={urlLogoMinerado(v.id)} alt="" loading="lazy" onError={() => setLogoRuim(true)} />
            : <span className="ini">{v.canal_nome.slice(0, 1).toUpperCase()}</span>}
          <span className="t">
            <b>{v.canal_nome}</b>
            <span className="sub">{t("app.mina.canal_sub", { inscritos: compacto(v.inscritos), meses: String(v.meses).replace(".", ",") })}</span>
          </span>
        </a>
        <textarea className="notas" rows={1} value={notas} placeholder={t("app.mina.notas_dica")}
                  onChange={(e) => setNotas(e.target.value)} />
        {modelar.isError && <p className="erro">{modelar.error.message}</p>}
        <div className="acoes">
          {aba === "novo" ? (
            <>
              <button className="bt pequeno primario" disabled={modelar.isPending} onClick={() => modelar.mutate()}>
                <Target size={14} />{t(modelar.isPending ? "app.mina.modelando" : "app.mina.modelar")}
              </button>
              <a className="bt pequeno so-icone" href={v.canal_url} target="_blank" rel="noreferrer noopener"
                 title={t("app.mina.abrir_canal")}><ExternalLink size={14} /></a>
              <button className="bt pequeno so-icone fim" title={t("app.mina.descartar")}
                      disabled={descartar.isPending} onClick={() => descartar.mutate()}><X size={15} /></button>
            </>
          ) : (
            <>
              {aba === "descartado" && (
                <button className="bt pequeno" disabled={voltar.isPending} onClick={() => voltar.mutate()}>
                  <Undo2 size={14} />{t("app.mina.voltar")}
                </button>
              )}
              <a className="bt pequeno so-icone" href={v.canal_url} target="_blank" rel="noreferrer noopener"
                 title={t("app.mina.abrir_canal")}><ExternalLink size={14} /></a>
              <button className="bt pequeno so-icone fim" title={t("app.mina.excluir")}
                      disabled={excluir.isPending} onClick={() => excluir.mutate()}><Trash2 size={14} /></button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Nichos({ d, escolhido, escolher }: { d: EstadoMina; escolhido: string; escolher: (n: string) => void }) {
  const t = useT();
  const qc = useQueryClient();
  const [nome, setNome] = useState("");
  const recarregar = () => qc.invalidateQueries({ queryKey: CHAVE });
  const criar = useMutation({
    mutationFn: () => enviar<{ nicho: Nicho }>("/api/mineracao/nichos", { nome }),
    onSuccess: (r) => { setNome(""); escolher(r.nicho.nome); recarregar(); },
  });
  const refazer = useMutation({ mutationFn: (n: string) => enviar("/api/mineracao/nichos/refazer", { nome: n }), onSettled: recarregar });
  const apagar = useMutation({
    mutationFn: (n: string) => enviar("/api/mineracao/nichos/excluir", { nome: n }),
    onSuccess: (_r, n) => { if (n === escolhido) escolher(""); recarregar(); },
  });

  return (
    <div className="nichos">
      {d.nichos.length > 0 && (
        <div className="chips">
          <button className={`nicho ${escolhido === "" ? "on" : ""}`} onClick={() => escolher("")}>
            {t("app.mina.nicho_todos")}
          </button>
          {d.nichos.map((n) => (
            <span key={n.id} className={`nicho ${escolhido === n.nome ? "on" : ""}`}
                  title={[t("app.mina.nicho_termos", { termos: n.termos.join(" · ") }),
                          n.ultimo ? t("app.mina.nicho_ultimo", { quando: n.ultimo }) : t("app.mina.nicho_nunca")].join("\n")}>
              <button className="nome" onClick={() => escolher(n.nome)}>{n.nome}</button>
              <button className="ic" title={t("app.mina.nicho_refazer")} disabled={refazer.isPending}
                      onClick={() => refazer.mutate(n.nome)}><RefreshCw size={12} /></button>
              <button className="ic" title={t("app.mina.nicho_excluir")} onClick={() => apagar.mutate(n.nome)}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
      {d.nichos.length === 0 && <p className="sub">{t("app.mina.nichos_vazio")}</p>}
      <form onSubmit={(e) => { e.preventDefault(); criar.mutate(); }}>
        <label className="campo">
          {t("app.mina.nicho_novo")}
          <input value={nome} placeholder={t("app.mina.nicho_colar")} onChange={(e) => setNome(e.target.value)} />
        </label>
        <button className="bt" disabled={nome.trim().length < 2 || criar.isPending}>
          <Sparkles size={15} />{t(criar.isPending ? "app.mina.nicho_criando" : "app.mina.nicho_add")}
        </button>
      </form>
      {criar.isError && <p className="erro">{criar.error.message}</p>}
      {refazer.isError && <p className="erro">{refazer.error.message}</p>}
    </div>
  );
}

const CAMPOS: { id: keyof FiltrosMina; rot: string; passo?: string }[] = [
  { id: "dias", rot: "app.mina.f_dias" },
  { id: "idade_max_meses", rot: "app.mina.f_idade" },
  { id: "inscritos_min", rot: "app.mina.f_inscritos_min" },
  { id: "inscritos_max", rot: "app.mina.f_inscritos_max" },
  { id: "vistas_min", rot: "app.mina.f_vistas_min" },
  { id: "surto_min", rot: "app.mina.f_surto", passo: "0.1" },
  { id: "por_termo", rot: "app.mina.f_por_termo" },
  { id: "pais", rot: "app.mina.f_pais" },
  { id: "idioma", rot: "app.mina.f_idioma" },
];

function Filtros({ d }: { d: EstadoMina }) {
  const t = useT();
  const qc = useQueryClient();
  const [f, setF] = useState<FiltrosMina>(d.filtros);
  const salvar = useMutation({
    mutationFn: (filtros: FiltrosMina) => enviar("/api/mineracao/filtros", { filtros }),
    onSuccess: () => qc.invalidateQueries({ queryKey: CHAVE }),
  });
  return (
    <details className="cartao filtros-mina">
      <summary><b>{t("app.mina.filtros")}</b><span className="sub">{t("app.mina.filtros_sub")}</span></summary>
      <div className="grade">
        {CAMPOS.map((c) => (
          <label key={c.id} className="campo">
            {t(c.rot)}
            {typeof d.padroes[c.id] === "string" ? (
              <input value={String(f[c.id])} maxLength={5} onChange={(e) => setF({ ...f, [c.id]: e.target.value })} />
            ) : (
              <input type="number" min={0} step={c.passo ?? "1"} value={String(f[c.id])}
                     onChange={(e) => setF({ ...f, [c.id]: Number(e.target.value) })} />
            )}
          </label>
        ))}
      </div>
      <div className="acoes">
        <button className="bt primario" disabled={salvar.isPending} onClick={() => salvar.mutate(f)}>
          {t(salvar.isPending ? "app.enviando" : "app.mina.salvar_filtros")}
        </button>
        <button className="bt" onClick={() => { setF(d.padroes); salvar.mutate(d.padroes); }}>
          {t("app.mina.voltar_padrao")}
        </button>
      </div>
    </details>
  );
}

function PedirChave() {
  const t = useT();
  const qc = useQueryClient();
  const [valor, setValor] = useState("");
  const salvar = useMutation({
    mutationFn: () => enviar("/api/config/chaves/youtube", { valor }),
    onSuccess: () => { setValor(""); qc.invalidateQueries({ queryKey: CHAVE }); },
  });
  return (
    <form className="sem-chave" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
      <span className="ic"><KeyRound size={16} /></span>
      <div className="t"><b>{t("app.mina.sem_chave")}</b><span className="sub">{t("app.mina.sem_chave_explica")}</span></div>
      <input type="password" value={valor} autoComplete="off" placeholder={t("app.chaves.colar")}
             onChange={(e) => setValor(e.target.value)} />
      <button className="bt pequeno primario" disabled={!valor.trim() || salvar.isPending}>
        {t("app.modelar.salvar_chave")}
      </button>
    </form>
  );
}

export function Mineracao() {
  const t = useT();
  const qc = useQueryClient();
  const [aba, setAba] = useState<Aba>("novo");
  const [nicho, setNicho] = useState("");
  const [ordem, setOrdem] = useState("nota");
  const { data } = useQuery({
    queryKey: [...CHAVE, aba, nicho, ordem],
    queryFn: () => pegar<EstadoMina>(`/api/mineracao?situacao=${aba}&nicho=${encodeURIComponent(nicho)}&ordem=${ordem}`),
  });
  const garimpar = useMutation({
    mutationFn: () => enviar<{ resumo: { nicho: string; olhados: number; aprovados: number; novos: number; cota: number } }>(
      "/api/mineracao/garimpar", { nicho }),
    onSettled: () => qc.invalidateQueries({ queryKey: CHAVE }),
  });
  const auto = useMutation({
    mutationFn: (ligado: boolean) => enviar("/api/mineracao/filtros", { automatico: ligado }),
    onSettled: () => qc.invalidateQueries({ queryKey: CHAVE }),
  });
  if (!data) return <div className="nivel-produtor"><TopoProdutor /></div>;
  const ABAS: { id: Aba; rot: string; n: number }[] = [
    { id: "novo", rot: "app.mina.aba_novos", n: data.contas.novo },
    { id: "descartado", rot: "app.mina.aba_descartados", n: data.contas.descartado },
    { id: "modelo", rot: "app.mina.aba_modelo", n: data.contas.modelo },
  ];

  return (
    <div className="nivel-produtor">
      <TopoProdutor />
      <section className="tela-produtor">
        <CabecaTela titulo={t("app.mina.titulo")} sub={t("app.mina.pagina_sub")}>
          <span className="selo neutro">{t("app.mina.n", { n: data.contas.novo })}</span>
        </CabecaTela>

        <div className="cartao garimpo">
          <header>
            <Nichos d={data} escolhido={nicho} escolher={setNicho} />
            <button className="bt primario grande" disabled={!data.nichos.length || garimpar.isPending || !data.tem_chave}
                    onClick={() => garimpar.mutate()}>
              <Pickaxe size={17} />
              {t(garimpar.isPending ? "app.mina.garimpando" : nicho ? "app.mina.garimpar" : "app.mina.garimpar_vez", { nicho })}
            </button>
          </header>
          {garimpar.isError && <p className="erro">{garimpar.error.message}</p>}
          {garimpar.data && <p className="ok-mina">{t("app.mina.resumo", { ...garimpar.data.resumo })}</p>}
          <footer>
            <span title={t("app.mina.cota_sub")}>{t("app.mina.cota", { usada: data.cota.usada, limite: data.cota.limite })}</span>
            <span>{t("app.mina.custo", { n: data.custo_nicho })}</span>
            <span>{data.ultimo
              ? t("app.mina.ultimo", { quando: data.ultimo.quando, olhados: data.ultimo.olhados, aprovados: data.ultimo.aprovados, novos: data.ultimo.novos })
              : t("app.mina.nunca")}</span>
            <label className="liga" title={t("app.mina.automatico_sub")}>
              <input type="checkbox" checked={data.automatico} onChange={(e) => auto.mutate(e.target.checked)} />
              {t("app.mina.automatico")}
            </label>
          </footer>
        </div>

        {!data.tem_chave && <PedirChave />}
        <Filtros d={data} />

        <nav className="abas-mina">
          {ABAS.map((a) => (
            <button key={a.id} className={aba === a.id ? "on" : ""} onClick={() => setAba(a.id)}>
              {t(a.rot)} <em>{a.n}</em>
            </button>
          ))}
          <label className="ordenar">
            {t("app.mina.ordem")}
            <select value={ordem} onChange={(e) => setOrdem(e.target.value)}>
              {data.ordens.map((o) => <option key={o} value={o}>{t(`app.mina.ordem_${o}`)}</option>)}
            </select>
          </label>
        </nav>

        {data.itens.length > 0 ? (
          <div className="achados">{data.itens.map((v) => <CartaoVideoMinerado key={v.id} v={v} aba={aba} />)}</div>
        ) : (
          <div className="vazio-modelar">
            <span className="ic"><Pickaxe size={22} /></span>
            <div>
              <b>{t("app.mina.vazio_titulo")}</b>
              <p className="sub">{t(aba === "novo" ? "app.mina.vazio" : aba === "descartado" ? "app.mina.vazio_descartados" : "app.mina.vazio_modelo")}</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
