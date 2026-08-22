import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "lotto-viewer-mobile",
  brand: {
    primaryColor: "#10b981",
  },
  permissions: [
    {
      name: "clipboard",
      access: "read",
    },
    {
      name: "clipboard",
      access: "write",
    },
  ],
  webBundleDir: "out",
});
