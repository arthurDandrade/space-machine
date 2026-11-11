// Thumbnail feita pelo sistema: você escolhe um modelo do formato do canal e ele monta (space_machine/thumb.py).
// Só aparece nos canais cujo formato tem modelos de thumbnail.
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Loader, Pipette, RotateCcw, Wand2 } from "lucide-react";
import { DetalheVideo, enviar } from "../api";
import { useT } from "../textos";

export function FazerThumb({ canal, v }: { canal: string; v: DetalheVideo }) {
  const t = useT();
  const qc = useQueryClient();
  const ts = v.thumb_sistema;
  const [modelo, setModelo] = useState(ts?.estado.modelo || ts?.modelos[0]?.id || "");
  const [obs, setObs] = useState("");
  const [fundo, setFundo] = useState((ts?.fundos.atual || "#FFFFFF").toUpperCase());
  const fazer = useMutation({
    mutationFn: (refazer: boolean) => enviar(`/api/c/${canal}/v/${v.slug}/thumbnail/fazer`, { modelo, refazer, obs, fundo }),
    onSettled: () => qc.invalidateQueries(),
  });
  if (!ts || !ts.modelos.length) return null;
  const e = ts.estado;
  const rodando = e.rodando || fazer.isPending;
  const deste = e.modelo === modelo;
  const pronta = deste && e.status === "ok";
  // só a cor mudou: redesenha a mesma thumbnail na cor nova, sem pedir outro plano
  const soCor = pronta && !obs.trim() && (e.fundo || ts.fundos.do_formato).toUpperCase() !== fundo;
  // o modelo que acabou de ficar pronto: fazer de novo é pedir outro plano; nos outros casos continua de onde parou
  const doZero = pronta && !soCor;
  const rotulo = rodando ? "app.thumb.sis_fazendo"
    : deste && e.status === "esperando_flow" ? "app.thumb.sis_continuar"
    : soCor ? "app.thumb.sis_trocar_cor"
    : doZero ? "app.thumb.sis_de_novo" : "app.thumb.sis_fazer";
  const cores = ts.fundos.cores.map((c) => c.toUpperCase());
  return (
    <div className="thumb-sis">
      <div className="titulo-secao"><h3>{t("app.thumb.sis_titulo")}</h3></div>
      <span className="sub">{t("app.thumb.sis_sub")}</span>
      <div className="modelos-thumb">
        {ts.modelos.map((m) => (
          <button type="button" key={m.id} className={`modelo-thumb ${modelo === m.id ? "on" : ""}`} disabled={rodando}
                  onClick={() => setModelo(m.id)} title={m.quando}>
            <img src={m.previa} alt="" loading="lazy" />
            <b>{m.nome}</b>
            <span className="sub">{m.descricao}</span>
          </button>
        ))}
      </div>
      <div className="cores-thumb">
        <span className="sub">{t("app.thumb.sis_fundo")}</span>
        {cores.map((c) => (
          <button type="button" key={c} className={`cor-thumb ${fundo === c ? "on" : ""}`} style={{ background: c }} title={c}
                  disabled={rodando} onClick={() => setFundo(c)} />
        ))}
        <label className={`cor-thumb outra ${cores.includes(fundo) ? "" : "on"}`} title={t("app.thumb.sis_outra_cor")}
               style={cores.includes(fundo) ? undefined : { background: fundo }}>
          {cores.includes(fundo) && <Pipette size={13} />}
          <input type="color" value={fundo} disabled={rodando} onChange={(ev) => setFundo(ev.target.value.toUpperCase())} />
        </label>
        <span className="sub">{fundo}</span>
      </div>
      <label className="campo obs-thumb"><input value={obs} onChange={(ev) => setObs(ev.target.value)} placeholder={t("app.thumb.sis_obs")} disabled={rodando} /></label>
      <div className="acoes-final">
        <button type="button" className="bt pequeno primario" disabled={rodando || !modelo} onClick={() => fazer.mutate(doZero)}>
          {rodando ? <Loader size={14} className="gira" /> : <Wand2 size={14} />}{t(rotulo)}
        </button>
        {!rodando && deste && e.status && !doZero && (
          <button type="button" className="bt pequeno" title={t("app.thumb.sis_do_zero_dica")} onClick={() => fazer.mutate(true)}>
            <RotateCcw size={14} />{t("app.thumb.sis_do_zero")}
          </button>
        )}
        {rodando && e.etapa && <span className="sub">{e.etapa}</span>}
      </div>
      {!rodando && e.status === "ok" && <span className="selo ok"><Check size={12} />{t("app.thumb.sis_pronta", { modelo: e.modelo_nome || e.modelo })}</span>}
      {!rodando && e.aviso && <span className="aviso-thumb"><AlertTriangle size={13} />{e.aviso}</span>}
      {!rodando && e.status === "erro" && e.erro && <span className="erro">{e.erro}</span>}
      {fazer.isError && <span className="erro">{(fazer.error as Error).message}</span>}
    </div>
  );
}
