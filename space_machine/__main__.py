"""Space Machine — linha de comando.

  python -m space_machine painel [--porta 8765]   painel no navegador (http://localhost:8765)
  python -m space_machine rodar <bloco> [--de etapa] [--ate etapa] [--obs "..."]   roteiro → prévia aprovada
  python -m space_machine fila <pasta do vídeo> [--max 3]   todos os blocos não entregues, até 3 ao mesmo tempo
  python -m space_machine final <pasta do vídeo> [--render]   junta os blocos entregues num projeto do After
  python -m space_machine reels <pasta do bloco>   Reels 9:16 do bloco (montado na vertical) em <vídeo>/reels/
  python -m space_machine escolher <bloco> [--sombra] [--asset ID] [--modelo haiku]
  python -m space_machine checar                     testa o claude (versão, login, modelos) sem rodar nada
  python -m space_machine atalho [--pasta ~/Desktop]  cria o app "Space Machine" na área de trabalho
  python -m space_machine limpar [--cache] [--aplicar]  manda para o Lixo o que o sistema gerou e não serve mais
  python -m space_machine consumo [--video slug]     consumo registrado das chamadas ao Claude
"""
import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "escolher":
        from .escolher import main as m
        m(args)
    elif cmd == "fila":
        from .fila import main as m
        m(args)
    elif cmd == "limpar":
        from .limpeza import main as m
        m(args)
    elif cmd == "atalho":
        from .atalho import main as m
        m(args)
    elif cmd == "final":
        from .final import main as m
        m(args)
    elif cmd == "reels":
        from .reels import main as m
        m(args)
    elif cmd in ("painel", "servidor"):
        from .servidor import main as m
        m(args)
    elif cmd == "rodar":
        from .rodar import main as m
        m(args)
    elif cmd == "checar":
        from .motor_claude import ErroClaude, MODELOS_DA_ETAPA, checar_claude, CHECAGEM, _versao_claude
        CHECAGEM.unlink(missing_ok=True)
        try:
            checar_claude(list(MODELOS_DA_ETAPA))
        except ErroClaude as e:
            print(f"FALHOU: {e}")
            sys.exit(1)
        print(f"ok: claude {_versao_claude()} logado e respondendo com todos os modelos das etapas")
    elif cmd == "consumo":
        from .motor_claude import _banco
        con = _banco()
        filtro, vals = "", ()
        if "--video" in args:
            filtro, vals = "where video = ?", (args[args.index("--video") + 1],)
        for lin in con.execute(f"select video, bloco, etapa, modelo, count(*), sum(equivalente), sum(custo_usd)"
                               f" from chamadas {filtro} group by 1,2,3,4 order by 1,2,3", vals):
            print(f"{lin[0] or '-':40} {lin[1] or '-':4} {lin[2]:18} {lin[3]:8} {lin[4]:>4} chamadas "
                  f"{lin[5] or 0:>10,} equiv.  US$ {lin[6] or 0:.3f}")
    else:
        print(f"comando desconhecido: {cmd}\n{__doc__}")
        sys.exit(2)


if __name__ == "__main__":
    main()
