// Mineração: área própria do produtor. Garimpa no YouTube canais novos que estouraram a própria audiência
// (space_machine/mineracao.py, pela API oficial) e manda para a Modelagem os que você quiser estudar.
// Nada é aberto nem baixado: o link do card é um link comum, que só vai ao YouTube quando VOCÊ clica.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink, KeyRound, Pickaxe, Plus, Power, Sparkles, Target, Trash2, Undo2, X,
} from "lucide-react";
import {
  CanalMinerado, EstadoMina, FiltrosMina, Veio, enviar, pegar, urlLogoMinerado,
} from "../api";
import { CabecaTela, TopoProdutor } from "../casca/TopoProdutor";
import { compacto, useT } from "../textos";

type Aba = "novo" | "descartado" | "modelo";

const CHAVE = ["mineracao"];

function Logo({ c }: { c: CanalMinerado }) {
  const [falhou, setFalhou] = useState(false);
  if (!c.tem_logo || falhou) return <div className="logo-modelo vazio">{c.nome.slice(0, 1).toUpperCase()}</div>;
  return <div className="logo-modelo"><img src={urlLogoMinerado(c.id)} alt="" onError={() => setFalhou(true)} /></div>;
}

/** Nota 0–100: metade é o surto, 30% o ritmo do canal, 20% ser jovem (ver _nota em mineracao.py). */
function Nota({ n }: { n: number }) {
  const t = useT();
  const faixa = n >= 70 ? "alta" : n >= 45 ? "media" : "baixa";
  return <div className={`nota-mina ${faixa}`}><b>{Math.round(n)}</b><span>{t("app.mina.nota")}</span></div>;
}

function CartaoMinerado({ c, aba }: { c: CanalMinerado; aba: Aba }) {
  const t = useT();
  const qc = useQueryClient();
  const [notas, setNotas] = useState(c.notas);
  const recarregar = () => qc.invalidateQueries({ queryKey: CHAVE });
  const salvarNotas = useMutation({ mutationFn: (texto: string) => enviar(`/api/mineracao/${c.id}/notas`, { notas: texto }) });
  const modelar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${c.id}/modelar`), onSettled: recarregar });
  const descartar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${c.id}/descartar`), onSettled: recarregar });
  const voltar = useMutation({ mutationFn: () => enviar(`/api/mineracao/${c.id}/voltar`), onSettled: recarregar });
  const excluir = useMutation({ mutationFn: () => enviar(`/api/mineracao/${c.id}/excluir`), onSettled: recarregar });
  // guarda sozinho um instante depois de você parar de escrever
  useEffect(() => {
    if (notas === c.notas) return;
    const id = setTimeout(() => salvarNotas.mutate(notas), 800);
    return () => clearTimeout(id);
  }, [notas, c.notas]);

  return (
    <div className="modelo minerado">
      <div className="topo">
        <Logo c={c} />
        <div className="t">
          <b>{c.nome}</b>
          <span className="sub">{[c.handle && `@${c.handle}`, c.pais, c.meses ? t("app.mina.meses", { n: c.meses }) : ""].filter(Boolean).join(" · ")}</span>
        </div>
        <Nota n={c.nota} />
      </div>
      <div className="nums quatro">
        <div className="num"><b>{c.surto}x</b><span>{t("app.mina.surto")}</span></div>
        <div className="num"><b>{compacto(c.inscritos)}</b><span>{t("app.mina.inscritos")}</span></div>
        <div className="num"><b>{compacto(c.vistas_dia)}</b><span>{t("app.mina.vistas_dia")}</span></div>
        <div className="num"><b>{compacto(c.videos)}</b><span>{t("app.modelar.videos")}</span></div>
      </div>
      <a className="estourou" href={c.video_url} target="_blank" rel="noreferrer noopener">
        <span className="rot">{t("app.mina.estourou")}</span>
        <b>{c.video_titulo}</b>
        <span className="sub">{t("app.mina.estourou_sub", { vistas: compacto(c.video_vistas), quando: c.video_quando, veio: c.de_veio })}</span>
      </a>
      <textarea className="notas" rows={2} value={notas} placeholder={t("app.mina.notas_dica")}
                onChange={(e) => setNotas(e.target.value)} />
      {modelar.isError && <p className="erro">{modelar.error.message}</p>}
      <div className="acoes">
        <a className="bt pequeno" href={c.url} target="_blank" rel="noreferrer noopener">
          <ExternalLink size={14} />{t("app.mina.abrir")}
        </a>
        {aba === "novo" && (
          <>
            <button className="bt pequeno primario" disabled={modelar.isPending} onClick={() => modelar.mutate()}>
              <Target size={14} />{t(modelar.isPending ? "app.mina.modelando" : "app.mina.modelar")}
            </button>
            <button className="bt pequeno so-icone" title={t("app.mina.descartar_dica")}
                    disabled={descartar.isPending} onClick={() => descartar.mutate()}>
              <X size={15} />
            </button>
          </>
        )}
        {aba !== "novo" && (
          <>
            {aba === "descartado" && (
              <button className="bt pequeno" disabled={voltar.isPending} onClick={() => voltar.mutate()}>
                <Undo2 size={14} />{t("app.mina.voltar")}
              </button>
            )}
            <button className="bt pequeno so-icone" title={t("app.mina.excluir")}
                    disabled={excluir.isPending} onClick={() => excluir.mutate()}>
              <Trash2 size={14} />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function Veios({ d }: { d: EstadoMina }) {
  const proximos = new Set(d.proximos);
  const t = useT();
  const qc = useQueryClient();
  const [termo, setTermo] = useState("");
  const [canal, setCanal] = useState(d.canais[0]?.slug ?? "");
  const [sugeridos, setSugeridos] = useState<string[] | null>(null);
  const recarregar = () => qc.invalidateQueries({ queryKey: CHAVE });
  const guardar = useMutation({
    mutationFn: (texto: string) => enviar("/api/mineracao/veios", { termo: texto }),
    onSuccess: (_r, texto) => { setTermo(""); setSugeridos((s) => s && s.filter((x) => x !== texto)); recarregar(); },
  });
  const alternar = useMutation({
    mutationFn: (v: Veio) => enviar(`/api/mineracao/veios/${v.id}`, { ativo: !v.ativo }),
    onSettled: recarregar,
  });
  const apagar = useMutation({ mutationFn: (v: Veio) => enviar(`/api/mineracao/veios/${v.id}/excluir`), onSettled: recarregar });
  const sugerir = useMutation({
    mutationFn: () => enviar<{ termos: string[] }>("/api/mineracao/veios/sugerir", { canal }),
    onSuccess: (r) => setSugeridos(r.termos),
  });

  return (
    <div className="veios">
      <div className="chips">
        {d.veios.map((v) => (
          <span key={v.id} className={`veio ${v.ativo ? "on" : ""} ${proximos.has(v.termo) ? "proximo" : ""}`}
                title={[v.origem === "claude" ? t("app.mina.veio_do_claude") : "",
                        v.ultimo ? t("app.mina.veio_ultimo", { quando: v.ultimo }) : t("app.mina.veio_nunca")]
                        .filter(Boolean).join(" · ")}>
            <button className="lig" title={t(v.ativo ? "app.mina.veio_desligar" : "app.mina.veio_ligar")}
                    onClick={() => alternar.mutate(v)}><Power size={12} /></button>
            {v.termo}
            <button className="x" title={t("app.mina.veio_excluir")} onClick={() => apagar.mutate(v)}><X size={12} /></button>
          </span>
        ))}
        {d.veios.length === 0 && <p className="sub">{t("app.mina.veios_vazio")}</p>}
      </div>
      {d.proximos.length < d.veios.filter((v) => v.ativo).length && (
        <p className="sub dica">{t("app.mina.rodizio", { n: d.por_garimpo, total: d.veios.filter((v) => v.ativo).length })}</p>
      )}

      <div className="linha-veio">
        <form onSubmit={(e) => { e.preventDefault(); guardar.mutate(termo); }}>
          <label className="campo">
            {t("app.mina.veio_novo")}
            <input value={termo} placeholder={t("app.mina.veio_colar")} onChange={(e) => setTermo(e.target.value)} />
          </label>
          <button className="bt" disabled={termo.trim().length < 2 || guardar.isPending}>
            <Plus size={15} />{t("app.mina.veio_add")}
          </button>
        </form>
        {d.canais.length > 0 && (
          <div className="do-claude">
            <select value={canal} onChange={(e) => setCanal(e.target.value)}>
              {d.canais.map((c) => <option key={c.slug} value={c.slug}>{c.nome}</option>)}
            </select>
            <button className="bt" disabled={sugerir.isPending} onClick={() => sugerir.mutate()}>
              <Sparkles size={15} />{t(sugerir.isPending ? "app.mina.sugerindo" : "app.mina.sugerir")}
            </button>
          </div>
        )}
      </div>
      <p className="sub dica">{t("app.mina.sugerir_sub")}</p>
      {guardar.isError && <p className="erro">{guardar.error.message}</p>}
      {sugerir.isError && <p className="erro">{sugerir.error.message}</p>}
      {sugeridos && (
        <div className="sugeridos">
          <p className="sub">{t("app.mina.sugeridos", { n: sugeridos.length })}</p>
          <div className="chips">
            {sugeridos.map((s) => (
              <button key={s} className="veio prop" onClick={() => guardar.mutate(s)}><Plus size={12} />{s}</button>
            ))}
          </div>
        </div>
      )}
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
  { id: "por_veio", rot: "app.mina.f_por_veio" },
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
              <input value={String(f[c.id])} maxLength={5}
                     onChange={(e) => setF({ ...f, [c.id]: e.target.value })} />
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
  const { data } = useQuery({ queryKey: [...CHAVE, aba], queryFn: () => pegar<EstadoMina>(`/api/mineracao?situacao=${aba}`) });
  const garimpar = useMutation({
    mutationFn: () => enviar<{ resumo: { olhados: number; aprovados: number; novos: number; cota: number } }>("/api/mineracao/garimpar"),
    onSettled: () => qc.invalidateQueries({ queryKey: CHAVE }),
  });
  const auto = useMutation({
    mutationFn: (ligado: boolean) => enviar("/api/mineracao/filtros", { automatico: ligado }),
    onSettled: () => qc.invalidateQueries({ queryKey: CHAVE }),
  });
  if (!data) return <div className="nivel-produtor"><TopoProdutor /></div>;
  const ligados = data.veios.filter((v) => v.ativo).length;
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
            <div>
              <b>{t("app.mina.garimpo")}</b>
              <span className="sub">{t("app.mina.garimpo_sub", { n: data.custo_busca })}</span>
            </div>
            <button className="bt primario" disabled={!ligados || garimpar.isPending || !data.tem_chave}
                    onClick={() => garimpar.mutate()}>
              <Pickaxe size={16} />{t(garimpar.isPending ? "app.mina.garimpando" : "app.mina.garimpar")}
            </button>
          </header>
          <Veios d={data} />
          {garimpar.isError && <p className="erro">{garimpar.error.message}</p>}
          {garimpar.data && <p className="ok-mina">{t("app.mina.resumo", { ...garimpar.data.resumo })}</p>}
          <footer>
            <span title={t("app.mina.cota_sub")}>{t("app.mina.cota", { usada: data.cota.usada, limite: data.cota.limite })}</span>
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
        </nav>

        {data.itens.length > 0 ? (
          <div className="modelos garimpados">{data.itens.map((c) => <CartaoMinerado key={c.id} c={c} aba={aba} />)}</div>
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
