// Topo do nível do produtor (escolha de canais e configurações do Space Machine): marca, situação da instalação,
// consumo, configurações e tema.
import { Link, NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, ChartPie, Settings } from "lucide-react";
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

export function TopoProdutor() {
  const t = useT();
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  const atualizacao = useSistema().data?.atualizacao ?? 0;
  return (
    <div className="topo-produtor">
      <Marca />
      <div className="esp" />
      <BotaoBusca />
      {atualizacao > 0 && (
        <Link className="chip atualizar" to="/config/atualizar" title={t("app.att.tem", { n: atualizacao })}>
          <ArrowDownToLine size={16} /><span className="txt">{t("app.produtor.atualizacao")}</span>
        </Link>
      )}
      <Link className={`chip ${data?.falta_algo ? "alerta" : ""}`} to="/config/passos">
        <span className="ponto" /><span className="txt">{t(data?.falta_algo ? "app.produtor.falta" : "app.produtor.tudo_ok")}</span>
      </Link>
      <Link className="chip" to="/config/consumo"><ChartPie size={16} /><span className="txt">{t("app.produtor.consumo")}</span></Link>
      <Link className="chip" to="/config/canais" title={t("app.produtor.config")}><Settings size={16} /></Link>
      <Sino />
      <BotaoTema />
    </div>
  );
}

const ABAS = [
  ["canais", "app.config.aba_canais"],
  ["modelos", "app.config.aba_modelos"],
  ["consumo", "app.config.aba_consumo"],
  ["limpeza", "app.config.aba_limpeza"],
  ["passos", "app.config.aba_passos"],
  ["atualizar", "app.config.aba_atualizar"],
] as const;

export function CascaProdutor() {
  const t = useT();
  return (
    <div className="nivel-produtor">
      <TopoProdutor />
      <div className="config-produtor">
        <h1>{t("app.config.titulo")}</h1>
        <nav className="abas">
          {ABAS.map(([id, rot]) => <NavLink key={id} to={`/config/${id}`} className={({ isActive }) => (isActive ? "on" : "")}>{t(rot)}</NavLink>)}
        </nav>
        <Outlet />
      </div>
    </div>
  );
}
