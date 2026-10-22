// Moldura de tudo o que é de um canal: barra lateral (troca de canal no topo, navegação, novo vídeo) + a tela.
// A cor de destaque do canal vira --accent em toda a moldura.
import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation, useNavigate, useOutlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen, CalendarDays, Check, ChevronsUpDown, Clapperboard, Columns3, Hand, KeyRound, LayoutDashboard, LayoutGrid, Lightbulb,
  ListChecks, ScrollText, Palette, Plus, Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Canais, PainelCanal, pegar, rota } from "../api";
import { LogoCanal } from "../componentes/Imagens";
import { useT } from "../textos";

export const useCanal = (slug: string) =>
  useQuery({ queryKey: ["canal", slug], queryFn: () => pegar<PainelCanal>(`/api/c/${slug}`) });

/** Abinha do topo da barra: lista os canais e entra em outro sem passar pela tela de escolha. */
function TrocarCanal({ canal, nome, cores, logo, aberto, setAberto }:
{ canal: string; nome?: string; cores?: PainelCanal["canal"]["cores"]; logo?: boolean; aberto: boolean; setAberto: (v: boolean) => void }) {
  const t = useT();
  const navegar = useNavigate();
  const caixa = useRef<HTMLDivElement>(null);
  // a lista só é buscada (e atualizada) enquanto a abinha está aberta
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais"), enabled: aberto });
  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => { if (!caixa.current?.contains(e.target as Node)) setAberto(false); };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [aberto, setAberto]);

  return (
    <div className="troca-canal" ref={caixa}>
      <button className={`troca ${aberto ? "aberta" : ""}`} onClick={() => setAberto(!aberto)} title={t("app.nav.trocar_dica")}
              aria-expanded={aberto} aria-haspopup="menu">
        {nome && cores ? <LogoCanal canal={canal} nome={nome} cores={cores} tem={!!logo} /> : <div className="logo-canal" />}
        <div>
          <b>{nome ?? "…"}</b>
          <span>{t("app.nav.trocar")}</span>
        </div>
        <ChevronsUpDown size={16} />
      </button>
      <AnimatePresence>
        {aberto && (
          <motion.div className="abinha-canais" role="menu" initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.14, ease: [0.2, 0.8, 0.2, 1] }}>
            {(data?.canais ?? []).map((o) => (
              <button key={o.slug} role="menuitem" className={`linha ${o.slug === canal ? "atual" : ""} ${o.ativo ? "" : "inativo"}`}
                      onClick={() => { setAberto(false); if (o.slug !== canal) navegar(`/c/${o.slug}`); }}>
                <LogoCanal canal={o.slug} nome={o.nome} cores={o.cores} tem={o.logo} className="pequena" />
                <span className="t">{o.nome}{!o.ativo && <em> · {t("app.canais.inativo")}</em>}</span>
                {!!o.esperando && <span className="qt">{o.esperando}</span>}
                {o.slug === canal && <Check size={15} />}
              </button>
            ))}
            {!data && <div className="linha vazia">{t("app.carregando")}</div>}
            <button role="menuitem" className="linha todos" onClick={() => { setAberto(false); navegar("/"); }}>
              <LayoutGrid size={16} />{t("app.nav.todos_canais")}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

type Item = { rot: string; icone: typeof Hand; para: string; fim?: boolean; contador?: number };

export function CascaCanal() {
  const { canal = "" } = useParams();
  const { data, error } = useCanal(canal);
  const t = useT();
  const navegar = useNavigate();
  const local = useLocation();
  // useOutlet (e não <Outlet/>): na transição a tela que sai continua sendo a antiga
  const tela = useOutlet();
  const [trocando, setTrocando] = useState(false);

  // Esc fecha a abinha de canais; com ela fechada, volta para a escolha de canais (fora de campos de texto)
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement;
      if (e.key !== "Escape" || alvo.closest("input, textarea, select, [role=dialog]")) return;
      if (trocando) setTrocando(false);
      else navegar("/");
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [navegar, trocando]);

  if (error) throw error;
  const c = data?.canal;
  // três grupos, pelo que você veio fazer: acompanhar o que está rodando, planejar o que vem, ajustar o canal
  const itens: (Item | string)[] = [
    "app.nav.secao_acompanhar",
    { rot: "app.nav.producao", icone: LayoutDashboard, para: `/c/${canal}`, fim: true },
    { rot: "app.nav.videos", icone: Clapperboard, para: `/c/${canal}/videos` },
    { rot: "app.nav.esperando", icone: Hand, para: `/c/${canal}/esperando`, contador: c?.esperando },
    "app.nav.secao_planejar",
    { rot: "app.nav.quadro", icone: Columns3, para: rota.quadro(canal) },
    { rot: "app.nav.ideias", icone: Lightbulb, para: rota.ideias(canal) },
    { rot: "app.nav.calendario", icone: CalendarDays, para: rota.calendario(canal) },
    { rot: "app.nav.prompts", icone: ScrollText, para: `/c/${canal}/prompts` },
    "app.nav.secao_ajustes",
    { rot: "app.nav.identidade", icone: Palette, para: `/c/${canal}/identidade` },
    { rot: "regras.titulo", icone: ListChecks, para: `/c/${canal}/regras` },
    { rot: "app.nav.aprendizados", icone: BookOpen, para: `/c/${canal}/aprendizados` },
    { rot: "app.nav.modelos", icone: Sparkles, para: `/c/${canal}/modelos` },
    { rot: "app.nav.chaves", icone: KeyRound, para: `/c/${canal}/chaves` },
  ];

  return (
    <div className="app" style={c?.cores.cor_destaque ? ({ "--accent": c.cores.cor_destaque } as React.CSSProperties) : undefined}>
      <aside className="lado">
        <TrocarCanal canal={canal} nome={c?.nome} cores={c?.cores} logo={c?.logo} aberto={trocando} setAberto={setTrocando} />
        <nav className="nav">
          {itens.map((it) =>
            typeof it === "string" ? (
              <div className="rot" key={it}>{t(it)}</div>
            ) : (
              <NavLink key={it.rot} to={it.para} end={it.fim}>
                <it.icone size={18} />
                {t(it.rot)}
                {!!it.contador && <span className="qt">{it.contador}</span>}
              </NavLink>
            ),
          )}
        </nav>
        <div className="pe">
          <Link className="bt escuro" to={rota.novoVideo(canal)}><Plus size={18} />{t("app.novo_video")}</Link>
          <Link className="conta" to="/config">
            <img className="av" src="/icone-128.png" alt="" />
            {t("app.nav.space_machine")}
          </Link>
        </div>
      </aside>
      <main className="principal">
        <AnimatePresence mode="wait">
          <motion.div key={local.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}>
            {data ? tela : <div className="carregando">{t("app.carregando")}</div>}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
