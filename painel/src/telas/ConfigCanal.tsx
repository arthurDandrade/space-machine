// Configurações de um canal: identidade (nome, cores, fonte, logo, banner, com prévia), regras do tema,
// log de aprendizados e chaves de API. Chave secreta nunca chega inteira aqui: só a máscara.
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, KeyRound, Save, Sparkles, Upload, Wand2 } from "lucide-react";
import { Cores, enviar, ErroApi, Formato, Narracao, pegar, urlMarca } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { fundoDoCanal, iniciais } from "../componentes/Imagens";
import { Markdown } from "../componentes/Markdown";
import { useT } from "../textos";

type Regras = Record<"escolha" | "storyboard" | "genericas" | "genericas_hist" | "proibidos" | "permitido_se" | "trocas", string>;
interface ConfigCanal {
  slug: string; nome: string; ativo: boolean; tema: string; idioma: string; cores: Cores; fonte: string;
  fontes: { arquivo: string; nome: string }[]; banner: boolean; logo: boolean; regras: Regras;
  formato: string; formatos: Formato[];
}
const useConfig = (canal: string) =>
  useQuery({ queryKey: ["config", canal], queryFn: () => pegar<ConfigCanal>(`/api/c/${canal}/config`) });

const CORES: [keyof Cores, string][] = [
  ["cor_fundo", "app.ident.fundo"], ["cor_texto", "app.ident.texto"], ["cor_destaque", "app.ident.destaque"],
  ["cor_caixa", "app.ident.caixa"], ["cor_sombra", "app.ident.sombra"],
];

function TrocarImagem({ canal, qual, tem, cores, nome, versao, mudou }: { canal: string; qual: "logo" | "banner"; tem: boolean; cores: Cores; nome: string; versao: number; mudou: () => void }) {
  const t = useT();
  const campo = useRef<HTMLInputElement>(null);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const mandar = async (f: File) => {
    setErro(""); setEnviando(true);
    const corpo = new FormData();
    corpo.append("arquivo", f);
    const r = await fetch(`/api/c/${canal}/marca/${qual}`, { method: "POST", body: corpo });
    setEnviando(false);
    if (!r.ok) setErro((await r.json().catch(() => ({}))).detail || r.statusText);
    else mudou();
  };
  return (
    <div className={`troca-img ${qual}`}>
      <div className="previa-img" style={tem ? undefined : { background: fundoDoCanal(cores) }}>
        {tem ? <img src={`${urlMarca(canal, qual)}?v=${versao}`} alt="" /> : <span>{iniciais(nome)}</span>}
      </div>
      <div>
        <b>{t(`app.ident.${qual}`)}</b>
        <span className="sub">{t(`app.ident.${qual}_dica`)}</span>
        <input ref={campo} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(e) => e.target.files?.[0] && mandar(e.target.files[0])} />
        <button type="button" className="bt pequeno" disabled={enviando} onClick={() => campo.current?.click()}>
          <Upload size={14} />{enviando ? t("app.enviando") : t(tem ? "app.ident.trocar" : "app.ident.enviar")}
        </button>
        {erro && <span className="erro">{erro}</span>}
      </div>
    </div>
  );
}

export function IdentidadeTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data } = useConfig(canal);
  const t = useT();
  const qc = useQueryClient();
  const [nome, setNome] = useState("");
  const [ativo, setAtivo] = useState(true);
  const [cores, setCores] = useState<Cores>({});
  const [fonte, setFonte] = useState("");
  const [formato, setFormato] = useState("");
  const [versao, setVersao] = useState(Date.now());
  // preenche uma vez: os dados se atualizam ao vivo e não podem apagar o que você está digitando
  const preenchido = useRef(false);
  useEffect(() => {
    if (data && !preenchido.current) {
      preenchido.current = true;
      setNome(data.nome); setAtivo(data.ativo); setCores(data.cores); setFonte(data.fonte);
      setFormato(data.formato);
    }
  }, [data]);
  const salvar = useMutation({
    mutationFn: async () => {
      await enviar(`/api/c/${canal}/config`, { nome, ativo, formato });
      await enviar(`/api/c/${canal}/identidade`, { cores, fonte });
    },
    onSuccess: () => qc.invalidateQueries(),
  });
  if (!data || !dc) return null;
  const familia = data.fontes.find((f) => f.arquivo === fonte)?.nome ?? "Impact";
  const mudouImagem = () => { setVersao(Date.now()); qc.invalidateQueries(); };
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.identidade")}</b></>} titulo={t("app.ident.titulo")} />
      <div className="config-grade">
        <form className="cartao" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
          <div className="duas-col">
            <label className="campo">{t("app.ident.nome")}<input value={nome} onChange={(e) => setNome(e.target.value)} /></label>
            <label className="campo">{t("app.ident.fonte")}
              <select value={fonte} onChange={(e) => setFonte(e.target.value)}>
                {data.fontes.map((f) => <option key={f.arquivo} value={f.arquivo}>{f.nome}</option>)}
              </select>
            </label>
          </div>
          <label className="campo">{t("app.ident.formato")}
            <select value={formato} onChange={(e) => setFormato(e.target.value)}>
              {data.formatos.map((f) => <option key={f.slug} value={f.slug}>{f.nome}</option>)}
            </select>
          </label>
          <p className="sub">{t("app.ident.formato_troca")}</p>
          <div className="cores-grade">
            {CORES.map(([k, rot]) => (
              <label key={k} className="campo cor">{t(rot)}
                <span className="par-cor">
                  <input type="color" value={cores[k] || "#000000"} onChange={(e) => setCores({ ...cores, [k]: e.target.value.toUpperCase() })} />
                  <code>{cores[k]}</code>
                </span>
              </label>
            ))}
          </div>
          <label className="interruptor">
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            <span className="trilho" /><span>{t("app.ident.ativo")}</span>
          </label>
          <p className="sub">{t("app.ident.vale_proximos")}</p>
          <div className="rodape-form">
            <button className="bt primario" disabled={salvar.isPending}><Save size={16} />{t("comum.salvar")}</button>
            {salvar.isSuccess && <span className="selo ok"><Check size={12} />{t("app.salvo")}</span>}
            {salvar.isError && <span className="erro">{salvar.error.message}</span>}
          </div>
        </form>
        <div className="coluna-dir">
          <div className="cartao">
            <div className="titulo-secao"><h3>{t("app.ident.previa")}</h3></div>
            <div className="previa-quadro" style={{ background: cores.cor_fundo }}>
              <div className="previa-card" style={{ boxShadow: `0 18px 30px ${cores.cor_sombra}55` }}>
                <div className="foto" />
              </div>
              <div className="previa-titulo" style={{ fontFamily: `"${familia}", Impact, sans-serif`, color: cores.cor_texto }}>
                {nome || data.nome}
                <span style={{ background: cores.cor_caixa, color: "#fff" }}>{t("app.ident.exemplo")}</span>
              </div>
              <div className="previa-faixa" style={{ background: cores.cor_destaque }} />
            </div>
          </div>
          <div className="cartao imagens">
            <TrocarImagem canal={canal} qual="logo" tem={data.logo} cores={cores} nome={nome} versao={versao} mudou={mudouImagem} />
            <TrocarImagem canal={canal} qual="banner" tem={data.banner} cores={cores} nome={nome} versao={versao} mudou={mudouImagem} />
          </div>
        </div>
      </div>
    </>
  );
}

const CAMPOS_REGRAS: { k: keyof Regras; rot: string; ex?: string; linhas: number }[] = [
  { k: "escolha", rot: "regras.escolha", ex: "regras.escolha_ex", linhas: 8 },
  { k: "storyboard", rot: "regras.storyboard", ex: "regras.storyboard_ex", linhas: 8 },
  { k: "genericas", rot: "regras.genericas", linhas: 3 },
  { k: "genericas_hist", rot: "regras.genericas_hist", linhas: 3 },
  { k: "proibidos", rot: "regras.proibidos", linhas: 1 },
  { k: "permitido_se", rot: "regras.permitido_se", linhas: 1 },
  { k: "trocas", rot: "regras.trocas", ex: "regras.trocas_ex", linhas: 2 },
];

export function RegrasTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data } = useConfig(canal);
  const t = useT();
  const qc = useQueryClient();
  const [regras, setRegras] = useState<Regras | null>(null);
  const [sugerido, setSugerido] = useState(false);
  useEffect(() => { if (data && !regras) setRegras(data.regras); }, [data, regras]);
  const salvar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/regras`, { regras }),
    onSuccess: () => { setSugerido(false); qc.invalidateQueries({ queryKey: ["config", canal] }); },
  });
  const sugerir = useMutation({
    mutationFn: () => enviar<{ regras: Regras }>(`/api/c/${canal}/regras/sugerir`),
    onSuccess: (r) => { setRegras(r.regras); setSugerido(true); },
  });
  if (!dc || !regras) return null;
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("regras.titulo")}</b></>} titulo={t("regras.titulo")}>
        <button className="bt" disabled={sugerir.isPending} onClick={() => sugerir.mutate()}>
          <Wand2 size={16} />{sugerir.isPending ? t("app.regras.perguntando") : t("regras.sugerir")}
        </button>
      </Cabecalho>
      <p className="sub intro">{t("regras.sub")}</p>
      {sugerido && <div className="aviso-ok"><Sparkles size={16} />{t("regras.sugeridas")}</div>}
      {sugerir.isError && <p className="erro">{sugerir.error.message}</p>}
      <form className="cartao" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
        <div className="regras-grade">
          {CAMPOS_REGRAS.map((c) => (
            <label key={c.k} className={`campo ${c.linhas > 2 ? "" : "curto"}`}>{t(c.rot)}
              {c.linhas > 1
                ? <textarea rows={c.linhas} value={regras[c.k]} placeholder={c.ex ? t(c.ex) : undefined} onChange={(e) => setRegras({ ...regras, [c.k]: e.target.value })} />
                : <input value={regras[c.k]} onChange={(e) => setRegras({ ...regras, [c.k]: e.target.value })} />}
            </label>
          ))}
        </div>
        <div className="rodape-form">
          <button className="bt primario" disabled={salvar.isPending}><Save size={16} />{t("regras.salvar")}</button>
          {salvar.isSuccess && <span className="selo ok"><Check size={12} />{t("app.salvo")}</span>}
          {salvar.isError && <span className="erro">{salvar.error.message}</span>}
          <span className="sub">{t("regras.sugerir_sub")}</span>
        </div>
      </form>
    </>
  );
}

export function AprendizadosTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data } = useQuery({ queryKey: ["aprendizados", canal], queryFn: () => pegar<{ texto: string }>(`/api/c/${canal}/aprendizados`) });
  const t = useT();
  if (!dc || !data) return null;
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.aprendizados")}</b></>} titulo={t("app.aprendizados.titulo")} />
      <p className="sub intro">{t("app.aprendizados.explica")}</p>
      {data.texto ? <div className="cartao leitura"><Markdown texto={data.texto.replace(/^---[\s\S]*?---\n/, "")} /></div>
        : <div className="vazio">{t("app.aprendizados.vazio")}</div>}
    </>
  );
}

interface Api {
  id: string; nome: string; escopo: string; ajuda: string; configurada: boolean;
  campos: { chave: string; rotulo: string; secreta: boolean; dica: string; tem_valor: boolean; mostrar: string; valor: string }[];
}

function CartaoApi({ canal, a }: { canal: string; a: Api }) {
  const t = useT();
  const qc = useQueryClient();
  const [valores, setValores] = useState<Record<string, string>>(() => Object.fromEntries(a.campos.map((c) => [c.chave, c.secreta ? "" : c.valor])));
  const [apagar, setApagar] = useState<string[]>([]);
  const salvar = useMutation({
    mutationFn: () => enviar<{ mudou: string[] }>(`/api/c/${canal}/chaves/${a.id}`, { valores, apagar }),
    onSuccess: () => {
      setValores((v) => Object.fromEntries(Object.entries(v).map(([k, x]) => [k, a.campos.find((c) => c.chave === k)?.secreta ? "" : x])));
      setApagar([]);
      qc.invalidateQueries({ queryKey: ["chaves", canal] });
      qc.invalidateQueries({ queryKey: ["canais"] });
    },
  });
  const testar = useMutation({ mutationFn: () => enviar<{ ok: boolean; mensagem: string }>(`/api/c/${canal}/chaves/${a.id}/testar`) });
  return (
    <form className="cartao api" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }} autoComplete="off">
      <div className="titulo-api">
        <span className="ic"><KeyRound size={16} /></span>
        <div><h3>{a.nome}</h3><span className="sub">{a.ajuda.split("`").map((p, i) => (i % 2 ? <code key={i}>{p}</code> : p))}</span></div>
        <div className="selos">
          {a.configurada ? <span className="selo ok">{t("app.chaves.configurada")}</span> : <span className="selo wait">{t("app.chaves.sem_chave")}</span>}
          {a.escopo === "sistema" && <span className="selo neutro">{t("app.chaves.todos_canais")}</span>}
        </div>
      </div>
      <div className="campos-api">
        {a.campos.map((c) => (
          <label key={c.chave} className="campo">
            <span>{c.rotulo}{c.secreta && c.tem_valor && <em> · {t("app.chaves.atual", { m: c.mostrar })}</em>}</span>
            <input type={c.secreta ? "password" : "text"} autoComplete={c.secreta ? "new-password" : "off"} value={valores[c.chave] ?? ""}
                   placeholder={c.secreta ? t(c.tem_valor ? "app.chaves.trocar" : "app.chaves.colar") : c.dica}
                   onChange={(e) => setValores({ ...valores, [c.chave]: e.target.value })} />
            {c.secreta && c.tem_valor && (
              <span className="apagar">
                <input type="checkbox" checked={apagar.includes(c.chave)} onChange={(e) => setApagar(e.target.checked ? [...apagar, c.chave] : apagar.filter((x) => x !== c.chave))} />
                {t("app.chaves.apagar")}
              </span>
            )}
          </label>
        ))}
      </div>
      <div className="rodape-form">
        <button className="bt primario pequeno" disabled={salvar.isPending}><Save size={14} />{t("comum.salvar")}</button>
        <button type="button" className="bt pequeno" disabled={testar.isPending} onClick={() => testar.mutate()}>{testar.isPending ? t("app.chaves.testando") : t("app.chaves.testar")}</button>
        {salvar.isSuccess && <span className="selo ok"><Check size={12} />{salvar.data.mudou.length ? t("app.salvo") : t("app.chaves.nada_mudou")}</span>}
        {salvar.isError && <span className="erro">{salvar.error.message}</span>}
        {testar.data && <span className={`selo ${testar.data.ok ? "ok" : "bad"}`}>{testar.data.mensagem}</span>}
        {testar.isError && <span className="erro">{(testar.error as ErroApi).message}</span>}
      </div>
    </form>
  );
}

interface OutroCanal { slug: string; nome: string; apis: { id: string; nome: string; mostrar: string }[] }

/** Traz para este canal a chave de API que outro canal já tem (só o campo secreto; a voz do Fish fica a daqui). */
function ImportarChaves({ canal, jaTem }: { canal: string; jaTem: Set<string> }) {
  const t = useT();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["chaves-importar", canal], queryFn: () => pegar<{ canais: OutroCanal[] }>(`/api/c/${canal}/chaves-importar`), refetchInterval: false });
  const [origem, setOrigem] = useState("");
  const [marcados, setMarcados] = useState<string[] | null>(null);
  const lista = data?.canais ?? [];
  const de = lista.find((c) => c.slug === origem) ?? lista[0];
  // sem escolha da pessoa, já vêm marcadas as chaves que faltam aqui
  const escolhidas = marcados ?? (de?.apis ?? []).filter((a) => !jaTem.has(a.id)).map((a) => a.id);
  const importar = useMutation({
    mutationFn: () => enviar<{ copiados: string[] }>(`/api/c/${canal}/chaves-importar`, { origem: de.slug, apis: escolhidas }),
    onSuccess: () => {
      setMarcados(null);
      qc.invalidateQueries({ queryKey: ["chaves", canal] });
      qc.invalidateQueries({ queryKey: ["canais"] });
    },
  });
  if (!de) return null;
  return (
    <form className="cartao api importar-chaves" onSubmit={(e) => { e.preventDefault(); importar.mutate(); }}>
      <div className="titulo-api">
        <span className="ic"><Copy size={16} /></span>
        <div><h3>{t("app.chaves.importar_titulo")}</h3><span className="sub">{t("app.chaves.importar_explica")}</span></div>
      </div>
      <div className="duas-col">
        <label className="campo">
          <span>{t("app.chaves.importar_de")}</span>
          <select value={de.slug} onChange={(e) => { setOrigem(e.target.value); setMarcados(null); }}>
            {lista.map((c) => <option key={c.slug} value={c.slug}>{c.nome}</option>)}
          </select>
        </label>
        <div className="campo">
          <span>{t("app.chaves.importar_quais")}</span>
          <div className="escolher-apis">
            {de.apis.map((a) => (
              <label key={a.id} className="marcar">
                <input type="checkbox" checked={escolhidas.includes(a.id)}
                       onChange={(e) => setMarcados(e.target.checked ? [...escolhidas, a.id] : escolhidas.filter((x) => x !== a.id))} />
                <span>{a.nome} <em>{a.mostrar}</em>{jaTem.has(a.id) && <em> · {t("app.chaves.importar_ja_tem")}</em>}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
      <div className="rodape-form">
        <button className="bt primario pequeno" disabled={!escolhidas.length || importar.isPending}>
          <Copy size={14} />{importar.isPending ? t("app.chaves.importar_copiando") : t("app.chaves.importar_bt")}
        </button>
        {importar.isSuccess && <span className="selo ok"><Check size={12} />{importar.data.copiados.length ? t("app.chaves.importar_feito", { n: importar.data.copiados.length }) : t("app.chaves.importar_nada")}</span>}
        {importar.isError && <span className="erro">{(importar.error as ErroApi).message}</span>}
      </div>
    </form>
  );
}

function EscolherNarracao({ canal, narracao }: { canal: string; narracao: Narracao }) {
  const t = useT();
  const qc = useQueryClient();
  const trocar = useMutation({
    mutationFn: (provedor: string) => enviar(`/api/c/${canal}/narracao`, { provedor }),
    onSuccess: () => qc.invalidateQueries(),
  });
  return (
    <form className="cartao" onSubmit={(e) => e.preventDefault()}>
      <div className="titulo-secao"><h3>{t("app.chaves.narracao")}</h3></div>
      <label className="campo">{t("app.chaves.narracao_quem")}
        <select value={narracao.provedor} onChange={(e) => trocar.mutate(e.target.value)} disabled={trocar.isPending}>
          {narracao.provedores.map((p) => <option key={p.id} value={p.id}>{p.nome}</option>)}
        </select>
      </label>
      <p className="sub">{t("app.chaves.narracao_explica")}</p>
      {trocar.isSuccess && <span className="selo ok"><Check size={12} />{t("app.salvo")}</span>}
      {trocar.isError && <span className="erro">{(trocar.error as ErroApi).message}</span>}
    </form>
  );
}

export function ChavesTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data } = useQuery({ queryKey: ["chaves", canal], queryFn: () => pegar<{ apis: Api[]; narracao: Narracao }>(`/api/c/${canal}/chaves`), refetchInterval: false });
  const t = useT();
  if (!dc || !data) return null;
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.chaves")}</b></>} titulo={t("app.chaves.titulo")} />
      <p className="sub intro">{t("app.chaves.explica")}</p>
      <EscolherNarracao canal={canal} narracao={data.narracao} />
      <ImportarChaves canal={canal} jaTem={new Set(data.apis.filter((a) => a.configurada).map((a) => a.id))} />
      <div className="apis">{data.apis.map((a) => <CartaoApi key={a.id} canal={canal} a={a} />)}</div>
    </>
  );
}
