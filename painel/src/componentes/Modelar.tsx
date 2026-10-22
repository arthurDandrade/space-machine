// Canais que você quer modelar, na tela inicial: você cola o link e o sistema traz nome, logo e tamanho
// (space_machine/modelar.py, pela API oficial do YouTube). Nada abre nem baixa vídeo: o link do card é um
// link comum, que só vai ao YouTube quando VOCÊ clica.
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, KeyRound, Plus, RefreshCw, Target, Trash2 } from "lucide-react";
import { CanaisModelo, CanalModelo, enviar, pegar, urlLogoModelo } from "../api";
import { Dialogo } from "./Dialogo";
import { compacto, useT } from "../textos";

function Logo({ c }: { c: CanalModelo }) {
  const [falhou, setFalhou] = useState(false);
  if (!c.tem_logo || falhou) return <div className="logo-modelo vazio">{c.nome.slice(0, 1).toUpperCase()}</div>;
  return <div className="logo-modelo"><img src={urlLogoModelo(c.id)} alt="" onError={() => setFalhou(true)} /></div>;
}

function CartaoModelo({ c }: { c: CanalModelo }) {
  const t = useT();
  const qc = useQueryClient();
  const [apagar, setApagar] = useState(false);
  const [notas, setNotas] = useState(c.notas);
  const recarregar = () => qc.invalidateQueries({ queryKey: ["modelar"] });
  const atualizar = useMutation({ mutationFn: () => enviar(`/api/modelar/${c.id}/atualizar`), onSettled: recarregar });
  const salvarNotas = useMutation({ mutationFn: (texto: string) => enviar(`/api/modelar/${c.id}/notas`, { notas: texto }) });
  // guarda sozinho um instante depois de você parar de escrever (sair da tela não perde a nota)
  useEffect(() => {
    if (notas === c.notas) return;
    const id = setTimeout(() => salvarNotas.mutate(notas), 800);
    return () => clearTimeout(id);
  }, [notas, c.notas]);
  const excluir = useMutation({
    mutationFn: () => enviar(`/api/modelar/${c.id}/excluir`),
    onSettled: () => { setApagar(false); recarregar(); },
  });
  return (
    <div className="modelo">
      <div className="topo">
        <Logo c={c} />
        <div className="t">
          <b>{c.nome}</b>
          <span className="sub">{[c.handle && `@${c.handle}`, c.pais].filter(Boolean).join(" · ")}</span>
        </div>
      </div>
      <div className="nums">
        <div className="num"><b>{compacto(c.inscritos)}</b><span>{t("app.modelar.inscritos")}</span></div>
        <div className="num"><b>{compacto(c.videos)}</b><span>{t("app.modelar.videos")}</span></div>
        <div className="num"><b>{compacto(c.vistas)}</b><span>{t("app.modelar.vistas")}</span></div>
      </div>
      <textarea className="notas" rows={2} value={notas} placeholder={t("app.modelar.notas_dica")}
                onChange={(e) => setNotas(e.target.value)} />
      {atualizar.isError && <p className="erro">{atualizar.error.message}</p>}
      <div className="acoes">
        <a className="bt pequeno" href={c.url} target="_blank" rel="noreferrer noopener">
          <ExternalLink size={14} />{t("app.modelar.abrir")}
        </a>
        <button className="bt pequeno" disabled={atualizar.isPending} onClick={() => atualizar.mutate()}>
          <RefreshCw size={14} />{t(atualizar.isPending ? "app.modelar.atualizando" : "app.modelar.atualizar")}
        </button>
        <button className="bt pequeno so-icone" title={t("app.modelar.remover")} onClick={() => setApagar(true)}>
          <Trash2 size={14} />
        </button>
      </div>
      {apagar && (
        <Dialogo titulo={t("app.modelar.remover_titulo", { nome: c.nome })} fechar={() => setApagar(false)}
                 acoes={<>
                   <button className="bt" onClick={() => setApagar(false)}>{t("app.cancelar")}</button>
                   <button className="bt perigo" disabled={excluir.isPending} onClick={() => excluir.mutate()}>
                     {t(excluir.isPending ? "app.modelar.removendo" : "app.modelar.remover")}
                   </button>
                 </>}>
          <p>{t("app.modelar.remover_explica")}</p>
        </Dialogo>
      )}
    </div>
  );
}

function PedirChave() {
  const t = useT();
  const qc = useQueryClient();
  const [valor, setValor] = useState("");
  const salvar = useMutation({
    mutationFn: () => enviar("/api/config/chaves/youtube", { valor }),
    onSuccess: () => { setValor(""); qc.invalidateQueries({ queryKey: ["modelar"] }); },
  });
  return (
    <form className="sem-chave" onSubmit={(e) => { e.preventDefault(); salvar.mutate(); }}>
      <span className="ic"><KeyRound size={16} /></span>
      <div className="t"><b>{t("app.modelar.sem_chave")}</b><span className="sub">{t("app.modelar.sem_chave_explica")}</span></div>
      <input type="password" value={valor} autoComplete="off" placeholder={t("app.chaves.colar")}
             onChange={(e) => setValor(e.target.value)} />
      <button className="bt pequeno primario" disabled={!valor.trim() || salvar.isPending}>
        {t(salvar.isPending ? "app.enviando" : "app.modelar.salvar_chave")}
      </button>
    </form>
  );
}

export function Modelar() {
  const t = useT();
  const qc = useQueryClient();
  const [link, setLink] = useState("");
  const { data } = useQuery({ queryKey: ["modelar"], queryFn: () => pegar<CanaisModelo>("/api/modelar") });
  const adicionar = useMutation({
    mutationFn: () => enviar("/api/modelar", { link }),
    onSuccess: () => { setLink(""); qc.invalidateQueries({ queryKey: ["modelar"] }); },
  });
  const itens = data?.itens ?? [];

  return (
    <section className="modelar">
      <div className="titulo-secao">
        <h3><Target size={16} />{t("app.modelar.titulo")}</h3>
        <span className="sub">{t("app.modelar.n", { n: itens.length })}</span>
      </div>
      <form className="colar-link" onSubmit={(e) => { e.preventDefault(); adicionar.mutate(); }}>
        <input value={link} placeholder={t("app.modelar.colar")} onChange={(e) => setLink(e.target.value)} />
        <button className="bt primario" disabled={!link.trim() || adicionar.isPending}>
          <Plus size={16} />{t(adicionar.isPending ? "app.modelar.buscando" : "app.modelar.adicionar")}
        </button>
      </form>
      {adicionar.isError && <p className="erro">{adicionar.error.message}</p>}
      {data && !data.tem_chave && <PedirChave />}
      {itens.length > 0 ? (
        <div className="modelos">{itens.map((c) => <CartaoModelo key={c.id} c={c} />)}</div>
      ) : (
        <p className="sub vazio-modelar">{t("app.modelar.vazio")}</p>
      )}
    </section>
  );
}
