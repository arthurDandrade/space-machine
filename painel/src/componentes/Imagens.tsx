// Capas e marcas do canal. Enquanto carrega (ou se a imagem não existe) fica um fundo com ícone ou iniciais.
import { useState } from "react";
import { ImageOff } from "lucide-react";
import { Cores, urlMarca } from "../api";

// existe={false}: a API já disse que não há capa; mostra o vazio sem pedir a imagem (sem 404 no console)
export function Capa({ src, className = "", alt = "", icone = true, vazio, existe = true }: { src: string; className?: string; alt?: string; icone?: boolean; vazio?: React.ReactNode; existe?: boolean }) {
  const [carregou, setEstado] = useState<"carregando" | "ok" | "erro">("carregando");
  const estado = existe ? carregou : "erro";
  return (
    <div className={`capa-img ${className}`}>
      {estado !== "erro" && (
        <img src={src} alt={alt} loading="lazy" style={{ opacity: estado === "ok" ? 1 : 0 }}
             onLoad={() => setEstado("ok")} onError={() => setEstado("erro")} />
      )}
      {estado === "erro" && (vazio ?? (icone && <span className="sem"><ImageOff size={20} /></span>))}
    </div>
  );
}

export const iniciais = (nome: string) =>
  nome.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");

// fundo gerado das cores do canal, para canal sem banner/logo
export const fundoDoCanal = (c: Cores) =>
  `linear-gradient(135deg, ${c.cor_sombra || "#1d2233"}, ${c.cor_destaque || "#3b4bd8"} 60%, ${c.cor_caixa || c.cor_destaque || "#3b4bd8"})`;

export function LogoCanal({ canal, nome, cores, tem, className = "" }: { canal: string; nome: string; cores: Cores; tem: boolean; className?: string }) {
  const [falhou, setFalhou] = useState(false);
  if (!tem || falhou)
    return <div className={`logo-canal gerado ${className}`} style={{ background: fundoDoCanal(cores) }}>{iniciais(nome)}</div>;
  return (
    <div className={`logo-canal ${className}`} style={{ background: cores.cor_fundo || undefined }}>
      <img src={urlMarca(canal, "logo")} alt="" onError={() => setFalhou(true)} />
    </div>
  );
}
