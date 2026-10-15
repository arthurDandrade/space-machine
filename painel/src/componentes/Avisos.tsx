// Avisos: o sino mostra o que parou esperando você, filas pausadas e o que foi entregue nas últimas 24 h, de todos
// os canais. Enquanto o painel está aberto, um aviso novo aparece num balão e, se você deixar, também no Mac.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, BellRing, CircleCheck, Hand, ListOrdered, X } from "lucide-react";
import { pegar, rota } from "../api";
import { haQuanto, useT } from "../textos";

interface Aviso {
  id: string; tipo: "esperando" | "entregue" | "fila"; canal: string; canal_nome: string; video: string; video_titulo: string;
  nn: string; topico: string; texto: string; etapa?: string; quando: number;
}

export const useAvisos = () => useQuery({ queryKey: ["avisos"], queryFn: () => pegar<{ itens: Aviso[] }>("/api/avisos") });

const VISTO = "sm-avisos-visto";
const lerVisto = () => { try { return Number(localStorage.getItem(VISTO) || 0); } catch { return 0; } };

function destino(a: Aviso) {
  return a.nn ? rota.bloco(a.canal, a.video, a.nn) : rota.video(a.canal, a.video);
}

function titulo(t: ReturnType<typeof useT>, a: Aviso) {
  if (a.tipo === "fila") return t("app.avisos.fila_pausada");
  return `${a.nn} · ${a.topico}`;
}

function Icone({ a }: { a: Aviso }) {
  return <span className={`ic ${a.tipo}`}>{a.tipo === "entregue" ? <CircleCheck size={16} /> : a.tipo === "fila" ? <ListOrdered size={16} /> : <Hand size={16} />}</span>;
}

export function Sino() {
  const t = useT();
  const { data } = useAvisos();
  const [aberto, setAberto] = useState(false);
  const [visto, setVisto] = useState(lerVisto);
  const [permissao, setPermissao] = useState(typeof Notification === "undefined" ? "denied" : Notification.permission);
  const caixa = useRef<HTMLDivElement>(null);
  const itens = data?.itens ?? [];
  const novos = itens.filter((a) => a.quando > visto).length;

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => { if (!caixa.current?.contains(e.target as Node)) setAberto(false); };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [aberto]);

  const abrir = () => {
    setAberto(!aberto);
    const agora = Date.now() / 1000;
    try { localStorage.setItem(VISTO, String(agora)); } catch { /* sem armazenamento: só nesta aba */ }
    setTimeout(() => setVisto(agora), 1500);
  };

  return (
    <div className="sino-caixa" ref={caixa}>
      <button className="bt redondo sino" onClick={abrir} title={t("app.avisos.titulo")}>
        <Bell size={18} />{novos > 0 && <i>{novos > 9 ? "9+" : novos}</i>}
      </button>
      <AnimatePresence>
        {aberto && (
          <motion.div className="avisos" initial={{ opacity: 0, y: -6, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -6, scale: 0.98 }} transition={{ duration: 0.16 }}>
            <div className="titulo-secao"><h3>{t("app.avisos.titulo")}</h3>
              {permissao === "default" && (
                <button onClick={() => Notification.requestPermission().then(setPermissao)}><BellRing size={13} /> {t("app.avisos.avisar_mac")}</button>
              )}
            </div>
            {itens.length ? (
              <div className="lista-avisos">
                {itens.map((a) => (
                  <Link key={a.id} to={destino(a)} className={`aviso ${a.quando > visto ? "novo" : ""}`} onClick={() => setAberto(false)}>
                    <Icone a={a} />
                    <div className="t">
                      <b>{titulo(t, a)}</b>
                      <span>{a.tipo === "esperando" ? (a.texto || t("app.esperando_voce")) : a.tipo === "entregue" ? t("app.avisos.entregue") : a.texto}</span>
                      <span className="de">{a.video_titulo} · {a.canal_nome} · {haQuanto(t, a.quando)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="vazio"><CircleCheck size={18} />{t("app.avisos.nada")}</div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// balões de aviso novo (e notificação do Mac, se permitida) enquanto o painel está aberto
export function BaloesDeAviso() {
  const t = useT();
  const { data } = useAvisos();
  const ja = useRef<Set<string> | null>(null);
  const [baloes, setBaloes] = useState<Aviso[]>([]);
  useEffect(() => {
    if (!data) return;
    if (!ja.current) { ja.current = new Set(data.itens.map((a) => a.id)); return; }  // o que já existia ao abrir não avisa
    const novos = data.itens.filter((a) => !ja.current!.has(a.id) && a.tipo !== "fila");
    novos.forEach((a) => ja.current!.add(a.id));
    if (!novos.length) return;
    setBaloes((b) => [...novos, ...b].slice(0, 3));
    for (const a of novos) {
      setTimeout(() => setBaloes((b) => b.filter((x) => x.id !== a.id)), 9000);
      if (typeof Notification !== "undefined" && Notification.permission === "granted" && document.hidden) {
        new Notification(a.tipo === "entregue" ? t("app.avisos.mac_entregue") : t("app.avisos.mac_esperando"), {
          body: `${a.nn} · ${a.topico} — ${a.video_titulo}`,
        });
      }
    }
  }, [data, t]);
  return (
    <div className="baloes">
      <AnimatePresence>
        {baloes.map((a) => (
          <motion.div key={a.id} className={`balao ${a.tipo}`} layout initial={{ opacity: 0, y: 16, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, x: 40 }} transition={{ duration: 0.25 }}>
            <Icone a={a} />
            <Link to={destino(a)} className="t" onClick={() => setBaloes((b) => b.filter((x) => x.id !== a.id))}>
              <b>{a.tipo === "entregue" ? t("app.avisos.mac_entregue") : t("app.avisos.mac_esperando")}</b>
              <span>{a.nn} · {a.topico}</span>
            </Link>
            <button className="x" onClick={() => setBaloes((b) => b.filter((x) => x.id !== a.id))}><X size={14} /></button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
