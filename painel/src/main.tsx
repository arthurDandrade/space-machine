import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import "@fontsource-variable/plus-jakarta-sans";
import "./estilo/base.css";
import "./estilo/casca.css";
import "./estilo/telas.css";
import { rotas } from "./rotas";

// sem refetch ao focar a janela: quem avisa que algo mudou é /api/eventos (aoVivo.ts); 30 s é a rede de segurança
const qc = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, refetchInterval: 30_000, retry: 1, staleTime: 2_000 } },
});

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <RouterProvider router={rotas} />
    </QueryClientProvider>
  </StrictMode>,
);
