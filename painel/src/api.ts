// Conversa com a API do painel (space_machine/api.py). Os tipos espelham o que a API devolve.

export type EstadoBloco = "run" | "ok" | "fila" | "wait" | "meio" | "todo";
export type Coluna = "ideia" | "roteiro" | "producao" | "edicao_final" | "agendado" | "publicado";

export interface Cores {
  cor_fundo?: string;
  cor_texto?: string;
  cor_destaque?: string;
  cor_caixa?: string;
  cor_sombra?: string;
}

export interface ResumoCanal {
  slug: string;
  nome: string;
  tema: string;
  idioma: string;
  ativo: boolean;
  cores: Cores;
  banner: boolean;
  logo: boolean;
  colunas: Record<Coluna, number>;
  n_videos: number;
  rodando: number;
  esperando: number;
  atual: { slug: string; titulo: string; n_blocos: number; entregues: number; rodando: number; tem_capa: boolean } | null;
  rodando_agora: string[];
}

export interface Canais {
  canais: ResumoCanal[];
  rodando: number;
  esperando: number;
  consumo_7d: number;
  falta_algo: boolean;
}

export interface Fila {
  ativa: boolean;
  status: string;
  rodando: string[];
  esperando: string[];
  parados: string[];
  max: number;
  motivo: string;
}

export interface Video {
  slug: string;
  titulo: string;
  titulo_pub: string;
  coluna: Coluna;
  n_blocos: number;
  entregues: number;
  rodando: number;
  esperando: number;
  na_fila: number;
  blocos: { nn: string; topico: string; estado: EstadoBloco }[];
  mudou: number;
  data_pub: string;
  link: string;
  fila: Fila | null;
  consumo: number;
  tem_capa: boolean;
}

export interface Esperando {
  tem_capa: boolean;
  video: string;
  video_titulo: string;
  nn: string;
  topico: string;
  etapa: string;
  motivo: string;
}

export interface Rodando {
  tem_capa: boolean;
  video: string;
  video_titulo: string;
  nn: string;
  topico: string;
  etapa: string;
  indice: number;
  total: number;
  detalhe: string;
  desde: number | null;
}

export interface PainelCanal {
  canal: ResumoCanal;
  colunas: { id: Coluna; rotulo: string; n: number }[];
  videos: Video[];
  destaque: Video | null;
  esperando: Esperando[];
  rodando: Rodando[];
  filas: (Fila & { video: string; video_titulo: string })[];
  publicacoes: { video: string; titulo: string; data: string; coluna: Coluna }[];
  consumo_7d: { total: number; etapas: { etapa: string; tokens: number }[] };
}

export interface BlocoDoVideo {
  nn: string;
  topico: string;
  estado: EstadoBloco;
  atual: string;
  feito: Record<string, boolean>;
  assets_total: number;
  assets_prontos: number;
  conferir: number;
  parado: { etapa?: string; motivo?: string } | null;
  aprovado: boolean;
  previas: number;
  mudou: number;
  tem_capa: boolean;
}

export interface Publicacao {
  status: string;
  titulo_pub: string;
  descricao: string;
  tags: string;
  data_pub: string;
  notas: string;
  link: string;
  atualizado: string;
}

export interface DetalheVideo extends Omit<Video, "blocos" | "fila"> {
  blocos: BlocoDoVideo[];
  fila: (Fila & { inicio?: string; fim?: string; lancados?: string[] }) | null;
  publicacao: Publicacao;
  consumo_detalhe: { chamadas?: number; equivalente?: number };
  etapas: { id: string; rotulo: string }[];
}

export interface DetalheBloco {
  nn: string;
  topico: string;
  video: string;
  video_titulo: string;
  feito: Record<string, boolean>;
  atual: string;
  rodando: boolean;
  parado: { etapa?: string; motivo?: string } | null;
  aprovado: boolean;
  travar_conferir: boolean;
  etapa_atual: string;
  etapas: { id: string; status: string; detalhe: string; quando: string }[];
  previas: { v: number; url: string }[];
  entregue: string | null;
  qa: string;
  qa_folha: string | null;
  storyboard: string;
  roteiro: string;
  conferir: { id: string; texto: string; tipo: string; descricao: string; arquivo: string | null }[];
  conferidos: number;
  revisao: string | null;
  assets_total: number;
  assets_prontos: number;
  log_rodar: string;
  log_etapa: { nome: string; texto: string } | null;
  anterior: string | null;
  proximo: string | null;
}

export interface Sistema {
  idioma: string;
  textos: Record<string, string>;
  falta_algo: boolean;
}

export class ErroApi extends Error {
  constructor(public status: number, mensagem: string) {
    super(mensagem);
  }
}

async function resposta<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let msg = r.statusText;
    try {
      msg = (await r.json()).detail || msg;
    } catch {
      /* corpo sem JSON */
    }
    throw new ErroApi(r.status, msg);
  }
  return r.json();
}

export const pegar = <T,>(url: string) => fetch(url).then((r) => resposta<T>(r));

export const enviar = <T = { ok: boolean },>(url: string, corpo?: unknown) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  }).then((r) => resposta<T>(r));

// endereços das imagens (a API gera e guarda em cache)
export const urlMarca = (canal: string, qual: "banner" | "logo") => `/api/c/${canal}/marca/${qual}`;
export const urlCapa = (canal: string, video: string, nn?: string) =>
  `/api/c/${canal}/v/${video}/capa${nn ? `?nn=${nn}` : ""}`;

// rotas do painel novo
export const rota = {
  canal: (c: string) => `/c/${c}`,
  video: (c: string, v: string) => `/c/${c}/v/${v}`,
  bloco: (c: string, v: string, nn: string) => `/c/${c}/v/${v}/b/${nn}`,
};

// páginas do painel antigo que ainda não passaram para o React
export const antiga = {
  novoVideo: (c: string) => `/novo/${c}`,
  ideias: (c: string) => `/canal/${c}/producao`,
  calendario: (c: string) => `/canal/${c}/calendario`,
  identidade: (c: string) => `/config/canais#regras-${c}`,
  chaves: (c: string) => `/config/apis?canal=${c}`,
  novoCanal: "/config/canais#novo",
  consumo: "/consumo",
  modelos: "/config/modelos",
  primeirosPassos: "/primeiros-passos",
};
