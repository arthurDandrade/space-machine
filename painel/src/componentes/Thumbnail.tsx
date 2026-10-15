// Thumbnail do vídeo: enviar (clique, arrastar ou colar), e os botões que aparecem sobre a capa ao passar o mouse
// (ampliar, enviar/trocar, baixar, remover), como no Dark Planner. Trocar ou remover guarda a anterior.
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Download, Loader, Trash2, Upload, X, ZoomIn } from "lucide-react";
import { enviar } from "../api";
import { useT } from "../textos";

export function useThumbnail(canal: string, video: string) {
  const qc = useQueryClient();
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState("");
  const mandar = useCallback(async (f: File) => {
    setErro("");
    if (!f.type.startsWith("image/")) return setErro("Envie uma imagem PNG, JPG ou WEBP.");
    setEnviando(true);
    const corpo = new FormData();
    // imagem colada vem sem nome (ou "image.png"): dá um nome com a extensão certa
    const nome = f.name && f.name !== "image.png" ? f.name : `thumbnail-colada.${f.type.split("/")[1] || "png"}`;
    corpo.append("arquivo", f, nome);
    const r = await fetch(`/api/c/${canal}/v/${video}/thumbnail`, { method: "POST", body: corpo });
    setEnviando(false);
    if (!r.ok) setErro((await r.json().catch(() => ({}))).detail || r.statusText);
    qc.invalidateQueries();
  }, [canal, video, qc]);
  const remover = useCallback(async () => {
    await enviar(`/api/c/${canal}/v/${video}/thumbnail/remover`);
    qc.invalidateQueries();
  }, [canal, video, qc]);
  return { enviar: mandar, remover, enviando, erro };
}

export function soltarArquivo(e: React.DragEvent, mandar: (f: File) => void) {
  e.preventDefault();
  e.stopPropagation();
  const f = [...e.dataTransfer.files].find((x) => x.type.startsWith("image/"));
  if (f) mandar(f);
}

// arrastar uma imagem sobre a capa: devolve as props do contêiner e se tem algo em cima
export function useSoltar(mandar: (f: File) => void) {
  const [sobre, setSobre] = useState(false);
  return {
    sobre,
    props: {
      onDragOver: (e: React.DragEvent) => { if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); setSobre(true); } },
      onDragLeave: () => setSobre(false),
      onDrop: (e: React.DragEvent) => { setSobre(false); soltarArquivo(e, mandar); },
    },
  };
}

export function Ampliar({ src, fechar }: { src: string; fechar: () => void }) {
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); fechar(); } };
    window.addEventListener("keydown", tecla, true);
    return () => window.removeEventListener("keydown", tecla, true);
  }, [fechar]);
  return createPortal(
    <div className="ampliar" onClick={fechar}>
      <motion.img src={src} alt="" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.18 }} />
      <button className="x fechar-ampliar" onClick={fechar}><X size={18} /></button>
    </div>,
    document.body,
  );
}

// os 4 botões sobre a capa. Num card que é um link, clicar num botão não navega; no resto da capa, navega.
export function BarraThumb({ canal, video, thumb, capa }: { canal: string; video: string; thumb: { url: string; nome: string } | null; capa: string }) {
  const t = useT();
  const { enviar: mandar, remover, enviando, erro } = useThumbnail(canal, video);
  const campo = useRef<HTMLInputElement>(null);
  const [ampliar, setAmpliar] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const parar = (e: React.MouseEvent) => { e.preventDefault(); e.stopPropagation(); };
  return (
    <>
      <div className="barra-thumb" onMouseLeave={() => setConfirmar(false)}>
        <button title={t("app.thumb.ampliar")} onClick={(e) => { parar(e); setAmpliar(true); }}><ZoomIn size={17} /></button>
        <button title={t(thumb ? "app.thumb.trocar" : "app.thumb.enviar")} disabled={enviando} onClick={(e) => { parar(e); campo.current?.click(); }}>
          {enviando ? <Loader size={17} className="gira" /> : <Upload size={17} />}
        </button>
        {thumb && (
          <a title={t("app.thumb.baixar")} href={thumb.url} download={thumb.nome} onClick={(e) => e.stopPropagation()}><Download size={17} /></a>
        )}
        {thumb && (confirmar ? (
          <button className="perigo sim" title={t("app.thumb.remover")} onClick={(e) => { parar(e); setConfirmar(false); remover(); }}>{t("app.thumb.remover_sim")}</button>
        ) : (
          <button className="perigo" title={t("app.thumb.remover")} onClick={(e) => { parar(e); setConfirmar(true); }}><Trash2 size={17} /></button>
        ))}
      </div>
      {erro && <span className="erro-barra" onClick={parar}>{erro}</span>}
      <input ref={campo} type="file" accept="image/png,image/jpeg,image/webp" hidden onClick={(e) => e.stopPropagation()}
             onChange={(e) => { const f = e.target.files?.[0]; if (f) mandar(f); e.target.value = ""; }} />
      {ampliar && <Ampliar src={thumb?.url ?? capa} fechar={() => setAmpliar(false)} />}
    </>
  );
}
