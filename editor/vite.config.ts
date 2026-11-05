import { defineConfig } from "vite";
export default defineConfig({
  publicDir: "../motion/public",
  resolve: { dedupe: ["react", "react-dom", "remotion"] },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/media": "http://127.0.0.1:8765",
      "/thumbnail": "http://127.0.0.1:8765",
    },
  },
  build: { outDir: "build", emptyOutDir: true },
});
