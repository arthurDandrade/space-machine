// Nível do produtor: o painel sempre abre aqui. Um card por canal; escolher um entra na produção dele.
// Teclas 1–9 entram direto no canal daquela posição.
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ChartPie, Hand, Loader, Plus, Settings, Sparkles } from "lucide-react";
import { antiga, Canais, pegar, ResumoCanal, urlCapa, urlMarca } from "../api";
import { BotaoTema } from "../casca/Cabecalho";
import { Capa, fundoDoCanal, iniciais, LogoCanal } from "../componentes/Imagens";
import { compacto, saudacao, useT } from "../textos";

function Marca() {
  return (
    <div className="marca-sm">
      <i>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M3 12c0-2 4-4.5 9-4.5s9 2.5 9 4.5-4 4.5-9 4.5S3 14 3 12z" />
        </svg>
      </i>
      Space Machine
    </div>
  );
}

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
            <Capa className="th" src={urlCapa(c.slug, c.atual.slug)} />
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

  const agora = [
    data?.rodando ? t(data.rodando === 1 ? "app.canais.um_rodando" : "app.canais.n_rodando", { n: data.rodando }) : "",
    data?.esperando ? t("app.esperando_n", { n: data.esperando }) : "",
  ].filter(Boolean);

  return (
    <div className="nivel-produtor">
      <div className="topo-produtor">
        <Marca />
        <div className="esp" />
        <a className={`chip ${data?.falta_algo ? "alerta" : ""}`} href={antiga.primeirosPassos}>
          <span className="ponto" /><span className="txt">{t(data?.falta_algo ? "app.produtor.falta" : "app.produtor.tudo_ok")}</span>
        </a>
        <a className="chip" href={antiga.consumo}><ChartPie size={16} /><span className="txt">{t("app.produtor.consumo")}</span></a>
        <a className="chip" href={antiga.modelos} title={t("app.produtor.config")}><Settings size={16} /></a>
        <BotaoTema />
      </div>

      <section className="ola">
        <h1>{saudacao(t)}.</h1>
        <p>
          {t(canais.length ? "app.canais.escolha" : "app.canais.primeiro")}
          {agora.length > 0 && <> {t("app.canais.agora")} <b>{agora.join(` ${t("app.e")} `)}</b>.</>}
        </p>
      </section>

      <div className="canais">
        {canais.map((c, i) => <CartaoCanal key={c.slug} c={c} i={i} />)}
        <a className="canal novo" href={antiga.novoCanal} style={{ animationDelay: `${canais.length * 60}ms` }}>
          <span className="mais"><Plus size={22} /></span>
          <b>{t("app.canais.novo")}</b>
          <span className="sub">{t("app.canais.novo_sub")}</span>
        </a>
      </div>

      {canais.length > 0 && (
        <div className="rodape-produtor">
          <div className="mini"><span className="ic run"><Loader size={18} /></span>
            <div><b>{t(data?.rodando === 1 ? "app.canais.um_rodando" : "app.canais.n_rodando", { n: data?.rodando ?? 0 })}</b>
              <span>{t("app.canais.em_todos")}</span></div></div>
          <div className="mini"><span className="ic wait"><Hand size={18} /></span>
            <div><b>{t("app.esperando_n", { n: data?.esperando ?? 0 })}</b><span>{t("app.canais.em_todos")}</span></div></div>
          <div className="mini"><span className="ic ok"><Sparkles size={18} /></span>
            <div><b>{t("app.canais.tokens", { n: compacto(data?.consumo_7d ?? 0) })}</b><span>{t("app.canais.claude_7d")}</span></div></div>
        </div>
      )}
    </div>
  );
}
