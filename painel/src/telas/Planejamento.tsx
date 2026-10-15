// Planejamento do canal: ideias, quadro de produção (arrastar para Edição final / Agendado / Publicado),
// calendário de publicação e o formulário de novo vídeo (roteiro → blocos, com a divisão mostrada ao vivo).
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DndContext, DragEndEvent, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { ArrowRight, CalendarDays, ChevronLeft, ChevronRight, Clapperboard, GripVertical, Lightbulb, Plus, Trash2 } from "lucide-react";
import { Coluna, enviar, pegar, rota, urlCapa, Video } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { Capa } from "../componentes/Imagens";
import { useT } from "../textos";

type Ideia = { id: number; titulo: string; notas: string; criado: string };
const useIdeias = (canal: string) =>
  useQuery({ queryKey: ["ideias", canal], queryFn: () => pegar<{ ideias: Ideia[] }>(`/api/c/${canal}/ideias`) });

function FormIdeia({ canal, compacto = false }: { canal: string; compacto?: boolean }) {
  const t = useT();
  const qc = useQueryClient();
  const [titulo, setTitulo] = useState("");
  const [notas, setNotas] = useState("");
  const criar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/ideias`, { titulo, notas }),
    onSuccess: () => { setTitulo(""); setNotas(""); qc.invalidateQueries({ queryKey: ["ideias", canal] }); qc.invalidateQueries({ queryKey: ["canal", canal] }); },
  });
  return (
    <form className={`cartao form-ideia ${compacto ? "compacto" : ""}`} onSubmit={(e) => { e.preventDefault(); if (titulo.trim()) criar.mutate(); }}>
      <input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder={t("app.ideias.titulo_ex")} required />
      {!compacto && <textarea value={notas} onChange={(e) => setNotas(e.target.value)} rows={2} placeholder={t("app.ideias.notas_ex")} />}
      <button className="bt primario pequeno" disabled={criar.isPending || !titulo.trim()}><Plus size={15} />{t("app.ideias.adicionar")}</button>
      {criar.isError && <span className="erro">{criar.error.message}</span>}
    </form>
  );
}

function CartaoIdeia({ canal, i }: { canal: string; i: Ideia }) {
  const t = useT();
  const qc = useQueryClient();
  const [confirmar, setConfirmar] = useState(false);
  const apagar = useMutation({
    mutationFn: () => enviar(`/api/c/${canal}/ideias/${i.id}/apagar`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ideias", canal] }); qc.invalidateQueries({ queryKey: ["canal", canal] }); },
  });
  return (
    <div className="ideia">
      <span className="ic"><Lightbulb size={16} /></span>
      <div className="t"><b>{i.titulo}</b>{i.notas && <span>{i.notas}</span>}</div>
      <div className="acoes-ideia">
        <Link className="bt pequeno" to={`/c/${canal}/novo?titulo=${encodeURIComponent(i.titulo)}`}>{t("app.ideias.virar_video")}<ArrowRight size={14} /></Link>
        {confirmar ? (
          <>
            <button className="bt pequeno perigo" onClick={() => apagar.mutate()}>{t("app.ideias.apagar_sim")}</button>
            <button className="bt pequeno" onClick={() => setConfirmar(false)}>{t("app.cancelar")}</button>
          </>
        ) : (
          <button className="x" onClick={() => setConfirmar(true)} title={t("app.ideias.apagar")}><Trash2 size={14} /></button>
        )}
      </div>
    </div>
  );
}

export function IdeiasTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data } = useIdeias(canal);
  const t = useT();
  if (!dc) return null;
  const ideias = data?.ideias ?? [];
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.ideias")}</b></>} titulo={t("app.ideias.titulo")} />
      <p className="sub intro">{t("app.ideias.explica")}</p>
      <div className="ideias-grade">
        <FormIdeia canal={canal} />
        <div className="lista-ideias">
          {ideias.length ? ideias.map((i) => <CartaoIdeia key={i.id} canal={canal} i={i} />)
            : <div className="vazio"><Lightbulb size={18} />{t("app.ideias.nenhuma")}</div>}
        </div>
      </div>
    </>
  );
}

// ---------------- quadro ----------------
const MOVEIS: Coluna[] = ["edicao_final", "agendado", "publicado"];

function CartaoQuadro({ canal, v }: { canal: string; v: Video }) {
  const t = useT();
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: v.slug, data: { coluna: v.coluna } });
  const estilo = transform ? { transform: `translate(${transform.x}px, ${transform.y}px)`, zIndex: 20 } : undefined;
  return (
    <div ref={setNodeRef} style={estilo} className={`card-quadro ${isDragging ? "arrastando" : ""}`} {...attributes} {...listeners}>
      <Link to={rota.video(canal, v.slug)} draggable={false} onClick={(e) => isDragging && e.preventDefault()}>
        <Capa className="cv" src={urlCapa(canal, v.slug)} existe={v.tem_capa} vazio={<span className="sem-capa"><Clapperboard size={20} /></span>} />
        <b>{v.titulo_pub || v.titulo}</b>
        <span className="sub">{t("app.video.blocos_de", { e: v.entregues, n: v.n_blocos })}{v.data_pub ? ` · ${v.data_pub.slice(8, 10)}/${v.data_pub.slice(5, 7)}` : ""}</span>
        <div className="progresso"><i style={{ width: `${v.n_blocos ? (100 * v.entregues) / v.n_blocos : 0}%` }} /></div>
      </Link>
      <span className="pega"><GripVertical size={14} /></span>
    </div>
  );
}

function ColunaQuadro({ id, children, n }: { id: Coluna; children: React.ReactNode; n: number }) {
  const t = useT();
  const { setNodeRef, isOver, active } = useDroppable({ id });
  const vindo = active?.data.current?.coluna as Coluna | undefined;
  const aceita = !!active && vindo !== id && (MOVEIS.includes(id) || id === "producao" || id === "roteiro");
  return (
    <div ref={setNodeRef} className={`coluna-quadro ${isOver && aceita ? "sobre" : ""} ${active && aceita ? "aceita" : ""}`}>
      <h3><span>{t(`app.coluna.${id}`)}</span><span className="n">{n}</span></h3>
      <div className="cards">{children}</div>
    </div>
  );
}

export function QuadroTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const { data: di } = useIdeias(canal);
  const t = useT();
  const qc = useQueryClient();
  const sensores = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const mover = useMutation({
    mutationFn: ({ video, coluna }: { video: string; coluna: Coluna }) => enviar(`/api/c/${canal}/v/${video}/coluna`, { coluna }),
    onSettled: () => qc.invalidateQueries(),
  });
  if (!dc) return null;
  const soltar = (e: DragEndEvent) => {
    const para = e.over?.id as Coluna | undefined;
    if (para && para !== "ideia" && para !== e.active.data.current?.coluna) mover.mutate({ video: String(e.active.id), coluna: para });
  };
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.quadro")}</b></>} titulo={t("app.quadro.titulo")} />
      <p className="sub intro">{t("app.quadro.explica")}</p>
      <DndContext sensors={sensores} onDragEnd={soltar}>
        <div className="quadro">
          {dc.colunas.map((c) => (
            <ColunaQuadro key={c.id} id={c.id} n={c.id === "ideia" ? (di?.ideias.length ?? 0) : dc.videos.filter((v) => v.coluna === c.id).length}>
              {c.id === "ideia" ? (
                <>
                  <FormIdeia canal={canal} compacto />
                  {(di?.ideias ?? []).map((i) => (
                    <Link key={i.id} className="ideia-mini" to={`/c/${canal}/novo?titulo=${encodeURIComponent(i.titulo)}`} title={t("app.ideias.virar_video")}>
                      <Lightbulb size={14} /><span>{i.titulo}</span><ArrowRight size={14} />
                    </Link>
                  ))}
                </>
              ) : (
                dc.videos.filter((v) => v.coluna === c.id).map((v) => <CartaoQuadro key={v.slug} canal={canal} v={v} />)
              )}
            </ColunaQuadro>
          ))}
        </div>
      </DndContext>
      {mover.isError && <p className="erro">{mover.error.message}</p>}
    </>
  );
}

// ---------------- calendário ----------------
type Cal = {
  mes: string; ano: number; mes_n: number; ant: string; prox: string;
  semanas: { data: string; dia: number; no_mes: boolean; hoje: boolean; videos: { slug: string; titulo: string; coluna: Coluna; tem_capa: boolean }[] }[][];
  sem_data: { slug: string; titulo: string; coluna: Coluna; tem_capa: boolean }[];
};

export function CalendarioTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const [params, setParams] = useSearchParams();
  const mes = params.get("mes") ?? "";
  const { data } = useQuery({ queryKey: ["calendario", canal, mes], queryFn: () => pegar<Cal>(`/api/c/${canal}/calendario?mes=${mes}`) });
  const t = useT();
  if (!dc || !data) return null;
  const nomeMes = t("app.meses").split(",")[data.mes_n - 1];
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.nav.calendario")}</b></>} titulo={`${nomeMes} ${data.ano}`}>
        <button className="bt redondo" onClick={() => setParams({ mes: data.ant })} title={t("app.cal.anterior")}><ChevronLeft size={18} /></button>
        <button className="bt" onClick={() => setParams({})}>{t("app.cal.hoje")}</button>
        <button className="bt redondo" onClick={() => setParams({ mes: data.prox })} title={t("app.cal.proximo")}><ChevronRight size={18} /></button>
      </Cabecalho>
      <p className="sub intro">{t("app.cal.explica")}</p>
      <div className="cal">
        {t("app.dias_semana_seg").split(",").map((d) => <div key={d} className="cab">{d}</div>)}
        {data.semanas.flat().map((d) => (
          <div key={d.data} className={`dia-cal ${d.no_mes ? "" : "fora"} ${d.hoje ? "hoje" : ""}`}>
            <span className="num">{d.dia}</span>
            {d.videos.map((v) => (
              <Link key={v.slug} className={`pub-cal ${v.coluna}`} to={`${rota.video(canal, v.slug)}?aba=publicacao`}>
                <Capa className="mini" src={urlCapa(canal, v.slug)} existe={v.tem_capa} icone={false} />
                <span>{v.titulo}</span>
              </Link>
            ))}
          </div>
        ))}
      </div>
      {data.sem_data.length > 0 && (
        <section className="sem-data">
          <div className="titulo-secao"><h3>{t("app.cal.sem_data")}</h3></div>
          <div className="pilulas">
            {data.sem_data.map((v) => (
              <Link key={v.slug} className="pilula-link" to={`${rota.video(canal, v.slug)}?aba=publicacao`}>
                <CalendarDays size={14} />{v.titulo}<span>{t(`app.coluna.${v.coluna}`)}</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

// ---------------- novo vídeo ----------------
function dividir(roteiro: string) {
  // mesma regra de gestao.dividir_roteiro: linha com # começa um tópico; o texto antes do 1º é o cold open
  const cold: string[] = [];
  const partes: { nome: string; palavras: number }[] = [];
  let atual: { nome: string; texto: string[] } | null = null;
  const todas: { nome: string; texto: string[] }[] = [];
  for (const linha of roteiro.trim().split("\n")) {
    const m = /^\s*#+\s*(.+?)\s*$/.exec(linha);
    if (m && !linha.trimStart().startsWith("#!")) {
      atual = { nome: m[1].replace(/[.:]+$/, "").trim(), texto: [] };
      todas.push(atual);
    } else if (!atual) cold.push(linha);
    else atual.texto.push(linha);
  }
  for (const p of todas) if (p.nome) partes.push({ nome: p.nome, palavras: p.texto.join(" ").split(/\s+/).filter(Boolean).length });
  return { cold: cold.join(" ").trim(), partes };
}

export function NovoVideoTela() {
  const { canal = "" } = useParams();
  const { data: dc } = useCanal(canal);
  const [params] = useSearchParams();
  const t = useT();
  const qc = useQueryClient();
  const navegar = useNavigate();
  const [titulo, setTitulo] = useState(params.get("titulo") ?? "");
  const [roteiro, setRoteiro] = useState("");
  const divisao = useMemo(() => dividir(roteiro), [roteiro]);
  const criar = useMutation({
    mutationFn: () => enviar<{ ok: boolean; video: string }>(`/api/c/${canal}/novo`, { titulo, roteiro }),
    onSuccess: (r) => { qc.invalidateQueries(); navegar(rota.video(canal, r.video)); },
  });
  if (!dc) return null;
  const n = divisao.partes.length + (divisao.cold ? 1 : 0);
  return (
    <>
      <Cabecalho onde={<>{dc.canal.nome} › <b>{t("app.novo_video")}</b></>} titulo={t("app.novo.titulo")} />
      <form className="novo-grade" onSubmit={(e) => { e.preventDefault(); criar.mutate(); }}>
        <div className="cartao">
          <label className="campo">{t("app.novo.titulo_video")}<input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Every NFL Team Name Explained" required /></label>
          <label className="campo">{t("app.novo.roteiro")}
            <textarea className="roteiro" rows={22} value={roteiro} onChange={(e) => setRoteiro(e.target.value)} placeholder={t("app.novo.roteiro_ex")} required />
          </label>
          <div className="rodape-form">
            <button className="bt primario" disabled={criar.isPending || !titulo.trim() || !divisao.partes.length}>
              <Plus size={16} />{t("app.novo.criar", { n })}
            </button>
            {criar.isError && <span className="erro">{criar.error.message}</span>}
          </div>
        </div>
        <aside className="cartao divisao">
          <div className="titulo-secao"><h3>{t("app.novo.vira")}</h3><span className="sub">{t("app.novo.n_blocos", { n })}</span></div>
          {!roteiro.trim() && <p className="sub">{t("app.novo.explica")}</p>}
          <ol>
            {divisao.cold && <li className="cold"><span className="nn">00</span><div><b>{t("app.novo.cold_open")}</b><span>{divisao.cold.slice(0, 90)}{divisao.cold.length > 90 ? "…" : ""}</span></div></li>}
            {divisao.partes.map((p, i) => (
              <li key={i}><span className="nn">{String(i + 1).padStart(2, "0")}</span><div><b>{p.nome}</b><span>{t("app.bloco.palavras", { n: p.palavras })}</span></div></li>
            ))}
          </ol>
          {roteiro.trim() && !divisao.partes.length && <p className="erro">{t("app.novo.sem_topicos")}</p>}
        </aside>
      </form>
    </>
  );
}
