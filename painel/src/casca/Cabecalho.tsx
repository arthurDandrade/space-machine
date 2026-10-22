// Topo de cada tela de canal: o título, uma linha dizendo para que a tela serve e as ações dela; busca, avisos e
// tema ficam sempre à direita. O caminho (`onde`) só aparece onde é caminho de verdade — vídeo e bloco, que estão
// dentro de outra coisa. Nas telas de primeiro nível a barra lateral já diz o canal e em que tela você está.
import { ReactNode } from "react";
import { Moon, Sun } from "lucide-react";
import { Sino } from "../componentes/Avisos";
import { BotaoBusca } from "../componentes/Busca";
import { useTema } from "../tema";
import { useT } from "../textos";

export function BotaoTema() {
  const { tema, alternar } = useTema();
  const t = useT();
  return (
    <button className="bt redondo" onClick={alternar} title={t(tema === "escuro" ? "app.tema.claro" : "app.tema.escuro")}>
      {tema === "escuro" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

export function Cabecalho({ onde, titulo, sub, children }:
{ onde?: ReactNode; titulo: ReactNode; sub?: ReactNode; children?: ReactNode }) {
  return (
    <header className="cabecalho">
      <div>
        {onde && <div className="onde">{onde}</div>}
        <h1>{titulo}</h1>
        {sub && <p className="sub">{sub}</p>}
      </div>
      <div className="acoes">
        {children}
        <BotaoBusca />
        <Sino />
        <BotaoTema />
      </div>
    </header>
  );
}
