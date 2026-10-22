// Moldura do nível do produtor (fora de um canal): barra de cima com a marca, as três áreas — Início, Modelagem
// e Configurações — e, à direita, busca, situação da instalação, avisos e tema. As Configurações têm barra
// lateral própria, agrupada por assunto, e cada painel abre com título e uma linha dizendo para que serve.
import { ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownToLine, ChartPie, CircleAlert, CircleCheck, LayoutGrid, ListChecks, Settings, Sparkles, Target, Trash2, Tv,
} from "lucide-react";
import { Canais, pegar } from "../api";
import { useSistema, useT } from "../textos";
import { Sino } from "../componentes/Avisos";
import { BotaoBusca } from "../componentes/Busca";
import { BotaoTema } from "./Cabecalho";

export function Marca() {
  return (
    <Link to="/" className="marca-sm">
      <img src="/icone-128.png" alt="" />
      Space Machine
    </Link>
  );
}

// as três áreas do produtor; dentro do canal a navegação é outra (CascaCanal)
const AREAS: { para: string; rot: string; icone: typeof LayoutGrid; fim?: boolean }[] = [
  { para: "/", rot: "app.produtor.nav_inicio", icone: LayoutGrid, fim: true },
  { para: "/modelagem", rot: "app.produtor.nav_modelagem", icone: Target },
  { para: "/config", rot: "app.produtor.nav_config", icone: Settings },
];

/** Um chip só para a situação: atualização pendente > falta configurar > tudo instalado. */
function Situacao() {
  const t = useT();
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  const atrasado = useSistema().data?.atualizacao ?? 0;
  if (atrasado > 0)
    return (
      <Link className="chip atualizar" to="/config/atualizar" title={t("app.att.tem", { n: atrasado })}>
        <ArrowDownToLine size={15} /><span className="txt">{t("app.produtor.atualizacao")}</span>
      </Link>
    );
  const falta = !!data?.falta_algo;
  return (
    <Link className={`chip ${falta ? "alerta" : "ok"}`} to="/config/passos">
      {falta ? <CircleAlert size={15} /> : <CircleCheck size={15} />}
      <span className="txt">{t(falta ? "app.produtor.falta" : "app.produtor.tudo_ok")}</span>
    </Link>
  );
}

export function TopoProdutor() {
  const t = useT();
  return (
    <div className="topo-produtor">
      <Marca />
      <nav className="areas">
        {AREAS.map((a) => (
          <NavLink key={a.para} to={a.para} end={a.fim} className={({ isActive }) => (isActive ? "on" : "")}>
            <a.icone size={16} />{t(a.rot)}
          </NavLink>
        ))}
      </nav>
      <div className="esp" />
      <BotaoBusca />
      <Situacao />
      <Sino />
      <BotaoTema />
    </div>
  );
}

/** Cabeçalho de cada tela do produtor: o que é a tela, uma linha de explicação e as ações dela. */
export function CabecaTela({ titulo, sub, children }: { titulo: ReactNode; sub?: ReactNode; children?: ReactNode }) {
  return (
    <header className="cabeca-tela">
      <div>
        <h2>{titulo}</h2>
        {sub && <p className="sub">{sub}</p>}
      </div>
      {children && <div className="acoes">{children}</div>}
    </header>
  );
}

// barra lateral das configurações, por assunto (do canal → da produção → da máquina)
const GRUPOS: { rot: string; itens: { id: string; rot: string; icone: typeof Tv }[] }[] = [
  { rot: "app.config.grupo_canais", itens: [{ id: "canais", rot: "app.config.aba_canais", icone: Tv }] },
  {
    rot: "app.config.grupo_producao",
    itens: [
      { id: "modelos", rot: "app.config.aba_modelos", icone: Sparkles },
      { id: "consumo", rot: "app.config.aba_consumo", icone: ChartPie },
      { id: "limpeza", rot: "app.config.aba_limpeza", icone: Trash2 },
    ],
  },
  {
    rot: "app.config.grupo_sistema",
    itens: [
      { id: "passos", rot: "app.config.aba_passos", icone: ListChecks },
      { id: "atualizar", rot: "app.config.aba_atualizar", icone: ArrowDownToLine },
    ],
  },
];

export function CascaProdutor() {
  const t = useT();
  return (
    <div className="nivel-produtor">
      <TopoProdutor />
      <div className="config-produtor">
        <h1>{t("app.config.titulo")}</h1>
        <p className="sub">{t("app.config.sub")}</p>
        <div className="config-layout">
          <nav className="config-nav">
            {GRUPOS.map((g) => (
              <div key={g.rot} className="grupo">
                <div className="rot">{t(g.rot)}</div>
                {g.itens.map((i) => (
                  <NavLink key={i.id} to={`/config/${i.id}`} className={({ isActive }) => (isActive ? "on" : "")}>
                    <i.icone size={17} />{t(i.rot)}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className="config-painel"><Outlet /></div>
        </div>
      </div>
    </div>
  );
}
