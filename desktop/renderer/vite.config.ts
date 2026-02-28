import { defineConfig } from "vite";
import path from "node:path";

export default defineConfig({
  root: path.resolve(__dirname),
  base: "./",
  server: {
    host: "127.0.0.1",
    port: process.env.PORT ? parseInt(process.env.PORT, 10) : 5173,
    strictPort: false,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
