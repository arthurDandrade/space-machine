// Atualização ao vivo: /api/eventos manda um aviso quando alguma pasta de produção muda; aí os dados na tela são
// pedidos de novo (sem recarregar a página nem reiniciar um vídeo tocando).
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useAoVivo() {
  const qc = useQueryClient();
  useEffect(() => {
    // ?sem-ao-vivo: sem a conexão aberta, o Chrome headless consegue esperar a página e tirar o print
    if (new URLSearchParams(window.location.search).has("sem-ao-vivo")) return;
    let ultima = "";
    const fonte = new EventSource("/api/eventos");
    fonte.onmessage = (e) => {
      if (ultima && e.data !== ultima) qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "sistema" });
      ultima = e.data;
    };
    return () => fonte.close();
  }, [qc]);
}
