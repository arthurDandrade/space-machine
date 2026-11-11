// Planejamento do canal: ideias, quadro de produção (arrastar para Edição final / Agendado / Publicado),
// calendário de publicação e o formulário de novo vídeo (roteiro → blocos, com a divisão mostrada ao vivo).
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DndContext, DragEndEvent, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { ArrowRight, CalendarDays, ChevronLeft, ChevronRight, Clapperboard, GripVertical, Lightbulb, Plus, Trash2 } from "lucide-react";
import { Coluna, enviar, pegar, rota, urlCapa, Video } from "../api";
import { Cabecalho } from "../casca/Cabecalho";
import { useCanal } from "../casca/CascaCanal";
import { TituloCopiavel } from "../componentes/Copiar";
import { Capa } from "../componentes/Imagens";
import { useT } from "../textos";

type Ideia = { id: number; titulo: string; notas: string; criado: string };
export const useIdeias = (canal: string) =>
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

export function CartaoIdeia({ canal, i }: { canal: string; i: Ideia }) {
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
        <Link className="bt pequeno" to={`/c/${canal}/novo?titulo=${encodeURIComponent(i.titulo)}&ideia=${i.id}`}>{t("app.ideias.virar_video")}<ArrowRight size={14} /></Link>
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
      <Cabecalho titulo={t("app.ideias.titulo")} sub={t("app.ideias.explica")} />
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

// O conteúdo de um card do quadro. Em Publicado (e Agendado) o card é uma linha baixa, com a capa pequena ao lado:
// são as colunas que só crescem, e com a capa grande cada vídeo publicado empurrava a página para baixo.
function ConteudoCard({ canal, v, compacto }: { canal: string; v: Video; compacto: boolean }) {
  const t = useT();
  const data = v.data_pub ? `${v.data_pub.slice(8, 10)}/${v.data_pub.slice(5, 7)}` : "";
  const capa = <Capa className="cv" src={urlCapa(canal, v.slug, undefined, v.capa_v)} existe={v.tem_capa} vazio={<span className="sem-capa"><Clapperboard size={compacto ? 14 : 20} /></span>} />;
  if (compacto)
    return (
      <Link to={rota.video(canal, v.slug)} draggable={false}>
        {capa}
        <span className="t">
          <b>{v.titulo_pub || v.titulo}</b>
          <span className="sub">{[v.numero ? `nº ${v.numero}` : "", data || t("app.quadro.sem_data"), v.arquivado ? t("app.arquivar.selo").toLowerCase() : ""].filter(Boolean).join(" · ")}</span>
        </span>
      </Link>
    );
  return (
    <Link to={rota.video(canal, v.slug)} draggable={false}>
      {capa}
      <b><TituloCopiavel texto={v.titulo_pub || v.titulo} /></b>
      <span className="sub">{v.fluxo === "video" ? t("app.video.capitulos_n", { n: v.n_blocos }) : t("app.video.blocos_de", { e: v.entregues, n: v.n_blocos })}{data ? ` · ${data}` : ""}</span>
      <div className="progresso"><i style={{ width: `${v.n_blocos ? (100 * v.entregues) / v.n_blocos : 0}%` }} /></div>
    </Link>
  );
}

const COMPACTAS: Coluna[] = ["agendado", "publicado"];

function CartaoQuadro({ canal, v }: { canal: string; v: Video }) {
  // quem se mexe na tela ao arrastar é a cópia do DragOverlay: a coluna tem rolagem própria e cortaria o card
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: v.slug, data: { coluna: v.coluna } });
  const compacto = COMPACTAS.includes(v.coluna);
  return (
    <div ref={setNodeRef} className={`card-quadro ${compacto ? "compacto" : ""} ${isDragging ? "arrastando" : ""}`} {...attributes} {...listeners}>
      <ConteudoCard canal={canal} v={v} compacto={compacto} />
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
  // ao soltar um card, o navegador manda um clique para ele. O dnd-kit para a propagação desse clique (o React nem
  // fica sabendo), mas não cancela a ação padrão: como o card é um link, o navegador abria a página do vídeo.
  // Na janela, antes de tudo: se o ponteiro andou mais que o limite de ativação do arrasto (6 px) entre apertar e
  // soltar dentro do quadro, o clique que vem em seguida tem a ação padrão cancelada.
  const quadro = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let inicio: { x: number; y: number } | null = null;
    let arrastou = false;
    const apertar = (e: PointerEvent) => { inicio = quadro.current?.contains(e.target as Node) ? { x: e.clientX, y: e.clientY } : null; arrastou = false; };
    const soltarPonteiro = (e: PointerEvent) => { arrastou = !!inicio && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) > 6; };
    const clicar = (e: MouseEvent) => {
      if (arrastou) { e.preventDefault(); e.stopPropagation(); }
      arrastou = false;
    };
    window.addEventListener("pointerdown", apertar, true);
    window.addEventListener("pointerup", soltarPonteiro, true);
    window.addEventListener("click", clicar, true);
    return () => {
      window.removeEventListener("pointerdown", apertar, true);
      window.removeEventListener("pointerup", soltarPonteiro, true);
      window.removeEventListener("click", clicar, true);
    };
  }, []);
  const mover = useMutation({
    mutationFn: ({ video, coluna }: { video: string; coluna: Coluna }) => enviar(`/api/c/${canal}/v/${video}/coluna`, { coluna }),
    onSettled: () => qc.invalidateQueries(),
  });
  const [arrastando, setArrastando] = useState<string | null>(null);
  if (!dc) return null;
  // Agendado: a data mais próxima em cima. Publicado: o mais recente em cima (sem data, pelo número do vídeo).
  const daColuna = (id: Coluna) => {
    const vs = dc.videos.filter((v) => v.coluna === id);
    if (id === "agendado") return [...vs].sort((a, b) => (a.data_pub || "9999").localeCompare(b.data_pub || "9999"));
    if (id === "publicado") return [...vs].sort((a, b) => (b.data_pub || "").localeCompare(a.data_pub || "") || b.numero - a.numero);
    return vs;
  };
  const noAr = dc.videos.find((v) => v.slug === arrastando);
  const soltar = (e: DragEndEvent) => {
    setArrastando(null);
    const para = e.over?.id as Coluna | undefined;
    if (para && para !== "ideia" && para !== e.active.data.current?.coluna) mover.mutate({ video: String(e.active.id), coluna: para });
  };
  return (
    <>
      <Cabecalho titulo={t("app.quadro.titulo")} sub={t("app.quadro.explica")} />
      <DndContext sensors={sensores} onDragStart={(e) => setArrastando(String(e.active.id))} onDragEnd={soltar} onDragCancel={() => setArrastando(null)}>
        <div className="quadro" ref={quadro}>
          {dc.colunas.map((c) => (
            <ColunaQuadro key={c.id} id={c.id} n={c.id === "ideia" ? (di?.ideias.length ?? 0) : dc.videos.filter((v) => v.coluna === c.id).length}>
              {c.id === "ideia" ? (
                <>
                  <FormIdeia canal={canal} compacto />
                  {(di?.ideias ?? []).map((i) => (
                    <Link key={i.id} className="ideia-mini" to={`/c/${canal}/novo?titulo=${encodeURIComponent(i.titulo)}&ideia=${i.id}`} title={t("app.ideias.virar_video")}>
                      <Lightbulb size={14} /><span>{i.titulo}</span><ArrowRight size={14} />
                    </Link>
                  ))}
                </>
              ) : (
                daColuna(c.id).map((v) => <CartaoQuadro key={v.slug} canal={canal} v={v} />)
              )}
            </ColunaQuadro>
          ))}
        </div>
        <DragOverlay dropAnimation={null}>
          {noAr && <div className={`card-quadro flutuando ${COMPACTAS.includes(noAr.coluna) ? "compacto" : ""}`}><ConteudoCard canal={canal} v={noAr} compacto={COMPACTAS.includes(noAr.coluna)} /></div>}
        </DragOverlay>
      </DndContext>
      {mover.isError && <p className="erro">{mover.error.message}</p>}
    </>
  );
}

// ---------------- calendário ----------------
type Cal = {
  mes: string; ano: number; mes_n: number; ant: string; prox: string;
  semanas: { data: string; dia: number; no_mes: boolean; hoje: boolean; videos: { slug: string; titulo: string; coluna: Coluna; tem_capa: boolean; capa_v: number }[] }[][];
  sem_data: { slug: string; titulo: string; coluna: Coluna; tem_capa: boolean; capa_v: number }[];
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
      <Cabecalho titulo={`${nomeMes} ${data.ano}`} sub={t("app.cal.explica")}>
        <button className="bt redondo" onClick={() => setParams({ mes: data.ant })} title={t("app.cal.anterior")}><ChevronLeft size={18} /></button>
        <button className="bt" onClick={() => setParams({})}>{t("app.cal.hoje")}</button>
        <button className="bt redondo" onClick={() => setParams({ mes: data.prox })} title={t("app.cal.proximo")}><ChevronRight size={18} /></button>
      </Cabecalho>
      <div className="cal">
        {t("app.dias_semana_seg").split(",").map((d) => <div key={d} className="cab">{d}</div>)}
        {data.semanas.flat().map((d) => (
          <div key={d.data} className={`dia-cal ${d.no_mes ? "" : "fora"} ${d.hoje ? "hoje" : ""}`}>
            <span className="num">{d.dia}</span>
            {d.videos.map((v) => (
              <Link key={v.slug} className={`pub-cal ${v.coluna}`} to={`${rota.video(canal, v.slug)}?aba=publicacao`}>
                <Capa className="mini" src={urlCapa(canal, v.slug, undefined, v.capa_v)} existe={v.tem_capa} icone={false} />
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
  const [instrucoes, setInstrucoes] = useState("");
  // veio de "Virar vídeo": as notas da ideia (ângulo, gancho, o que citar) já entram como instruções, para você ajustar
  const idIdeia = Number(params.get("ideia")) || 0;
  const { data: ideias } = useIdeias(canal);
  const preenchido = useRef(false);
  useEffect(() => {
    const notas = ideias?.ideias.find((i) => i.id === idIdeia)?.notas;
    if (notas && !preenchido.current) { preenchido.current = true; setInstrucoes(notas); }
  }, [ideias, idIdeia]);
  const divisao = useMemo(() => dividir(roteiro), [roteiro]);
  const criar = useMutation({
    // veio de "Virar vídeo": a ideia sai da lista quando o vídeo é criado
    mutationFn: () => enviar<{ ok: boolean; video: string }>(`/api/c/${canal}/novo`, { titulo, roteiro, ideia: idIdeia, instrucoes: roteiro.trim() ? "" : instrucoes }),
    onSuccess: (r) => { qc.invalidateQueries(); navegar(rota.video(canal, r.video)); },
  });
  if (!dc) return null;
  const n = divisao.partes.length + (divisao.cold ? 1 : 0);
  // formato com agente de roteiro: sem roteiro colado, o Claude escreve a partir do título
  const escreve = !!dc.canal.escreve_roteiro;
  const so_titulo = escreve && !roteiro.trim();
  return (
    <>
      <Cabecalho titulo={t("app.novo.titulo")} sub={t(dc.canal.capitulo_falado === false ? "app.novo.explica_capitulo" : "app.novo.explica")} />
      <form className="novo-grade" onSubmit={(e) => { e.preventDefault(); criar.mutate(); }}>
        <div className="cartao">
          <label className="campo">{t("app.novo.titulo_video")}<input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Every NFL Team Name Explained" required /></label>
          {so_titulo && (
            <label className="campo">{t("app.novo.instrucoes")}
              <textarea rows={4} value={instrucoes} onChange={(e) => setInstrucoes(e.target.value)} placeholder={t("app.novo.instrucoes_ex")} maxLength={4000} />
              <span className="sub">{t("app.novo.instrucoes_sub")}</span>
            </label>
          )}
          <label className="campo">{t(escreve ? "app.novo.roteiro_opcional" : "app.novo.roteiro")}
            <textarea className="roteiro" rows={22} value={roteiro} onChange={(e) => setRoteiro(e.target.value)}
              placeholder={t(escreve ? "app.novo.roteiro_ex_agente" : "app.novo.roteiro_ex")} required={!escreve} />
          </label>
          <div className="rodape-form">
            <button className="bt primario" disabled={criar.isPending || !titulo.trim() || (!so_titulo && !divisao.partes.length)}>
              <Plus size={16} />{so_titulo ? t("app.novo.escrever") : t("app.novo.criar", { n })}
            </button>
            {criar.isPending && so_titulo && <span className="sub">{t("app.novo.escrevendo")}</span>}
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
