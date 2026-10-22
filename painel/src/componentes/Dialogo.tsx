// Diálogo de confirmação (Esc ou clique fora cancela). Para ações que mexem em pastas: excluir, juntar no After.
import { ReactNode, useEffect } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";

// largo: para o que é formulário de verdade (criar canal), não só uma pergunta de sim ou não
export function Dialogo({ titulo, children, acoes, fechar, largo }:
{ titulo: ReactNode; children: ReactNode; acoes: ReactNode; fechar: () => void; largo?: boolean }) {
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); fechar(); } };
    window.addEventListener("keydown", tecla, true);
    return () => window.removeEventListener("keydown", tecla, true);
  }, [fechar]);
  return createPortal(
    <div className="dialogo-fundo" onMouseDown={(e) => e.target === e.currentTarget && fechar()}>
      <motion.div className={`dialogo ${largo ? "largo" : ""}`} role="dialog" aria-modal="true" initial={{ opacity: 0, y: 10, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ duration: 0.18 }}>
        <h3>{titulo}</h3>
        <div className="corpo-dialogo">{children}</div>
        <div className="acoes-dialogo">{acoes}</div>
      </motion.div>
    </div>,
    document.body,
  );
}
