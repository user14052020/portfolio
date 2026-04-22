/** @type {import('next').NextConfig} */
const API_PROXY_TARGET =
  process.env.INTERNAL_API_URL?.replace(/\/api\/v1\/?$/, "") ||
  "http://backend:8000";

const nextConfig = {
  reactStrictMode: true,
  distDir:
    process.env.NODE_ENV === "production"
      ? ".next-production"
      : ".next-development",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_PROXY_TARGET}/api/v1/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${API_PROXY_TARGET}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;