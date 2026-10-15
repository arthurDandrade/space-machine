// Dois níveis: /  = seus canais (do produtor) · /c/<canal>/... = a produção daquele canal.
import { createBrowserRouter, Navigate, Outlet, useRouteError } from "react-router-dom";
import { useAoVivo } from "./aoVivo";
import { BaloesDeAviso } from "./componentes/Avisos";
import { Busca } from "./componentes/Busca";
import { CascaCanal } from "./casca/CascaCanal";
import { CascaProdutor } from "./casca/TopoProdutor";
import { AprendizadosTela, ChavesTela, IdentidadeTela, RegrasTela } from "./telas/ConfigCanal";
import { CanaisConfigTela, ConsumoTela, ModelosTela, PassosTela } from "./telas/Produtor";
import { BlocoTela } from "./telas/Bloco";
import { EscolhaCanais } from "./telas/EscolhaCanais";
import { EsperandoCanal, VideosCanal } from "./telas/ListasCanal";
import { CalendarioTela, IdeiasTela, NovoVideoTela, QuadroTela } from "./telas/Planejamento";
import { ProducaoCanal } from "./telas/ProducaoCanal";
import { PromptsTela } from "./telas/Prompts";
import { VideoTela } from "./telas/Video";
import { useSistema, useT } from "./textos";

function Raiz() {
  useAoVivo();
  // sem os textos, a tela mostraria as chaves ("app.canais...") por um instante
  const { data, error } = useSistema();
  if (error) throw error;
  if (!data) return null;
  return (
    <>
      <Outlet />
      <Busca />
      <BaloesDeAviso />
    </>
  );
}

function Erro() {
  // rota "*" não tem erro: é página que não existe
  const erro = (useRouteError() ?? { status: 404 }) as { message?: string; status?: number };
  const t = useT();
  return (
    <div className="erro-tela">
      <h1>{erro?.status === 404 ? t("app.erro.nao_achei") : t("app.erro.titulo")}</h1>
      <p className="sub">{erro?.message}</p>
      <a className="bt" href="/">{t("app.erro.voltar")}</a>
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
          path: "/config",
          element: <CascaProdutor />,
          children: [
            { index: true, element: <Navigate to="canais" replace /> },
            { path: "canais", element: <CanaisConfigTela /> },
            { path: "modelos", element: <ModelosTela /> },
            { path: "consumo", element: <ConsumoTela /> },
            { path: "passos", element: <PassosTela /> },
          ],
        },
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
            { path: "prompts", element: <PromptsTela /> },
            { path: "novo", element: <NovoVideoTela /> },
            { path: "identidade", element: <IdentidadeTela /> },
            { path: "regras", element: <RegrasTela /> },
            { path: "aprendizados", element: <AprendizadosTela /> },
            { path: "chaves", element: <ChavesTela /> },
            { path: "v/:video", element: <VideoTela /> },
            { path: "v/:video/b/:nn", element: <BlocoTela /> },
          ],
        },
        { path: "*", element: <Erro /> },
      ],
    },
  ],
);
