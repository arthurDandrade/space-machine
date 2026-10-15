// Título que copia ao clicar (como no Dark Planner): passa o mouse, clica, o texto vai para a área de transferência.
// Dentro de um card que é link, o clique copia e não navega.
import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { useT } from "../textos";

// copia para a área de transferência; se o navegador negar a API nova, usa o jeito antigo (execCommand)
export async function copiarTexto(texto: string) {
  try {
    await navigator.clipboard.writeText(texto);
    return;
  } catch {
    /* sem permissão: vai pelo jeito antigo */
  }
  const area = document.createElement("textarea");
  area.value = texto;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  document.execCommand("copy");
  area.remove();
}

export function TituloCopiavel({ texto, className = "" }: { texto: string; className?: string }) {
  const t = useT();
  const [copiado, setCopiado] = useState(false);
  const copiar = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    await copiarTexto(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1300);
  };
  return (
    <span className={`copiavel ${copiado ? "copiado" : ""} ${className}`} onClick={copiar} title={t("app.copiar.dica")} role="button">
      {texto}
      <span className="sinal-copiar">{copiado ? <><Check size={12} />{t("app.copiar.feito")}</> : <Copy size={12} />}</span>
    </span>
  );
}
