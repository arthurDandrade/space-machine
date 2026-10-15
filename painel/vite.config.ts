// Painel do Space Machine (React). O build vai para space_machine/static/app/, que o FastAPI serve na raiz.
// Em desenvolvimento (npm run dev, porta 5173) o Vite repassa a API e os arquivos da produção para o painel na 8765.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const PAINEL = "http://127.0.0.1:8765";
const DO_SERVIDOR = ["/api", "/arquivo"];

export default defineConfig({
  base: "/",
  plugins: [react()],
  build: { outDir: "../space_machine/static/app", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  server: { port: 5173, proxy: Object.fromEntries(DO_SERVIDOR.map((p) => [p, PAINEL])) },
});
