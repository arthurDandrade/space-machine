// Início do produtor: o painel sempre abre aqui. A tela tem um trabalho só — escolher em qual canal você vai
// mexer. Saudação, os três números do momento (rodando, esperando, gasto do Claude) e um card por canal.
// Teclas 1–9 entram direto no canal daquela posição.
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Hand, Loader, Plus, Sparkles } from "lucide-react";
import { Canais, pegar, ResumoCanal, urlCapa, urlMarca } from "../api";
import { TopoProdutor } from "../casca/TopoProdutor";
import { Capa, fundoDoCanal, iniciais, LogoCanal } from "../componentes/Imagens";
import { compacto, saudacao, useT } from "../textos";

function CartaoCanal({ c, i }: { c: ResumoCanal; i: number }) {
  const t = useT();
  const estilo = { animationDelay: `${i * 60}ms`, ...(c.cores.cor_destaque ? { "--accent": c.cores.cor_destaque } : {}) } as React.CSSProperties;
  return (
    <Link className={`canal ${c.ativo ? "" : "inativo"}`} to={`/c/${c.slug}`} style={estilo}>
      <div className="capa">
        {c.banner ? (
          <Capa src={urlMarca(c.slug, "banner")} icone={false} />
        ) : (
          <div className="gerado" style={{ background: fundoDoCanal(c.cores) }}>{iniciais(c.nome)}</div>
        )}
        {c.rodando > 0 && (
          <span className="ao-vivo"><span className="pulso" />
            {c.rodando_agora.length ? t("app.canais.rodando_bloco", { nn: c.rodando_agora[0] }) : t("app.canais.rodando")}
          </span>
        )}
        {i < 9 && <span className="tecla">{i + 1}</span>}
      </div>
      <div className="corpo">
        <LogoCanal canal={c.slug} nome={c.nome} cores={c.cores} tem={c.logo} className="grande" />
        <h2>{c.nome}{!c.ativo && <span className="selo neutro">{t("app.canais.inativo")}</span>}</h2>
        <div className="tema">{[c.tema, t(`app.idioma.${c.idioma}`, undefined, c.idioma)].filter(Boolean).join(" · ")}</div>
        <div className="nums">
          <div className="num"><b>{c.colunas.producao}</b><span>{t("app.coluna.producao")}</span></div>
          <div className="num"><b>{c.colunas.edicao_final}</b><span>{t("app.coluna.edicao_final")}</span></div>
          <div className={`num ${c.esperando ? "alerta" : ""}`}><b>{c.esperando}</b><span>{t("app.esperando_voce")}</span></div>
        </div>
        {c.atual ? (
          <div className="atual">
            <Capa className="th" src={urlCapa(c.slug, c.atual.slug, undefined, c.atual.capa_v)} existe={c.atual.tem_capa} />
            <div className="t">{c.atual.titulo}
              <span>{t("app.video.blocos_entregues", { e: c.atual.entregues, n: c.atual.n_blocos })}</span>
            </div>
          </div>
        ) : (
          <div className="atual vazio-atual">
            <div className="t">{t("app.canais.sem_producao")}<span>{t("app.canais.sem_producao_sub")}</span></div>
          </div>
        )}
        <div className="entrar">{t("app.canais.entrar")} <ArrowRight size={18} /></div>
      </div>
    </Link>
  );
}

/** Os três números do momento, ao lado da saudação (antes se repetiam no rodapé da tela). */
function Agora({ data }: { data?: Canais }) {
  const t = useT();
  const itens = [
    { ic: <Loader size={16} />, cls: "run", n: data?.rodando ?? 0, rot: "app.canais.stat_rodando", para: "" },
    { ic: <Hand size={16} />, cls: "wait", n: data?.esperando ?? 0, rot: "app.canais.stat_esperando", para: "" },
    { ic: <Sparkles size={16} />, cls: "ok", n: compacto(data?.consumo_7d ?? 0), rot: "app.canais.stat_tokens", para: "/config/consumo" },
  ];
  return (
    <div className="agora">
      {itens.map((i) => {
        const miolo = <><span className={`ic ${i.cls}`}>{i.ic}</span><div><b>{i.n}</b><span>{t(i.rot)}</span></div></>;
        return i.para
          ? <Link key={i.rot} className="stat" to={i.para}>{miolo}</Link>
          : <div key={i.rot} className="stat">{miolo}</div>;
      })}
    </div>
  );
}

export function EscolhaCanais() {
  const t = useT();
  const navegar = useNavigate();
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  const canais = data?.canais ?? [];

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, textarea, select") || e.metaKey || e.ctrlKey) return;
      const n = Number(e.key);
      if (n >= 1 && n <= 9 && canais[n - 1]) navegar(`/c/${canais[n - 1].slug}`);
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [canais, navegar]);

  return (
    <div className="nivel-produtor">
      <TopoProdutor />

      <section className="ola">
        <div>
          <h1>{saudacao(t)}.</h1>
          {/* enquanto a lista não chega, nenhuma das duas frases: "crie seu primeiro canal" piscava sem motivo */}
          <p>{data ? t(canais.length ? "app.canais.escolha" : "app.canais.primeiro") : " "}</p>
        </div>
        {canais.length > 0 && <Agora data={data} />}
      </section>

      <div className="canais">
        {canais.map((c, i) => <CartaoCanal key={c.slug} c={c} i={i} />)}
        {data && (
          <Link className="canal novo" to="/config/canais?novo=1" style={{ animationDelay: `${canais.length * 60}ms` }}>
            <span className="mais"><Plus size={22} /></span>
            <b>{t("app.canais.novo")}</b>
            <span className="sub">{t("app.canais.novo_sub")}</span>
          </Link>
        )}
      </div>
    </div>
  );
}
