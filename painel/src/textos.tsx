// Textos do painel: os mesmos space_machine/textos/<idioma>.json do painel antigo, entregues por /api/sistema.
// Uso: const t = useT(); t("app.canais.titulo"). Chave que falta aparece como a própria chave (fácil de achar).
import { useQuery } from "@tanstack/react-query";
import { pegar, Sistema } from "./api";

export function useSistema() {
  return useQuery({ queryKey: ["sistema"], queryFn: () => pegar<Sistema>("/api/sistema"), staleTime: 60_000 });
}

export function useT() {
  const { data } = useSistema();
  const textos = data?.textos ?? {};
  // padrao: o que mostrar quando a chave não existe (ex.: nome de etapa que veio do motor e não tem tradução)
  return (chave: string, valores?: Record<string, string | number>, padrao?: string) => {
    // plural: com {n} = 1 ou 0, a chave "_1" / "_0" vence quando existe ("1 bloco", "nenhum vídeo")
    const n = valores?.n;
    const forma = n === 1 || n === 0 ? textos[`${chave}_${n}`] : undefined;
    let s = forma ?? textos[chave] ?? padrao ?? chave;
    if (valores) for (const [k, v] of Object.entries(valores)) s = s.replaceAll(`{${k}}`, String(v));
    return s;
  };
}

// números: 14901276 → "14,9 M"; 4538 → "4,5 mil"; 12 → "12"
export function compacto(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} M`;
  if (n >= 10_000) return `${Math.round(n / 1000)} mil`;
  if (n >= 1000) return `${(n / 1000).toFixed(1).replace(".", ",")} mil`;
  return String(Math.round(n));
}

export function saudacao(t: ReturnType<typeof useT>) {
  const h = new Date().getHours();
  return t(h < 5 ? "app.boa_noite" : h < 12 ? "app.bom_dia" : h < 18 ? "app.boa_tarde" : "app.boa_noite");
}

// "há 4 min", "há 2 h"
export function haQuanto(t: ReturnType<typeof useT>, ts: number | null) {
  if (!ts) return "";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return t("app.agora");
  if (s < 3600) return t("app.ha_min", { n: Math.floor(s / 60) });
  if (s < 86400) return t("app.ha_h", { n: Math.floor(s / 3600) });
  return t("app.ha_dias", { n: Math.floor(s / 86400) });
}
