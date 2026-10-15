// Tema claro/escuro. Sem escolha, segue o Mac; a escolha fica guardada neste navegador (localStorage).
import { useEffect, useState } from "react";

type Tema = "claro" | "escuro";

const doMac = () => (window.matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro");

function guardado(): Tema | null {
  try {
    const t = localStorage.getItem("sm-tema");
    return t === "claro" || t === "escuro" ? t : null;
  } catch {
    return null;
  }
}

export function useTema() {
  const [tema, setTema] = useState<Tema>(() => guardado() ?? doMac());
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const mudou = () => !guardado() && setTema(doMac());
    mq.addEventListener("change", mudou);
    return () => mq.removeEventListener("change", mudou);
  }, []);
  const alternar = () => {
    const novo: Tema = tema === "escuro" ? "claro" : "escuro";
    document.documentElement.dataset.theme = novo;
    try {
      localStorage.setItem("sm-tema", novo);
    } catch {
      /* navegador sem armazenamento: vale só nesta aba */
    }
    setTema(novo);
  };
  return { tema, alternar };
}
