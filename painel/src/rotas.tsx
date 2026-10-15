// Dois níveis: /  = seus canais (do produtor) · /c/<canal>/... = a produção daquele canal.
import { createBrowserRouter, Outlet, useRouteError } from "react-router-dom";
import { useAoVivo } from "./aoVivo";
import { CascaCanal } from "./casca/CascaCanal";
import { EscolhaCanais } from "./telas/EscolhaCanais";
import { EsperandoCanal, VideosCanal } from "./telas/ListasCanal";
import { ProducaoCanal } from "./telas/ProducaoCanal";
import { useSistema, useT } from "./textos";

function Raiz() {
  useAoVivo();
  // sem os textos, a tela mostraria as chaves ("app.canais...") por um instante
  const { data, error } = useSistema();
  if (error) throw error;
  return data ? <Outlet /> : null;
}

function Erro() {
  // rota "*" não tem erro: é página que não existe
  const erro = (useRouteError() ?? { status: 404 }) as { message?: string; status?: number };
  const t = useT();
  return (
    <div className="erro-tela">
      <h1>{erro?.status === 404 ? t("app.erro.nao_achei") : t("app.erro.titulo")}</h1>
      <p className="sub">{erro?.message}</p>
      <a className="bt" href="/app/">{t("app.erro.voltar")}</a>
    </div>
  );
}

export const rotas = createBrowserRouter(
  [
    {
      element: <Raiz />,
      errorElement: <Erro />,
      children: [
        { path: "/", element: <EscolhaCanais /> },
        {
          path: "/c/:canal",
          element: <CascaCanal />,
          children: [
            { index: true, element: <ProducaoCanal /> },
            { path: "videos", element: <VideosCanal /> },
            { path: "esperando", element: <EsperandoCanal /> },
          ],
        },
        { path: "*", element: <Erro /> },
      ],
    },
  ],
  { basename: "/app" },
);
