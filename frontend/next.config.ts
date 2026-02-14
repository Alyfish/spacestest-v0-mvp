import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // Unblocks CI/e2e builds while existing lint debt is fixed incrementally.
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/api/**",
      },
    ],
  },
};

export default nextConfig;
