import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

const nextConfig: NextConfig = {
  ...(isDev ? {} : { output: "export" as const }),
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
