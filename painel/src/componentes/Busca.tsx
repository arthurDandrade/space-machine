// Busca (⌘K / Ctrl+K em qualquer tela): canais, vídeos, blocos (pelo tópico) e as telas do canal atual.
import { useEffect, useState } from "react";
import { useMatch, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Command } from "cmdk";
import { Clapperboard, Film, LayoutDashboard, Search, Settings, Tv } from "lucide-react";
import { pegar, rota } from "../api";
import { useT } from "../textos";

interface Indice {
  canais: { slug: string; nome: string; tema: string }[];
  videos: { canal: string; canal_nome: string; slug: string; titulo: string }[];
  blocos: { canal: string; video: string; video_titulo: string; nn: string; topico: string }[];
}

const abrirBusca = () => window.dispatchEvent(new Event("sm:buscar"));

export function BotaoBusca() {
  const t = useT();
  const mac = navigator.platform.toLowerCase().includes("mac");
  return (
    <button className="busca-botao" onClick={abrirBusca}>
      <Search size={16} /><span>{t("app.busca.buscar")}</span><kbd>{mac ? "⌘K" : "Ctrl K"}</kbd>
    </button>
  );
}

export function Busca() {
  const t = useT();
  const navegar = useNavigate();
  const [aberta, setAberta] = useState(false);
  const noCanal = useMatch("/c/:canal/*")?.params.canal;
  const { data } = useQuery({ queryKey: ["busca"], queryFn: () => pegar<Indice>("/api/busca"), enabled: aberta, staleTime: 15_000 });

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setAberta((a) => !a); }
    };
    const abrir = () => setAberta(true);
    window.addEventListener("keydown", tecla);
    window.addEventListener("sm:buscar", abrir);
    return () => { window.removeEventListener("keydown", tecla); window.removeEventListener("sm:buscar", abrir); };
  }, []);

  const ir = (para: string) => { setAberta(false); navegar(para); };
  // vídeos e blocos do canal em que você está vêm primeiro
  const ordem = <T extends { canal: string }>(l: T[]) => (noCanal ? [...l.filter((x) => x.canal === noCanal), ...l.filter((x) => x.canal !== noCanal)] : l);
  const telas = noCanal
    ? [["app.nav.producao", rota.canal(noCanal)], ["app.nav.videos", `/c/${noCanal}/videos`], ["app.nav.quadro", rota.quadro(noCanal)],
       ["app.nav.esperando", `/c/${noCanal}/esperando`], ["app.nav.ideias", rota.ideias(noCanal)], ["app.nav.calendario", rota.calendario(noCanal)],
       ["app.novo_video", rota.novoVideo(noCanal)], ["app.nav.identidade", `/c/${noCanal}/identidade`], ["regras.titulo", `/c/${noCanal}/regras`],
       ["app.nav.aprendizados", `/c/${noCanal}/aprendizados`], ["app.nav.chaves", `/c/${noCanal}/chaves`]]
    : [];
  const config = [["app.config.aba_canais", "/config/canais"], ["app.config.aba_modelos", "/config/modelos"],
    ["app.config.aba_consumo", "/config/consumo"], ["app.config.aba_passos", "/config/passos"]];

  return (
    <Command.Dialog open={aberta} onOpenChange={setAberta} label={t("app.busca.buscar")} className="busca" overlayClassName="busca-fundo">
      <div className="busca-entrada"><Search size={18} /><Command.Input placeholder={t("app.busca.placeholder")} autoFocus /><kbd>esc</kbd></div>
      <Command.List>
        <Command.Empty>{data ? t("app.busca.nada") : t("app.carregando")}</Command.Empty>
        {telas.length > 0 && (
          <Command.Group heading={t("app.busca.telas")}>
            {telas.map(([rot, para]) => (
              <Command.Item key={para} value={`tela ${t(rot)}`} onSelect={() => ir(para)}><LayoutDashboard size={16} />{t(rot)}</Command.Item>
            ))}
          </Command.Group>
        )}
        {data && (
          <>
            <Command.Group heading={t("app.busca.canais")}>
              <Command.Item value={`canais escolher ${t("app.busca.todos_canais")}`} onSelect={() => ir("/")}><Tv size={16} />{t("app.busca.todos_canais")}</Command.Item>
              {data.canais.map((c) => (
                <Command.Item key={c.slug} value={`canal ${c.nome} ${c.tema}`} onSelect={() => ir(rota.canal(c.slug))}><Tv size={16} />{c.nome}<span className="de">{c.tema}</span></Command.Item>
              ))}
            </Command.Group>
            <Command.Group heading={t("app.busca.videos")}>
              {ordem(data.videos).map((v) => (
                <Command.Item key={v.canal + v.slug} value={`video ${v.titulo} ${v.slug}`} onSelect={() => ir(rota.video(v.canal, v.slug))}>
                  <Film size={16} />{v.titulo}<span className="de">{v.canal_nome}</span>
                </Command.Item>
              ))}
            </Command.Group>
            <Command.Group heading={t("app.busca.blocos")}>
              {ordem(data.blocos).map((b) => (
                <Command.Item key={b.canal + b.video + b.nn} value={`bloco ${b.nn} ${b.topico} ${b.video_titulo}`} onSelect={() => ir(rota.bloco(b.canal, b.video, b.nn))}>
                  <Clapperboard size={16} />{b.nn} · {b.topico}<span className="de">{b.video_titulo}</span>
                </Command.Item>
              ))}
            </Command.Group>
          </>
        )}
        <Command.Group heading={t("app.busca.config")}>
          {config.map(([rot, para]) => (
            <Command.Item key={para} value={`configuracao ${t(rot)}`} onSelect={() => ir(para)}><Settings size={16} />{t(rot)}</Command.Item>
          ))}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  );
}
