// Dois níveis: /  = seus canais (do produtor) · /c/<canal>/... = a produção daquele canal.
import { createBrowserRouter, Outlet, useRouteError } from "react-router-dom";
import { useAoVivo } from "./aoVivo";
import { CascaCanal } from "./casca/CascaCanal";
import { BlocoTela } from "./telas/Bloco";
import { EscolhaCanais } from "./telas/EscolhaCanais";
import { EsperandoCanal, VideosCanal } from "./telas/ListasCanal";
import { CalendarioTela, IdeiasTela, NovoVideoTela, QuadroTela } from "./telas/Planejamento";
import { ProducaoCanal } from "./telas/ProducaoCanal";
import { VideoTela } from "./telas/Video";
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
            { path: "quadro", element: <QuadroTela /> },
            { path: "ideias", element: <IdeiasTela /> },
            { path: "calendario", element: <CalendarioTela /> },
            { path: "novo", element: <NovoVideoTela /> },
            { path: "v/:video", element: <VideoTela /> },
            { path: "v/:video/b/:nn", element: <BlocoTela /> },
          ],
        },
        { path: "*", element: <Erro /> },
      ],
    },
  ],
  { basename: "/app" },
);
