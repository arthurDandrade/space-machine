// Topo de cada tela de canal: onde você está, o título e as ações da tela; o botão de tema fica sempre à direita.
import { ReactNode } from "react";
import { Moon, Sun } from "lucide-react";
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

export function Cabecalho({ onde, titulo, children }: { onde: ReactNode; titulo: ReactNode; children?: ReactNode }) {
  return (
    <header className="cabecalho">
      <div>
        <div className="onde">{onde}</div>
        <h1>{titulo}</h1>
      </div>
      <div className="acoes">
        {children}
        <BotaoTema />
      </div>
    </header>
  );
}
