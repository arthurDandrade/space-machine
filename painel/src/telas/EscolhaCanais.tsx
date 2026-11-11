// Início do produtor: o painel sempre abre aqui. A tela tem um trabalho só — escolher em qual canal você vai
// mexer. Saudação, os três números do momento (rodando, esperando, gasto do Claude) e um card por canal.
// Teclas 1–9 entram direto no canal daquela posição.
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { closestCenter, DndContext, DragEndEvent, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { ArrowRight, GripVertical, Hand, Loader, Plus, Sparkles } from "lucide-react";
import { Canais, enviar, pegar, ResumoCanal, urlCapa, urlMarca } from "../api";
import { TopoProdutor } from "../casca/TopoProdutor";
import { Capa, fundoDoCanal, iniciais, LogoCanal } from "../componentes/Imagens";
import { compacto, saudacao, useT } from "../textos";

// O cartão de um canal. Dá para puxar o cartão inteiro para outro lugar da grade: a ordem fica guardada e vale também
// para as teclas 1–9 e para a troca de canal na barra lateral. `lado` = de que lado o cartão arrastado vai entrar.
function CartaoCanal({ c, i, lado }: { c: ResumoCanal; i: number; lado: "" | "antes" | "depois" }) {
  const { attributes, listeners, setNodeRef: pegar_, isDragging } = useDraggable({ id: c.slug });
  const { setNodeRef: soltar_ } = useDroppable({ id: c.slug });
  const estilo = { animationDelay: `${i * 60}ms`, ...(c.cores.cor_destaque ? { "--accent": c.cores.cor_destaque } : {}) } as React.CSSProperties;
  return (
    <Link ref={(el) => { pegar_(el); soltar_(el); }} className={`canal ${c.ativo ? "" : "inativo"} ${isDragging ? "arrastando" : ""} ${lado}`}
          to={`/c/${c.slug}`} style={estilo} draggable={false} {...attributes} {...listeners} role="link">
      <MioloCanal c={c} i={i} />
    </Link>
  );
}

function MioloCanal({ c, i }: { c: ResumoCanal; i: number }) {
  const t = useT();
  return (
    <>
      <div className="capa">
        {c.banner ? (
          <Capa src={urlMarca(c.slug, "banner")} icone={false} />
        ) : (
          <div className="gerado" style={{ background: fundoDoCanal(c.cores) }}>{iniciais(c.nome)}</div>
        )}
        {c.rodando > 0 && (
          <span className="ao-vivo"><span className="pulso" />
            {c.rodando_agora.length ? t("app.canais.rodando_bloco", { nn: c.rodando_agora[0] }) : t("app.canais.rodando")}
          </span>
        )}
        {i < 9 && <span className="tecla">{i + 1}</span>}
        <span className="pega" title={t("app.canais.arrastar")}><GripVertical size={15} /></span>
      </div>
      <div className="corpo">
        <LogoCanal canal={c.slug} nome={c.nome} cores={c.cores} tem={c.logo} className="grande" />
        <h2>{c.nome}{!c.ativo && <span className="selo neutro">{t("app.canais.inativo")}</span>}</h2>
        <div className="tema">{[c.tema, t(`app.idioma.${c.idioma}`, undefined, c.idioma)].filter(Boolean).join(" · ")}</div>
        <div className="nums">
          <div className="num"><b>{c.colunas.producao}</b><span>{t("app.coluna.producao")}</span></div>
          <div className="num"><b>{c.colunas.edicao_final}</b><span>{t("app.coluna.edicao_final")}</span></div>
          <div className={`num ${c.esperando ? "alerta" : ""}`}><b>{c.esperando}</b><span>{t("app.esperando_voce")}</span></div>
        </div>
        {c.atual ? (
          <div className="atual">
            <Capa className="th" src={urlCapa(c.slug, c.atual.slug, undefined, c.atual.capa_v)} existe={c.atual.tem_capa} />
            <div className="t">{c.atual.titulo}
              <span>{t("app.video.blocos_entregues", { e: c.atual.entregues, n: c.atual.n_blocos })}</span>
            </div>
          </div>
        ) : (
          <div className="atual vazio-atual">
            <div className="t">{t("app.canais.sem_producao")}<span>{t("app.canais.sem_producao_sub")}</span></div>
          </div>
        )}
        <div className="entrar">{t("app.canais.entrar")} <ArrowRight size={18} /></div>
      </div>
    </>
  );
}

/** Os três números do momento, ao lado da saudação (antes se repetiam no rodapé da tela). */
function Agora({ data }: { data?: Canais }) {
  const t = useT();
  // o número leva ao canal onde aquilo está acontecendo (o primeiro, se for mais de um): antes era só um número
  const onde = (campo: "rodando" | "esperando") => data?.canais.find((c) => c[campo] > 0)?.slug;
  const itens = [
    { ic: <Loader size={16} />, cls: "run", n: data?.rodando ?? 0, rot: "app.canais.stat_rodando", para: onde("rodando") ? `/c/${onde("rodando")}` : "" },
    { ic: <Hand size={16} />, cls: "wait", n: data?.esperando ?? 0, rot: "app.canais.stat_esperando", para: onde("esperando") ? `/c/${onde("esperando")}/esperando` : "" },
    { ic: <Sparkles size={16} />, cls: "ok", n: compacto(data?.consumo_7d ?? 0), rot: "app.canais.stat_tokens", para: "/config/consumo" },
  ];
  return (
    <div className="agora">
      {itens.map((i) => {
        const miolo = <><span className={`ic ${i.cls}`}>{i.ic}</span><div><b>{i.n}</b><span>{t(i.rot)}</span></div></>;
        return i.para
          ? <Link key={i.rot} className="stat" to={i.para}>{miolo}</Link>
          : <div key={i.rot} className="stat">{miolo}</div>;
      })}
    </div>
  );
}

export function EscolhaCanais() {
  const t = useT();
  const navegar = useNavigate();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["canais"], queryFn: () => pegar<Canais>("/api/canais") });
  // enquanto a ordem nova está sendo guardada, a tela já mostra como vai ficar
  const [ordem, setOrdem] = useState<string[] | null>(null);
  const doServidor = data?.canais ?? [];
  const canais = ordem ? ordem.map((s) => doServidor.find((c) => c.slug === s)).filter((c): c is ResumoCanal => !!c) : doServidor;
  const [puxando, setPuxando] = useState<string | null>(null);
  const [sobre, setSobre] = useState<string | null>(null);
  const sensores = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  const guardar = useMutation({
    mutationFn: (nova: string[]) => enviar("/api/canais/ordem", { ordem: nova }),
    onSettled: async () => { await qc.invalidateQueries({ queryKey: ["canais"] }); setOrdem(null); },
  });
  const de = canais.findIndex((c) => c.slug === puxando);
  const para = canais.findIndex((c) => c.slug === sobre);
  const soltar = (e: DragEndEvent) => {
    setPuxando(null); setSobre(null);
    const alvo = e.over ? String(e.over.id) : "";
    const a = canais.findIndex((c) => c.slug === e.active.id), b = canais.findIndex((c) => c.slug === alvo);
    if (a < 0 || b < 0 || a === b) return;
    const nova = canais.map((c) => c.slug);
    nova.splice(b, 0, nova.splice(a, 1)[0]);
    setOrdem(nova);
    guardar.mutate(nova);
  };
  // soltar o cartão manda um clique para ele, e o cartão é um link: sem isto, arrastar abria o canal
  const grade = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let inicio: { x: number; y: number } | null = null;
    let arrastou = false;
    const apertar = (e: PointerEvent) => { inicio = grade.current?.contains(e.target as Node) ? { x: e.clientX, y: e.clientY } : null; arrastou = false; };
    const levantar = (e: PointerEvent) => { arrastou = !!inicio && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) > 8; };
    const clicar = (e: MouseEvent) => { if (arrastou) { e.preventDefault(); e.stopPropagation(); } arrastou = false; };
    window.addEventListener("pointerdown", apertar, true);
    window.addEventListener("pointerup", levantar, true);
    window.addEventListener("click", clicar, true);
    return () => {
      window.removeEventListener("pointerdown", apertar, true);
      window.removeEventListener("pointerup", levantar, true);
      window.removeEventListener("click", clicar, true);
    };
  }, []);

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, textarea, select") || e.metaKey || e.ctrlKey) return;
      const n = Number(e.key);
      if (n >= 1 && n <= 9 && canais[n - 1]) navegar(`/c/${canais[n - 1].slug}`);
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, [canais, navegar]);

  return (
    <div className="nivel-produtor">
      <TopoProdutor />

      <section className="ola">
        <div>
          <h1>{saudacao(t)}.</h1>
          {/* enquanto a lista não chega, nenhuma das duas frases: "crie seu primeiro canal" piscava sem motivo */}
          <p>{data ? t(canais.length ? "app.canais.escolha" : "app.canais.primeiro") : " "}</p>
        </div>
        {canais.length > 0 && <Agora data={data} />}
      </section>

      <DndContext sensors={sensores} collisionDetection={closestCenter} onDragStart={(e) => setPuxando(String(e.active.id))}
                  onDragOver={(e) => setSobre(e.over ? String(e.over.id) : null)} onDragEnd={soltar}
                  onDragCancel={() => { setPuxando(null); setSobre(null); }}>
      <div className="canais" ref={grade}>
        {canais.map((c, i) => (
          <CartaoCanal key={c.slug} c={c} i={i} lado={puxando && sobre === c.slug && de !== para ? (de < para ? "depois" : "antes") : ""} />
        ))}
        {data && (
          <Link className="canal novo" to="/config/canais?novo=1" style={{ animationDelay: `${canais.length * 60}ms` }}>
            <span className="mais"><Plus size={22} /></span>
            <b>{t("app.canais.novo")}</b>
            <span className="sub">{t("app.canais.novo_sub")}</span>
          </Link>
        )}
      </div>
      <DragOverlay dropAnimation={null}>
        {de >= 0 && <div className="canal flutuando" style={canais[de].cores.cor_destaque ? ({ "--accent": canais[de].cores.cor_destaque } as React.CSSProperties) : undefined}><MioloCanal c={canais[de]} i={de} /></div>}
      </DragOverlay>
      </DndContext>
      {guardar.isError && <p className="erro" style={{ textAlign: "center" }}>{guardar.error.message}</p>}
    </div>
  );
}
