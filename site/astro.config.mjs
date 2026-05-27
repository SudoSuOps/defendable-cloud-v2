import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import sitemap from "@astrojs/sitemap";

// DefendableCloud — clean static marketing site.
// Built with Astro, deployed to defendablecloud.com via Cloudflare Pages.
export default defineConfig({
  site: "https://defendablecloud.com",
  output: "static",
  integrations: [tailwind(), sitemap()],
  server: {
    port: 4321,
    host: true,
  },
});
