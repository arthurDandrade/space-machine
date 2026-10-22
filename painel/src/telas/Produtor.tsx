// Configurações do Space Machine (do produtor, valem para todos os canais): canais (com o novo canal), consumo,
// limpeza do disco e primeiros passos. O modelo do Claude de cada etapa é de cada canal (telas/ConfigCanal.tsx).
// A moldura — barra lateral por assunto e o cabeçalho de cada painel — está em casca/TopoProdutor.tsx.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowRight, Check, CircleAlert, CircleCheck, HardDrive, KeyRound, Palette, Plus, RotateCw, Save, Sparkles, Trash2 } from "lucide-react";
import { Atualizacao, Atualizou, Canais, Formatos, enviar, pegar, rota } from "../api";
import { CabecaTela } from "../casca/TopoProdutor";
import { Dialogo } from "../componentes/Dialogo";
import { LogoCanal } from "../componentes/Imagens";
import { AnelConsumo } from "../componentes/Pecas";
import { compacto, haQuanto, useT } from "../textos";

/** Criar canal é um diálogo: antes o formulário ficava sempre aberto e engolia a lista de canais. */
function NovoCanal({ fechar }: { fechar: () => void }) {
  const t = useT();
  const qc = useQueryClient();
  const navegar = useNavigate();
  const { data } = useQuery({ queryKey: ["fontes"], queryFn: () => pegar<{ fontes: { arquivo: string; nome: string }[] }>("/api/fontes"), staleTime: Infinity });
  const { data: fmt } = useQuery({ queryKey: ["formatos"], queryFn: () => pegar<Formatos>("/api/formatos"), staleTime: Infinity });
  const [formato, setFormato] = useState("");
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
    <Dialogo largo titulo={t("app.canais.novo")} fechar={fechar}
      acoes={<>
        <button type="button" className="bt" onClick={fechar}>{t("app.cancelar")}</button>
        <button className="bt primario" form="novo-canal" disabled={enviando}>
          <Plus size={16} />{enviando ? t("app.enviando") : t("app.config.criar_canal")}
        </button>
        {erro && <span className="erro">{erro}</span>}
      </>}>
      <p className="sub">{t("app.config.novo_explica")}</p>
      <form className="novo-canal duas-col" id="novo-canal" onSubmit={criar}>
        <div>
          <label className="campo">{t("app.config.nome_canal")}<input name="nome" required placeholder="Space Explained" /></label>
          <label className="campo">{t("app.config.formato")}
            {fmt && (
              <select name="formato" value={formato || fmt.padrao} onChange={(e) => setFormato(e.target.value)}>
                {fmt.formatos.map((f) => <option key={f.slug} value={f.slug}>{f.nome}</option>)}
              </select>
            )}
          </label>
          <p className="sub">{fmt?.formatos.find((f) => f.slug === (formato || fmt.padrao))?.resumo ?? t("app.config.formato_explica")}</p>
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
      </form>
    </Dialogo>
  );
}

export function CanaisConfigTela() {
  const t = useT();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  const ativar = useMutation({
    mutationFn: ({ slug, nome, ativo }: { slug: string; nome: string; ativo: boolean }) => enviar(`/api/c/${slug}/config`, { nome, ativo }),
    onSettled: () => qc.invalidateQueries(),
  });
  // "Novo canal" na tela inicial chega aqui com ?novo=1 e já abre o diálogo
  const [novo, setNovo] = useState(params.has("novo"));
  const fechar = () => { setNovo(false); if (params.has("novo")) setParams({}, { replace: true }); };
  return (
    <>
      <CabecaTela titulo={t("app.config.titulo_canais")} sub={t("app.config.canais_sub")}>
        <button className="bt primario" onClick={() => setNovo(true)}><Plus size={16} />{t("app.canais.novo")}</button>
      </CabecaTela>
      <div className="lista-canais">
        {(data?.canais ?? []).map((c) => (
          <div key={c.slug} className={`linha-canal ${c.ativo ? "" : "inativo"}`}
               style={c.cores.cor_destaque ? ({ "--accent": c.cores.cor_destaque } as React.CSSProperties) : undefined}>
            <LogoCanal canal={c.slug} nome={c.nome} cores={c.cores} tem={c.logo} />
            <div className="t">
              <b>{c.nome}</b>
              <span className="sub">{c.tema} · {t("app.config.n_videos", { n: c.n_videos })}</span>
            </div>
            <label className="interruptor" title={t("app.config.ativo_dica")}>
              <input type="checkbox" checked={c.ativo} onChange={(e) => ativar.mutate({ slug: c.slug, nome: c.nome, ativo: e.target.checked })} />
              <span className="trilho" /><span>{t(c.ativo ? "app.config.ativo" : "app.canais.inativo")}</span>
            </label>
            <div className="atalhos">
              <Link className="bt pequeno" to={`/c/${c.slug}/identidade`}><Palette size={14} />{t("app.nav.identidade")}</Link>
              <Link className="bt pequeno" to={`/c/${c.slug}/chaves`}><KeyRound size={14} />{t("app.nav.chaves")}</Link>
              <Link className="bt pequeno primario" to={`/c/${c.slug}`}>{t("app.config.entrar")}<ArrowRight size={14} /></Link>
            </div>
          </div>
        ))}
      </div>
      {novo && <NovoCanal fechar={fechar} />}
    </>
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
  const cabeca = <CabecaTela titulo={t("app.config.aba_consumo")} sub={t("app.consumo.explica")} />;
  if (!data) return <>{cabeca}<div className="carregando">{t("app.carregando")}</div></>;
  const total = data.por_etapa.reduce((s, e) => s + e.tokens, 0);
  return (
    <>
      {cabeca}
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
  const { data, isFetching } = useQuery({ queryKey: ["passos"], queryFn: () => pegar<{ itens: { ok: boolean; nome: string; detalhe: string; como: string }[]; after_app: string }>("/api/primeiros-passos"), refetchInterval: false });
  const [after, setAfter] = useState("");
  const preenchido = useRef(false);
  useEffect(() => {
    if (data && !preenchido.current) { preenchido.current = true; setAfter(data.after_app); }
  }, [data]);
  const salvarAfter = useMutation({
    mutationFn: () => enviar("/api/primeiros-passos/after", { after_app: after }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["passos"] }),
  });
  const testar = useMutation({
    mutationFn: () => enviar<{ ok: boolean; mensagem: string }>("/api/primeiros-passos/testar-claude"),
    onSettled: () => qc.invalidateQueries({ queryKey: ["canais"] }),
  });
  // o título fica de pé enquanto os dados não chegam: painel vazio parecia tela quebrada
  const cabeca = <CabecaTela titulo={t("app.config.aba_passos")} sub={t("pp.sub")} />;
  if (!data) return <>{cabeca}<div className="carregando">{t("app.carregando")}</div></>;
  const faltam = data.itens.filter((i) => !i.ok).length;
  return (
    <>
      {cabeca}
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
      <form className="cartao" style={{ marginTop: 16 }} onSubmit={(e) => { e.preventDefault(); salvarAfter.mutate(); }}>
        <div className="rodape-form" style={{ margin: 0, alignItems: "flex-end" }}>
          <label className="campo" style={{ maxWidth: 420, margin: 0 }}>{t("app.passos.after")}<input value={after} onChange={(e) => setAfter(e.target.value)} /></label>
          <button className="bt" disabled={salvarAfter.isPending}><Save size={16} />{t("comum.salvar")}</button>
          {salvarAfter.isSuccess && <span className="selo ok"><Check size={12} />{t("app.passos.after_salvo")}</span>}
          {salvarAfter.isError && <span className="erro">{salvarAfter.error.message}</span>}
        </div>
      </form>
      <div className="rodape-form" style={{ marginTop: 16 }}>
        <button className="bt" disabled={testar.isPending} onClick={() => testar.mutate()}><Sparkles size={16} />{testar.isPending ? t("app.passos.testando") : t("pp.testar_claude")}</button>
        <button className="bt pequeno" disabled={isFetching} onClick={() => qc.invalidateQueries({ queryKey: ["passos"] })}>{t("app.passos.conferir")}</button>
        <span className="sub">{t("pp.testar_claude_sub")}</span>
      </div>
      {testar.data && <div className={testar.data.ok ? "aviso-ok" : "aviso-parado"} style={{ marginTop: 12 }}>{testar.data.mensagem}</div>}
    </>
  );
}

// ---------------- limpeza ----------------
// O que a produção gera e não serve mais (prévias já entregues, candidatos, Auto-Save, cache) vai para o Lixo do Mac.
interface Limpeza {
  categorias: Record<string, number>;
  rotulos: Record<string, string>;
  total: number;
  automatica: boolean;
  disco: { livre: number; total: number };
  videos: { canal: string; canal_nome: string; video: string; titulo: string; categorias: Record<string, number>; total: number; itens: number }[];
}
interface Limpou { bytes: number; itens: number; pasta: string; no_lixo_do_mac: boolean; caminho: string }

const gbs = (n: number) => (n < 1e8 ? `${Math.max(1, Math.round(n / 1e6))} MB` : `${(n / 1e9).toFixed(1).replace(".", ",")} GB`);
const POR_VIDEO = ["previas", "candidatos", "after"];   // o cache é de todos os canais, não de um vídeo

export function LimpezaTela() {
  const t = useT();
  const qc = useQueryClient();
  const { data, isFetching } = useQuery({ queryKey: ["limpeza"], queryFn: () => pegar<Limpeza>("/api/limpeza"), refetchOnWindowFocus: false });
  const [escolhidas, setEscolhidas] = useState<string[]>(["previas", "candidatos", "after"]);
  const [confirmar, setConfirmar] = useState(false);
  const limpar = useMutation({
    mutationFn: () => enviar<Limpou>("/api/limpeza", { categorias: escolhidas }),
    onSuccess: () => { setConfirmar(false); qc.invalidateQueries(); },
  });
  const auto = useMutation({
    mutationFn: (ligada: boolean) => enviar("/api/limpeza/automatica", { ligada }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["limpeza"] }),
  });
  const cabeca = <CabecaTela titulo={t("app.config.aba_limpeza")} sub={t("app.limpeza.explica")} />;
  if (!data) return <>{cabeca}<div className="carregando">{t("app.carregando")}</div></>;
  const soma = escolhidas.reduce((s, c) => s + (data.categorias[c] || 0), 0);
  const usado = data.disco.total ? (data.disco.total - data.disco.livre) / data.disco.total : 0;
  const marcar = (c: string, sim: boolean) => setEscolhidas(sim ? [...escolhidas, c] : escolhidas.filter((x) => x !== c));
  return (
    <>
      {cabeca}
      {limpar.data && (
        <div className="aviso-ok">
          <CircleCheck size={16} />
          <span style={{ flex: 1 }}>
            {t(limpar.data.no_lixo_do_mac ? "app.limpeza.feito" : "app.limpeza.feito_pasta",
               { gb: gbs(limpar.data.bytes), n: limpar.data.itens, pasta: limpar.data.pasta, caminho: limpar.data.caminho })}
          </span>
          {limpar.data.no_lixo_do_mac && <button className="bt pequeno" onClick={() => enviar("/api/limpeza/abrir-lixo")}>{t("app.limpeza.abrir_lixo")}</button>}
        </div>
      )}
      <div className="limpeza-topo">
        <div className="cartao disco">
          <div className="titulo-secao"><h3><HardDrive size={16} />{t("app.limpeza.disco")}</h3></div>
          <div className="pct"><b>{gbs(data.disco.livre)}</b><span>{t("app.limpeza.livres", { total: gbs(data.disco.total) })}</span></div>
          <div className="progresso grosso"><i style={{ width: `${100 * usado}%`, background: usado > 0.85 ? "var(--bad)" : "var(--accent)" }} /></div>
          <label className="interruptor" style={{ marginTop: 18 }}>
            <input type="checkbox" checked={data.automatica} onChange={(e) => auto.mutate(e.target.checked)} />
            <span className="trilho" /><span>{t("app.limpeza.automatica")}</span>
          </label>
          <p className="sub" style={{ marginTop: 6 }}>{t("app.limpeza.automatica_sub")}</p>
        </div>
        <div className="cartao">
          <div className="titulo-secao"><h3>{t("app.limpeza.o_que")}</h3>{isFetching && <span className="sub">{t("app.carregando")}</span>}</div>
          {data.total === 0 ? <p className="sub">{t("app.limpeza.nada")}</p> : (
            <>
              <div className="cats-limpeza">
                {Object.keys(data.rotulos).map((c) => (
                  <label key={c} className={`cat-limpeza ${escolhidas.includes(c) && data.categorias[c] ? "on" : ""} ${data.categorias[c] ? "" : "zerada"}`}>
                    <input type="checkbox" checked={escolhidas.includes(c) && !!data.categorias[c]} disabled={!data.categorias[c]} onChange={(e) => marcar(c, e.target.checked)} />
                    <div className="t"><b>{data.rotulos[c]}</b><span className="sub">{t(`app.limpeza.ex_${c}`)}</span></div>
                    <span className="tam">{data.categorias[c] ? gbs(data.categorias[c]) : "—"}</span>
                  </label>
                ))}
              </div>
              <div className="rodape-form">
                <button className="bt primario" disabled={!soma || limpar.isPending} onClick={() => setConfirmar(true)}>
                  <Trash2 size={16} />{t("app.limpeza.botao", { gb: gbs(soma) })}
                </button>
                <span className="sub">{t("app.limpeza.recupera")}</span>
              </div>
            </>
          )}
        </div>
      </div>
      {data.videos.length > 0 && (
        <div className="cartao" style={{ marginTop: 20 }}>
          <div className="titulo-secao"><h3>{t("app.limpeza.por_video")}</h3></div>
          <div className="rola-x">
            <table className="tabela">
              <thead>
                <tr>
                  <th>{t("app.consumo.video")}</th>
                  {POR_VIDEO.map((c) => <th key={c} className="n">{data.rotulos[c].split(" ")[0]}</th>)}
                  <th className="n">{t("app.limpeza.total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.videos.map((v) => (
                  <tr key={v.canal + v.video}>
                    <td><Link to={rota.video(v.canal, v.video)}><b>{v.titulo}</b></Link><div className="sub">{v.canal_nome}</div></td>
                    {POR_VIDEO.map((c) => <td key={c} className="n">{v.categorias[c] ? gbs(v.categorias[c]) : "—"}</td>)}
                    <td className="n"><b>{gbs(v.total)}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {confirmar && (
        <Dialogo titulo={t("app.limpeza.confirmar_titulo", { gb: gbs(soma) })} fechar={() => setConfirmar(false)}
          acoes={<>
            <button className="bt" onClick={() => setConfirmar(false)}>{t("app.cancelar")}</button>
            <button className="bt primario" disabled={limpar.isPending} onClick={() => limpar.mutate()}>
              <Trash2 size={16} />{limpar.isPending ? t("app.limpeza.limpando") : t("app.limpeza.confirmar")}
            </button>
          </>}>
          <ul className="lista-dialogo">
            {escolhidas.filter((c) => data.categorias[c]).map((c) => <li key={c}>{data.rotulos[c]}: <b>{gbs(data.categorias[c])}</b></li>)}
          </ul>
          <p>{t("app.limpeza.confirmar_explica")}</p>
          {limpar.isError && <p className="erro">{limpar.error.message}</p>}
        </Dialogo>
      )}
    </>
  );
}

// ---------------- atualizar o Space Machine ----------------
// O código novo vem do GitHub (git pull); a pasta de dados não é tocada. Quando algo muda de verdade, o painel se
// reinicia no código novo (api.py › /api/atualizacao) e esta tela espera ele voltar para recarregar a página.
const dataCurta = (iso: string) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "");

export function AtualizarTela() {
  const t = useT();
  const qc = useQueryClient();
  const [conferindo, setConferindo] = useState(false);
  const [reiniciando, setReiniciando] = useState(false);
  const { data } = useQuery({ queryKey: ["atualizacao"], queryFn: () => pegar<Atualizacao>("/api/atualizacao"), refetchOnWindowFocus: false });
  const conferir = async () => {
    setConferindo(true);
    try {
      qc.setQueryData(["atualizacao"], await pegar<Atualizacao>("/api/atualizacao?conferir=1"));
      qc.invalidateQueries({ queryKey: ["sistema"] });
    } finally {
      setConferindo(false);
    }
  };
  const atualizar = useMutation({
    mutationFn: () => enviar<Atualizou>("/api/atualizacao"),
    onSuccess: async (r) => {
      if (!r.reiniciar) return void qc.invalidateQueries();
      setReiniciando(true);
      await new Promise((pronto) => setTimeout(pronto, 3500));   // o painel se troca 1,5 s depois de responder
      for (let i = 0; i < 180; i++) {
        try {
          if ((await fetch("/api/sistema", { cache: "no-store" })).ok) return window.location.reload();
        } catch {
          /* o painel ainda está voltando */
        }
        await new Promise((pronto) => setTimeout(pronto, 1000));
      }
      setReiniciando(false);
    },
  });
  const cabeca = <CabecaTela titulo={t("app.config.aba_atualizar")} sub={t("app.att.explica")} />;
  if (!data) return <>{cabeca}<div className="carregando">{t("app.carregando")}</div></>;
  const feito = atualizar.data;
  const impedimento = data.impedimento && (data.atrasado > 0 || data.impedimento === "sem_git") ? data.impedimento : "";
  const pode = data.atrasado > 0 && !impedimento && !reiniciando;
  return (
    <>
      {cabeca}
      <div className="cartao versao-att">
        <div className="t">
          <span className="sub">{t("app.att.sua_versao")}</span>
          <b>{data.local.versao || data.local.commit || "—"}{data.local.data && <span className="sub"> · {t("app.att.de", { data: dataCurta(data.local.data) })}</span>}</b>
          <span className="sub">{data.local.titulo}{data.local.branch && data.local.branch !== "main" ? ` · ${data.local.branch}` : ""}</span>
        </div>
        <div className="esp" />
        <button className="bt" disabled={conferindo} onClick={conferir}>
          <RotateCw size={16} />{conferindo ? t("app.att.conferindo") : t("app.att.conferir")}
        </button>
        {data.quando > 0 && <span className="sub">{t("app.att.conferido", { quando: haQuanto(t, data.quando) })}</span>}
      </div>

      {data.erro ? (
        <div className="aviso-parado" style={{ marginTop: 16 }}>
          <CircleAlert size={18} />
          <div><b>{t(`app.att.erro_${data.erro}`, undefined, t("app.att.erro_rede"))}</b>{data.erro_detalhe && <pre className="saida">{data.erro_detalhe}</pre>}</div>
        </div>
      ) : data.atrasado === 0 && !reiniciando && !feito ? (
        <div className="aviso-ok" style={{ marginTop: 16 }}><CircleCheck size={16} />{t("app.att.em_dia")}</div>
      ) : null}

      {data.atrasado > 0 && (
        <div className="cartao" style={{ marginTop: 16 }}>
          <div className="titulo-secao"><h3>{t("app.att.tem", { n: data.atrasado })}</h3></div>
          <div className="att-commits">
            {data.commits.map((c) => (
              <div key={c.commit} className="att-commit">
                <span className="sub">{dataCurta(c.data)}</span>
                <span>{c.titulo}</span>
              </div>
            ))}
          </div>
          <div className="rodape-form">
            <button className="bt primario" disabled={!pode || atualizar.isPending} onClick={() => atualizar.mutate()}>
              <ArrowDownToLine size={16} />{atualizar.isPending || reiniciando ? t("app.att.atualizando") : t("app.att.botao")}
            </button>
            <span className="sub">{t("app.att.demora")}</span>
          </div>
        </div>
      )}

      {impedimento && (
        <div className="aviso-parado" style={{ marginTop: 16 }}>
          <CircleAlert size={18} />
          <div>
            <b>{t("app.att.nao_da")}</b>
            <div>{t(`app.att.imp_${impedimento}`, undefined, impedimento)}</div>
            {data.detalhe && <pre className="saida">{data.detalhe}</pre>}
            <span className="sub">{t("app.att.pelo_terminal")}</span>
          </div>
        </div>
      )}

      {reiniciando && <div className="aviso-ok" style={{ marginTop: 16 }}><RotateCw size={16} className="girando" />{t("app.att.reiniciando")}</div>}

      {feito && !reiniciando && (
        <div style={{ marginTop: 16 }}>
          <div className={feito.ok && !feito.impedimento ? "aviso-ok" : "aviso-parado"}>
            {feito.ok && !feito.impedimento ? <CircleCheck size={16} /> : <CircleAlert size={18} />}
            <div>
              <b>{feito.nada ? t("app.att.em_dia") : feito.ok && !feito.impedimento
                ? t("app.att.pronto", { commit: feito.local.commit, data: dataCurta(feito.local.data) })
                : t("app.att.falhou")}</b>
              {feito.impedimento && <div>{t(`app.att.imp_${feito.impedimento}`, undefined, feito.impedimento)}</div>}
              {feito.detalhe && <pre className="saida">{feito.detalhe}</pre>}
            </div>
          </div>
          {feito.passos.length > 0 && (
            <div className="cartao passos-lista" style={{ marginTop: 12 }}>
              {feito.passos.map((p) => (
                <div key={p.passo} className={`passo-item ${p.ok ? "ok" : "falta"}`}>
                  <span className="ic">{p.ok ? <Check size={15} /> : <CircleAlert size={15} />}</span>
                  <div className="t"><b>{p.passo}</b>{!p.ok && p.saida && <pre className="saida">{p.saida}</pre>}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {atualizar.isError && <p className="erro">{atualizar.error.message}</p>}
    </>
  );
}
