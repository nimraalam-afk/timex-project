import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Minimal Vite config. Frontend runs on 5173 and calls the FastAPI backend on 8000.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
