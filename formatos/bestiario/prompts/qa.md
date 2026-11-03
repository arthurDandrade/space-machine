<!-- Correção automática depois de um QA reprovado (rodar.py _corrigir_qa). Regras do QA: formatos/bestiario/conhecimento/04 - Edição/Visual do Bestiário.md -->
# Correção depois do QA
O bloco já foi montado no After Effects e o controle de qualidade (qa_bloco.py) reprovou. Cada FALHA vem com os tempos (↳) em que o defeito aparece. Corrija só o que as FALHAS pedem, no cenas.json, mexendo o mínimo possível:
- **Palco vazio** (tela preta por mais de 0,5 s no meio do bloco): a cena seguinte entra mais cedo (gatilho numa palavra anterior) ou a anterior fica até a próxima entrar. Gravura muito escura ou muito pequena também mede como tela vazia: troque por outra (card novo, sem "id").
- **Texto pouco tempo na tela** (menos de 0,7 s): junte textos seguidos ou mova o gatilho para o texto ficar pelo menos 1 s.
- **Origem dos assets** (banco com marca d'água ou assunto proibido no tema): troque aquele card por um card novo, sem "id", com a mesma descrição; ele será buscado de novo.
- Mantenha cada asset ≥ 1,8 s na tela.
- Mantenha os "id" dos cards que continuam (eles já têm arquivo); card novo vem sem "id" e será buscado (ilustração nova é gerada de novo e custa).
Responda SÓ com o JSON do cenas.json completo.
