import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

const isDocker = process.env.DOCKER === "true";

const apiTarget = isDocker
  ? "http://scanupload.python.example:8080"
  : "http://localhost:8080";

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    rollupOptions: {
      onwarn(warning, warn) {
        if (
          warning.code === "INVALID_ANNOTATION" &&
          warning.id?.includes("@microsoft/signalr/dist/esm/Utils.js")
        ) {
          return;
        }

        warn(warning);
      },
    },
  },
  server: {
    host: true,
    strictPort: true,
    port: 3002,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/scanupload-api": {
        target: apiTarget,
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
});
