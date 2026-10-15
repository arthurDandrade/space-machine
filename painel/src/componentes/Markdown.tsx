// Markdown dos arquivos do motor (QA, storyboard, log de aprendizados): títulos, parágrafos, listas, tabelas,
// **negrito**, `código` e <br> nas células. Monta elementos React (nada de HTML cru vindo do arquivo).
import { Fragment, ReactNode } from "react";

function inline(texto: string): ReactNode[] {
  const partes: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|<br\s*\/?>)/g;
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(texto))) {
    if (m.index > ultimo) partes.push(texto.slice(ultimo, m.index));
    const t = m[0];
    if (t.startsWith("**")) partes.push(<b key={i++}>{t.slice(2, -2)}</b>);
    else if (t.startsWith("`")) partes.push(<code key={i++}>{t.slice(1, -1)}</code>);
    else partes.push(<br key={i++} />);
    ultimo = m.index + t.length;
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo));
  return partes;
}

const celulas = (linha: string) => linha.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

export function Markdown({ texto, className = "" }: { texto: string; className?: string }) {
  const linhas = texto.split("\n");
  const blocos: ReactNode[] = [];
  let i = 0;
  while (i < linhas.length) {
    const l = linhas[i];
    if (!l.trim()) { i++; continue; }
    if (l.trim().startsWith("```")) {
      const codigo: string[] = [];
      i++;
      while (i < linhas.length && !linhas[i].trim().startsWith("```")) codigo.push(linhas[i++]);
      i++;
      blocos.push(<pre key={i} className="codigo-md"><code>{codigo.join("\n")}</code></pre>);
      continue;
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(l);
    if (h) {
      const Tag = (`h${Math.min(h[1].length + 1, 5)}`) as "h2";
      blocos.push(<Tag key={i}>{inline(h[2])}</Tag>);
      i++;
      continue;
    }
    if (l.trim().startsWith("|")) {
      const tabela: string[] = [];
      while (i < linhas.length && linhas[i].trim().startsWith("|")) tabela.push(linhas[i++]);
      const [cab, ...resto] = tabela;
      const corpo = resto.length && /^[\s|:-]+$/.test(resto[0]) ? resto.slice(1) : resto;
      blocos.push(
        <div className="tabela-md" key={i}>
          <table>
            <thead><tr>{celulas(cab).map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
            <tbody>{corpo.map((r, k) => <tr key={k}>{celulas(r).map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(l)) {
      const itens: string[] = [];
      while (i < linhas.length && /^\s*[-*]\s+/.test(linhas[i])) itens.push(linhas[i++].replace(/^\s*[-*]\s+/, ""));
      blocos.push(<ul key={i}>{itens.map((t, k) => <li key={k}>{inline(t)}</li>)}</ul>);
      continue;
    }
    if (/^---+$/.test(l.trim())) { blocos.push(<hr key={i} />); i++; continue; }
    const par: string[] = [];
    // a primeira linha entra sempre (senão uma linha como "--- x" travaria o laço)
    par.push(linhas[i++]);
    while (i < linhas.length && linhas[i].trim() && !/^(#{1,4}\s|\||\s*[-*]\s|---|\s*```)/.test(linhas[i])) par.push(linhas[i++]);
    blocos.push(<p key={i}>{par.map((t, k) => <Fragment key={k}>{k > 0 && " "}{inline(t)}</Fragment>)}</p>);
  }
  return <div className={`md ${className}`}>{blocos}</div>;
}
