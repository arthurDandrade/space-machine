# Buscador de assets — Pro Football

Busca na internet todos os assets de um vídeo no formato "___ Explained" a partir do **roteiro + narração**, e entrega tudo organizado e amarrado à palavra da narração em que cada asset aparece.

## Como usar (pedindo ao Claude)

> "Busca os assets do vídeo X. Roteiro em …, narração em …"

O Claude segue a skill `buscar-assets` (`.claude/skills/buscar-assets/SKILL.md`): planeja as cenas, busca, escolhe, recorta, baixa os trechos de vídeo e te mostra uma página de revisão.

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

Cache em `_cache/` (buscas por 7 dias, imagens baixadas, limpa sozinho o que passa de 30 dias). Pode apagar a pasta inteira sem perder nada.
| sem resultado bom | Imagem gerada com IA (Higgsfield), só para coisas genéricas, nunca pessoas ou lances reais |

Nenhuma chave de API é obrigatória. Opcionais (grátis), em `ProFootball/.env.fontes` ou no ambiente: `SI_API_KEY` (Smithsonian, api.data.gov; sem ela o Smithsonian é pulado), `PEXELS_API_KEY`, `PIXABAY_API_KEY` (pixabay.com/api/docs, fotos e vídeos), `SERPER_API_KEY` (serper.dev, Google Imagens; **pago**, sempre a última fonte de imagem e só se faltar candidato). Sem a chave, a fonte é pulada.
Ordem das fontes, tamanho mínimo, nº de candidatos e domínios bloqueados (bancos com marca d'água) ficam em `config.json`.

## Comandos (o Claude roda; você só precisa se quiser)

```bash
cd /Users/arthur/Canais/ProFootball/buscador_assets
.venv/bin/python scripts/transcrever.py   <projeto>
.venv/bin/python scripts/validar_plano.py <projeto>
.venv/bin/python scripts/buscar.py        <projeto> [--item 01] [--asset ID --refazer --consulta "..."]
.venv/bin/python scripts/detalhar_video.py <projeto> <asset> <n_video> <ini> <fim>
.venv/bin/python scripts/finalizar.py     <projeto> [--asset ID]
.venv/bin/python scripts/status.py        <projeto> [--pendentes]
```

## Limites conhecidos

- Narração em inglês (modelo `small.en`). Para português, baixar `ggml-small.bin` e trocar em `config.json`.
- O DuckDuckGo às vezes limita a taxa de buscas; basta rodar de novo depois (só busca o que falta).
- Times da NFL quase não têm logos no Wikimedia (são material não livre); a busca na web cobre.
- Material da NFL é protegido por direitos autorais. O `creditos.txt` registra a origem de tudo.

`teste_projeto/` é um exemplo completo (Philly Special, 23 s) que serviu de teste.
