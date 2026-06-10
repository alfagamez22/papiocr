import type { NextConfig } from "next";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const isDev = process.env.NODE_ENV !== "production";
const projectRoot = dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  ...(isDev ? {} : { output: "export" as const }),
  images: { unoptimized: true },
  turbopack: { root: projectRoot },
  trailingSlash: true,
};

export default nextConfig;
