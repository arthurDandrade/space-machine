"""API do painel React (painel/, servido em /app).

Lê o mesmo que o painel antigo: as pastas (estado.py), a gestão (ideias, publicação) e o consumo no sqlite.
As ações chamam as mesmas funções das rotas antigas (fila.lancar_rodada, fila.lancar_fila, ...).
/api/eventos avisa o navegador quando alguma pasta de produção muda, para a tela se atualizar sozinha.

Um arquivo por assunto (até 2026-11-11 era um api.py só, com 1.450 linhas):
  painel.py        lista de canais, tela do canal, busca, avisos e o /api/eventos (ao vivo)
  videos.py        um vídeo: página, produzir, publicação, thumbnail, vídeo final, arquivar, excluir, lixeira
  blocos.py        um bloco: página, rodar, parar, conferir, Reels, limpar, excluir
  planejamento.py  ideias, calendário, prompts do canal e prompt de roteiro
  canal.py         ajustes do canal: nome, formato, identidade, regras, aprendizados, chaves, narração, modelos
  sistema.py       fora de um canal: consumo, primeiros passos, limpeza, atualização, formatos, canal novo
  pesquisa.py      Modelagem e Mineração
  comum.py         o que mais de um assunto usa: achar canal, vídeo e bloco pelo endereço; resumos
Rota nova vai no arquivo do assunto dela, com `@api.get/post` como as outras. A ordem dentro do arquivo importa
quando dois endereços se parecem (o mais específico vem antes).
"""
from fastapi import APIRouter

from . import blocos, canal, painel, pesquisa, planejamento, sistema, videos

api = APIRouter()
for _m in (painel, videos, blocos, planejamento, canal, sistema, pesquisa):
    api.include_router(_m.api)
