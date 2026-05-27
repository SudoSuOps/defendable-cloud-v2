import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// DefendableCloud Vault — React SPA, deployed to app.defendablecloud.com (CF Pages).
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", target: "es2020", sourcemap: false },
  server: { port: 5173, host: true },
});
