// Um item da lista "Para conferir" em palavras de gente: de que cena é (em vez do código "01-02-a"), o que o sistema
// anotou (sem os rótulos internos do motor, como "cena_errada" ou "troca automática (recorte)") e a miniatura.
import { ImageOff } from "lucide-react";
import { useT } from "../textos";

type T = ReturnType<typeof useT>;
export interface ItemParaConferir { id: string; texto: string; tipo: string; descricao: string; arquivo: string | null }

// "03-02-a" = capítulo 3, cena 2, asset a (vídeo inteiro); "02-a" = cena 2, asset a (um bloco)
export function ondeFica(t: T, id: string) {
  const p = id.split("-");
  if (p.length === 3 && /^\d+$/.test(p[0]) && /^\d+$/.test(p[1])) return t("app.conferir.onde_cap", { cap: +p[0], cena: +p[1] });
  if (p.length === 2 && /^\d+$/.test(p[0])) return t("app.conferir.onde_cena", { cena: +p[0] });
  return id;
}

// os problemas que a conferência automática aponta (escolher.py), como o motor os chama
const PROBLEMAS = ["cena_errada", "recorte", "tarja", "qualidade", "texto", "identidade"];

export function emPalavras(t: T, texto: string) {
  let s = (texto || "").trim();
  s = s.replace(/\s*troca automática \((\w+)\)/g, (_, p: string) => ` ${t(`app.conferir.troca_${p}`, undefined, t("app.conferir.troca"))}`);
  s = s.replace(new RegExp(`^(${PROBLEMAS.join("|")}):\\s*`), (_, p: string) => `${t(`app.conferir.problema_${p}`, undefined, p)}: `);
  s = s.trim();
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

export function ItemConferir({ c }: { c: ItemParaConferir }) {
  const t = useT();
  return (
    <div className="conf">
      <div className="mini-asset">
        {c.arquivo ? (c.arquivo.includes(".mp4") ? <video src={`${c.arquivo}#t=1`} preload="metadata" muted /> : <img src={c.arquivo} alt="" loading="lazy" />)
          : <ImageOff size={16} />}
      </div>
      <div className="t">
        <b title={c.id}>{ondeFica(t, c.id)}{c.tipo && <i>{c.tipo}</i>}</b>
        <span>{emPalavras(t, c.texto)}</span>
        {c.descricao && <em>{c.descricao}</em>}
      </div>
    </div>
  );
}
