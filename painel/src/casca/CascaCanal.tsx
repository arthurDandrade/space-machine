// Moldura de tudo o que é de um canal: barra lateral (troca de canal no topo, navegação, novo vídeo) + a tela.
// A cor de destaque do canal vira --accent em toda a moldura.
import { useEffect } from "react";
import { NavLink, useLocation, useNavigate, useOutlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen, CalendarDays, ChevronsUpDown, Clapperboard, Columns3, Hand, KeyRound, LayoutDashboard, Lightbulb, ListChecks,
  Palette, Plus, Settings,
} from "lucide-react";
import { Link } from "react-router-dom";
import { PainelCanal, pegar, rota } from "../api";
import { LogoCanal } from "../componentes/Imagens";
import { useT } from "../textos";

export const useCanal = (slug: string) =>
  useQuery({ queryKey: ["canal", slug], queryFn: () => pegar<PainelCanal>(`/api/c/${slug}`) });

type Item = { rot: string; icone: typeof Hand; para: string; fim?: boolean; contador?: number };

export function CascaCanal() {
  const { canal = "" } = useParams();
  const { data, error } = useCanal(canal);
  const t = useT();
  const navegar = useNavigate();
  const local = useLocation();
  // useOutlet (e não <Outlet/>): na transição a tela que sai continua sendo a antiga
  const tela = useOutlet();

  // Esc volta para a escolha de canais (fora de campos de texto)
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      const alvo = e.target as HTMLElement;
      if (e.key === "Escape" && !alvo.closest("input, textarea, select, [role=dialog]")) navegar("/");
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [navegar]);

  if (error) throw error;
  const c = data?.canal;
  const itens: (Item | string)[] = [
    { rot: "app.nav.producao", icone: LayoutDashboard, para: `/c/${canal}`, fim: true },
    { rot: "app.nav.videos", icone: Clapperboard, para: `/c/${canal}/videos` },
    { rot: "app.nav.quadro", icone: Columns3, para: rota.quadro(canal) },
    { rot: "app.nav.esperando", icone: Hand, para: `/c/${canal}/esperando`, contador: c?.esperando },
    { rot: "app.nav.ideias", icone: Lightbulb, para: rota.ideias(canal) },
    { rot: "app.nav.calendario", icone: CalendarDays, para: rota.calendario(canal) },
    "app.nav.secao_canal",
    { rot: "app.nav.identidade", icone: Palette, para: `/c/${canal}/identidade` },
    { rot: "regras.titulo", icone: ListChecks, para: `/c/${canal}/regras` },
    { rot: "app.nav.aprendizados", icone: BookOpen, para: `/c/${canal}/aprendizados` },
    { rot: "app.nav.chaves", icone: KeyRound, para: `/c/${canal}/chaves` },
  ];

  return (
    <div className="app" style={c?.cores.cor_destaque ? ({ "--accent": c.cores.cor_destaque } as React.CSSProperties) : undefined}>
      <aside className="lado">
        <button className="troca" onClick={() => navegar("/")} title={t("app.nav.trocar_dica")}>
          {c ? <LogoCanal canal={canal} nome={c.nome} cores={c.cores} tem={c.logo} /> : <div className="logo-canal" />}
          <div>
            <b>{c?.nome ?? "…"}</b>
            <span>{t("app.nav.trocar")}</span>
          </div>
          <ChevronsUpDown size={16} />
        </button>
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
            <span className="av"><Settings size={16} /></span>
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
