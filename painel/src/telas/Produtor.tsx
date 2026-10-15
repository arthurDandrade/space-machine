// Configurações do Space Machine (do produtor, valem para todos os canais): canais (com o novo canal),
// modelos do Claude por etapa, consumo e primeiros passos.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, CircleAlert, CircleCheck, KeyRound, Palette, Plus, Save, Sparkles } from "lucide-react";
import { Canais, enviar, pegar } from "../api";
import { LogoCanal } from "../componentes/Imagens";
import { AnelConsumo } from "../componentes/Pecas";
import { compacto, useT } from "../textos";

function NovoCanal() {
  const t = useT();
  const qc = useQueryClient();
  const navegar = useNavigate();
  const { data } = useQuery({ queryKey: ["fontes"], queryFn: () => pegar<{ fontes: { arquivo: string; nome: string }[] }>("/api/fontes"), staleTime: Infinity });
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const criar = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErro(""); setEnviando(true);
    const r = await fetch("/api/canais/novo", { method: "POST", body: new FormData(e.currentTarget) });
    setEnviando(false);
    const corpo = await r.json().catch(() => ({}));
    if (!r.ok) return setErro(corpo.detail || r.statusText);
    qc.invalidateQueries();
    navegar(`/c/${corpo.slug}/regras`);
  };
  const impact = data?.fontes.find((f) => f.nome === "Impact")?.arquivo;
  return (
    <form className="cartao novo-canal" id="novo" onSubmit={criar}>
      <div className="titulo-secao"><h3>{t("app.canais.novo")}</h3></div>
      <p className="sub">{t("app.config.novo_explica")}</p>
      <div className="duas-col">
        <div>
          <label className="campo">{t("app.config.nome_canal")}<input name="nome" required placeholder="Space Explained" /></label>
          <label className="campo">{t("app.config.tema")}<input name="tema" required placeholder="astronomia" /></label>
          <label className="campo">{t("app.config.idioma")}
            <select name="idioma" defaultValue="en">
              <option value="en">{t("app.config.ingles")}</option>
              <option value="pt">{t("app.config.portugues")}</option>
              <option value="es">{t("app.config.espanhol")}</option>
            </select>
          </label>
          <label className="campo">{t("app.ident.fonte")}
            {data && (
              <select name="fonte" defaultValue={impact}>
                {data.fontes.map((f) => <option key={f.arquivo} value={f.arquivo}>{f.nome}</option>)}
              </select>
            )}
          </label>
        </div>
        <div>
          <label className="campo">{t("app.config.logo")}<input type="file" name="logo" accept="image/*" /></label>
          <label className="campo">{t("app.config.banner")}<input type="file" name="banner" accept="image/*" /></label>
          <label className="campo">{t("app.config.fundo")}<input type="file" name="fundo" accept="image/*" /></label>
          <div className="cores-grade">
            {([["cor_fundo", "#EDF0F6", "app.ident.fundo"], ["cor_texto", "#191A21", "app.ident.texto"], ["cor_destaque", "#1D2D85", "app.ident.destaque"],
               ["cor_caixa", "#0B2479", "app.ident.caixa"], ["cor_sombra", "#0B1A3A", "app.ident.sombra"]] as const).map(([k, v, rot]) => (
              <label key={k} className="campo cor">{t(rot)}<input type="color" name={k} defaultValue={v} /></label>
            ))}
          </div>
        </div>
      </div>
      <div className="rodape-form">
        <button className="bt primario" disabled={enviando}><Plus size={16} />{enviando ? t("app.enviando") : t("app.config.criar_canal")}</button>
        {erro && <span className="erro">{erro}</span>}
      </div>
    </form>
  );
}

export function CanaisConfigTela() {
  const t = useT();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const ref = useRef<HTMLDivElement>(null);
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  const ativar = useMutation({
    mutationFn: ({ slug, nome, ativo }: { slug: string; nome: string; ativo: boolean }) => enviar(`/api/c/${slug}/config`, { nome, ativo }),
    onSettled: () => qc.invalidateQueries(),
  });
  useEffect(() => { if (params.has("novo")) ref.current?.scrollIntoView({ behavior: "smooth" }); }, [params, data]);
  return (
    <>
      <div className="lista-canais">
        {(data?.canais ?? []).map((c) => (
          <div key={c.slug} className="linha-canal" style={c.cores.cor_destaque ? ({ "--accent": c.cores.cor_destaque } as React.CSSProperties) : undefined}>
            <LogoCanal canal={c.slug} nome={c.nome} cores={c.cores} tem={c.logo} />
            <div className="t"><b>{c.nome}</b><span className="sub">{c.tema} · {t("app.config.n_videos", { n: c.n_videos })}</span></div>
            <label className="interruptor">
              <input type="checkbox" checked={c.ativo} onChange={(e) => ativar.mutate({ slug: c.slug, nome: c.nome, ativo: e.target.checked })} />
              <span className="trilho" /><span>{t(c.ativo ? "app.config.ativo" : "app.canais.inativo")}</span>
            </label>
            <Link className="bt pequeno" to={`/c/${c.slug}/identidade`}><Palette size={14} />{t("app.nav.identidade")}</Link>
            <Link className="bt pequeno" to={`/c/${c.slug}/chaves`}><KeyRound size={14} />{t("app.nav.chaves")}</Link>
            <Link className="bt pequeno primario" to={`/c/${c.slug}`}>{t("app.config.entrar")}<ArrowRight size={14} /></Link>
          </div>
        ))}
      </div>
      <div ref={ref}><NovoCanal /></div>
    </>
  );
}

interface Modelos {
  linhas: { id: string; nome: string; ajuda: string; modelo: string; esforco: string; chamadas: number; media: number; ultimo: string }[];
  modelos: { id: string; nome: string }[];
  esforcos: string[];
  after_app: string;
}

export function ModelosTela() {
  const t = useT();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["modelos"], queryFn: () => pegar<Modelos>("/api/config/modelos"), refetchInterval: false });
  const [modelos, setModelos] = useState<Record<string, string>>({});
  const [esforco, setEsforco] = useState<Record<string, string>>({});
  const [after, setAfter] = useState("");
  const preenchido = useRef(false);
  useEffect(() => {
    if (data && !preenchido.current) {
      preenchido.current = true;
      setModelos(Object.fromEntries(data.linhas.map((l) => [l.id, l.modelo])));
      setEsforco(Object.fromEntries(data.linhas.map((l) => [l.id, l.esforco])));
      setAfter(data.after_app);
    }
  }, [data]);
  const salvar = useMutation({
    mutationFn: () => enviar("/api/config/modelos", { modelos, esforco, after_app: after }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["modelos"] }),
  });
  if (!data) return null;
  return (
    <form className="cartao" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
      <p className="sub">{t("app.modelos.explica")}</p>
      <div className="tabela-modelos">
        {data.linhas.map((l) => (
          <div key={l.id} className="linha-modelo">
            <div className="t"><b>{l.nome}</b><span className="sub">{l.ajuda}</span></div>
            <select value={modelos[l.id] ?? ""} onChange={(e) => setModelos({ ...modelos, [l.id]: e.target.value })}>
              {data.modelos.map((m) => <option key={m.id} value={m.id}>{m.nome}</option>)}
            </select>
            <select value={esforco[l.id] ?? "low"} onChange={(e) => setEsforco({ ...esforco, [l.id]: e.target.value })}>
              {data.esforcos.map((x) => <option key={x}>{x}</option>)}
            </select>
            <div className="num"><b>{compacto(l.media)}</b><span>{t("app.modelos.por_chamada", { n: l.chamadas })}</span></div>
          </div>
        ))}
      </div>
      <label className="campo" style={{ marginTop: 18, maxWidth: 420 }}>{t("app.modelos.after")}<input value={after} onChange={(e) => setAfter(e.target.value)} /></label>
      <div className="rodape-form">
        <button className="bt primario" disabled={salvar.isPending}><Save size={16} />{t("comum.salvar")}</button>
        {salvar.isSuccess && <span className="selo ok"><Check size={12} />{t("app.modelos.salvo")}</span>}
        {salvar.isError && <span className="erro">{salvar.error.message}</span>}
      </div>
    </form>
  );
}

interface Consumo {
  total_7d: number;
  por_etapa: { etapa: string; chamadas: number; tokens: number; media: number }[];
  por_video: { canal: string; video: string; chamadas: number; tokens: number; ultima: string }[];
  linhas: { canal: string; video: string; bloco: string; etapa: string; modelo: string; chamadas: number; tokens: number; falhas: number; ultima: string }[];
}

export function ConsumoTela() {
  const t = useT();
  const { data } = useQuery({ queryKey: ["consumo"], queryFn: () => pegar<Consumo>("/api/consumo") });
  if (!data) return null;
  const total = data.por_etapa.reduce((s, e) => s + e.tokens, 0);
  return (
    <>
      <p className="sub intro">{t("app.consumo.explica")}</p>
      <div className="consumo-topo">
        <div className="cartao"><div className="titulo-secao"><h3>{t("app.consumo.tudo")}</h3><span className="sub">{t("app.consumo.semana", { n: compacto(data.total_7d) })}</span></div>
          <AnelConsumo total={total} etapas={data.por_etapa.map((e) => ({ etapa: e.etapa, tokens: e.tokens }))} /></div>
        <div className="cartao">
          <div className="titulo-secao"><h3>{t("app.consumo.por_etapa")}</h3></div>
          <div className="rola-x"><table className="tabela">
            <thead><tr><th>{t("app.consumo.etapa")}</th><th className="n">{t("app.consumo.chamadas")}</th><th className="n">{t("app.consumo.tokens_col")}</th><th className="n">{t("app.consumo.media")}</th></tr></thead>
            <tbody>{data.por_etapa.map((e) => (
              <tr key={e.etapa}><td>{t(`app.consumo.${e.etapa}`, undefined, e.etapa)}</td><td className="n">{e.chamadas}</td><td className="n">{compacto(e.tokens)}</td><td className="n">{compacto(e.media)}</td></tr>
            ))}</tbody>
          </table></div>
        </div>
      </div>
      <div className="cartao" style={{ marginTop: 20 }}>
        <div className="titulo-secao"><h3>{t("app.consumo.por_video")}</h3></div>
        <div className="rola-x"><table className="tabela">
          <thead><tr><th>{t("app.consumo.canal")}</th><th>{t("app.consumo.video")}</th><th className="n">{t("app.consumo.chamadas")}</th><th className="n">{t("app.consumo.tokens_col")}</th><th>{t("app.consumo.ultima")}</th></tr></thead>
          <tbody>{data.por_video.map((v) => (
            <tr key={v.canal + v.video}><td>{v.canal}</td><td>{v.video || "—"}</td><td className="n">{v.chamadas}</td><td className="n">{compacto(v.tokens)}</td><td className="sub">{v.ultima}</td></tr>
          ))}</tbody>
        </table></div>
      </div>
      <details className="cartao recolhe" style={{ marginTop: 20 }}>
        <summary><h3>{t("app.consumo.detalhe")}</h3><span className="sub">{t("app.consumo.ultimas", { n: data.linhas.length })}</span></summary>
        <div className="tabela-rola">
          <table className="tabela">
            <thead><tr><th>{t("app.consumo.video")}</th><th>{t("app.consumo.bloco")}</th><th>{t("app.consumo.etapa")}</th><th>{t("app.consumo.modelo")}</th><th className="n">{t("app.consumo.chamadas")}</th><th className="n">{t("app.consumo.tokens_col")}</th><th className="n">{t("app.consumo.falhas")}</th><th>{t("app.consumo.ultima")}</th></tr></thead>
            <tbody>{data.linhas.map((l, i) => (
              <tr key={i}><td>{l.video}</td><td>{l.bloco}</td><td>{t(`app.consumo.${l.etapa}`, undefined, l.etapa)}</td><td className="sub">{l.modelo.replace("claude-", "")}</td><td className="n">{l.chamadas}</td><td className="n">{compacto(l.tokens)}</td><td className="n">{l.falhas || ""}</td><td className="sub">{l.ultima}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </details>
    </>
  );
}

export function PassosTela() {
  const t = useT();
  const qc = useQueryClient();
  const { data, isFetching } = useQuery({ queryKey: ["passos"], queryFn: () => pegar<{ itens: { ok: boolean; nome: string; detalhe: string; como: string }[] }>("/api/primeiros-passos"), refetchInterval: false });
  const testar = useMutation({
    mutationFn: () => enviar<{ ok: boolean; mensagem: string }>("/api/primeiros-passos/testar-claude"),
    onSettled: () => qc.invalidateQueries({ queryKey: ["canais"] }),
  });
  if (!data) return <div className="carregando">{t("app.carregando")}</div>;
  const faltam = data.itens.filter((i) => !i.ok).length;
  return (
    <>
      <p className="sub intro">{t("pp.sub")}</p>
      {faltam === 0 ? <div className="aviso-ok"><CircleCheck size={16} />{t("pp.tudo_ok")}</div>
        : <div className="aviso-parado"><CircleAlert size={18} /><div><b>{t("app.passos.faltam", { n: faltam })}</b></div></div>}
      <div className="cartao passos-lista">
        {data.itens.map((i) => (
          <div key={i.nome} className={`passo-item ${i.ok ? "ok" : "falta"}`}>
            <span className="ic">{i.ok ? <Check size={15} /> : <CircleAlert size={15} />}</span>
            <div className="t"><b>{i.nome}</b><span className="sub">{i.detalhe}</span>{i.como && <span className="como">{t("pp.como")}: {i.como}</span>}</div>
          </div>
        ))}
      </div>
      <div className="rodape-form" style={{ marginTop: 16 }}>
        <button className="bt" disabled={testar.isPending} onClick={() => testar.mutate()}><Sparkles size={16} />{testar.isPending ? t("app.passos.testando") : t("pp.testar_claude")}</button>
        <button className="bt pequeno" disabled={isFetching} onClick={() => qc.invalidateQueries({ queryKey: ["passos"] })}>{t("app.passos.conferir")}</button>
        <span className="sub">{t("pp.testar_claude_sub")}</span>
      </div>
      {testar.data && <div className={testar.data.ok ? "aviso-ok" : "aviso-parado"} style={{ marginTop: 12 }}>{testar.data.mensagem}</div>}
    </>
  );
}
