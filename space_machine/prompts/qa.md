<!-- Correção automática depois de um QA reprovado (rodar.py _corrigir_qa). Regras do QA: formatos/explained/conhecimento/04 - Edição/Controle de Qualidade.md -->
# Correção depois do QA
O bloco já foi montado no After Effects e o controle de qualidade (qa_bloco.py) reprovou. Cada FALHA vem com os tempos (↳) em que o defeito aparece. Corrija só o que as FALHAS pedem, no cenas.json, mexendo o mínimo possível:
- **Palco vazio** (tela só com papel por mais de 0,5 s): a cena seguinte entra mais cedo (gatilho numa palavra anterior) ou a anterior fica até a próxima entrar.
- **Texto cortado na borda**: frase mais curta, "2linhas" ou outro layout para aquela cena (o zoom da cena empurra texto comprido para fora do quadro).
- **Tamanho do texto solo** ou **do nome/rótulo junto dos cards** pequeno: frase ou nome mais curto (2–6 palavras) ou "2linhas".
- **Texto por cima de imagem**: o texto vai para um layout com rótulo ao lado ou acima do card, ou sai.
- **Texto pouco tempo na tela** (menos de 0,7 s): junte textos seguidos ou mova o gatilho para o texto ficar pelo menos 1 s.
- **Origem dos assets** (banco com marca d'água ou assunto proibido no tema): troque aquele card por um card novo, sem "id", com a mesma descrição; ele será buscado de novo.
- Mantenha cada asset ≥ 1,8 s na tela.
- Mantenha os "id" dos cards que continuam (eles já têm arquivo baixado); card novo vem sem "id" e será buscado.
Responda SÓ com o JSON do cenas.json completo.
