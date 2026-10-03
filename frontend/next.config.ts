import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The default bottom-left spot covers the sidebar's account menu
  devIndicators: { position: "bottom-right" },
  // Serve the FastAPI backend under /api on the same origin, so auth cookies are
  // first-party and no CORS setup is needed.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }];
  },
};

export default nextConfig;
