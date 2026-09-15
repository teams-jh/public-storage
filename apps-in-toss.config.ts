import { defineConfig } from "@apps-in-toss/web-framework/config";

import { CURRENT_APP_NAME } from "./src/constants/global_constants";

export default defineConfig({
  appName: CURRENT_APP_NAME,
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
