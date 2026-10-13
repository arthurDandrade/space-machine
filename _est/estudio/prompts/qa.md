<!-- Correção automática depois de um QA reprovado (rodar.py _corrigir_qa). Regras do QA: conhecimento/<canal>/04 - Edição/Controle de Qualidade.md -->
# Correção depois do QA
O bloco já foi montado no After Effects e o controle de qualidade (qa_bloco.py) reprovou. Cada FALHA diz o que está fora da medida das referências (ex.: texto pequeno demais porque a frase é longa, asset que fica menos de 1,8 s na tela, card esticado, cena vazia). Corrija só o que as FALHAS pedem, no cenas.json:
- texto pequeno → frase mais curta (2–6 palavras) ou "2linhas";
- asset curto → juntar trocas, mover o gatilho para uma palavra mais cedo/tarde, ou tirar o asset;
- mantenha os "id" dos cards que continuam (eles já têm arquivo baixado); card novo vem sem "id" e será buscado.
Responda SÓ com o JSON do cenas.json completo.
