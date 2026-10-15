// Painel do Space Machine (React). O build vai para space_machine/static/app/, que o FastAPI serve em /app.
// Em desenvolvimento (npm run dev, porta 5173) o Vite repassa a API e as páginas antigas para o painel na 8765.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const PAINEL = "http://127.0.0.1:8765";
const ANTIGAS = ["/api", "/arquivo", "/v/", "/b/", "/canal/", "/config", "/novo/", "/consumo", "/primeiros-passos"];

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  build: { outDir: "../space_machine/static/app", emptyOutDir: true, chunkSizeWarningLimit: 900 },
  server: { port: 5173, proxy: Object.fromEntries(ANTIGAS.map((p) => [p, PAINEL])) },
});
