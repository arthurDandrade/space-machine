# Buscador de assets (motor do Space Machine)

Busca na internet todos os assets de um vídeo no formato "___ Explained" a partir do **roteiro + narração**, e entrega tudo organizado e amarrado à palavra da narração em que cada asset aparece.

## Como usar

Normalmente pelo painel do Space Machine (`./spacemachine`): o orquestrador roda estes scripts para cada bloco, com o canal no ambiente (`SM_CANAL`/`SM_DADOS`, ver `motor/caminhos.py`). As regras do TEMA (trocas de termo nas buscas, buscas genéricas) vêm de `canal.json` › `regras.busca`; o resto é do formato e vale para todos os canais.

## O que sai em cada projeto

```
<projeto>/
├── roteiro.txt, narracao.*      (entrada)
├── plano.json                   cenas, textos e assets com palavra-gatilho e tempo
├── escolhas.json                qual candidato foi escolhido para cada asset
├── assets/<item>/<cena>/NN_<gatilho>.(jpg|png|mp4)
├── manifesto.json               lista final para o agente de edição
├── creditos.txt                 fonte e licença de cada asset
├── revisao.html                 galeria: escolhido + alternativas (abra no navegador)
└── _work/                       transcrição e candidatos (pode apagar depois)
```

## Fontes

| Tipo | Fontes (em ordem) |
|---|---|
| foto | Web (DuckDuckGo), Wikimedia Commons, Openverse, Smithsonian, Pixabay |
| histórica | Smithsonian, Commons, Web, Openverse |
| recorte (PNG sem fundo) | Web com fundo transparente, Web, Commons → remoção de fundo automática (rembg) |
| logo | Web com fundo transparente, Commons, Web |
| mapa | Commons, Web |
| bandeira | Commons, Web com fundo transparente |
| vídeo | Só bancos livres: Pexels, Pixabay e, se faltar, Commons, Archive. **YouTube removido em 2026-10-11** (bloqueio de IP / acusação de fraude). Baixa só o trecho escolhido, H.264, sem áudio |

Cache em `<dados>/cache/` (buscas por 7 dias, imagens baixadas, limpa sozinho o que passa de 30 dias). Pode apagar a pasta inteira sem perder nada.
| sem resultado bom | Imagem gerada com IA (Higgsfield), só para coisas genéricas, nunca pessoas ou lances reais |

Nenhuma chave de API é obrigatória. Opcionais (grátis), no `.env` do canal (painel › APIs) ou no ambiente: `SI_API_KEY` (Smithsonian, api.data.gov; sem ela o Smithsonian é pulado), `PEXELS_API_KEY`, `PIXABAY_API_KEY` (pixabay.com/api/docs, fotos e vídeos), `SERPER_API_KEY` (serper.dev, Google Imagens; **pago**, sempre a última fonte de imagem e só se faltar candidato). Sem a chave, a fonte é pulada.
Ordem das fontes, tamanho mínimo, nº de candidatos e domínios bloqueados (bancos com marca d'água) ficam em `config.json` (padrão do motor; um canal pode sobrepor qualquer chave em `canal.json` › `busca`).

## Comandos (o Claude roda; você só precisa se quiser)

```bash
cd motor/busca          # PY=../../.venv/bin/python; o canal sai do caminho do <projeto> (ou SM_CANAL)
$PY scripts/transcrever.py   <projeto>
$PY scripts/validar_plano.py <projeto>
$PY scripts/buscar.py        <projeto> [--item 01] [--asset ID --refazer --consulta "..."]
$PY scripts/detalhar_video.py <projeto> <asset> <n_video> <ini> <fim>
$PY scripts/finalizar.py     <projeto> [--asset ID]
$PY scripts/status.py        <projeto> [--pendentes]
```

## Limites conhecidos

- Narração em inglês usa o modelo `small.en`; canal criado com outro idioma já aponta para `ggml-small.bin` (`canal.json` › `busca.whisper_modelo`; o `instalar.sh` baixa).
- O DuckDuckGo às vezes limita a taxa de buscas; basta rodar de novo depois (só busca o que falta).
- Logos de marcas e times quase nunca estão no Wikimedia (material não livre); a busca na web cobre.
- Material da web pode ter direitos autorais. O `creditos.txt` registra a origem e a licença de tudo.

`teste_projeto/` é um exemplo completo (Philly Special, 23 s) que serviu de teste.
