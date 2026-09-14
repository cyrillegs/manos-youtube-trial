import type { NextConfig } from "next";

const backend = (process.env.BACKEND_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/media/:path*",
        destination: `${backend}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;
