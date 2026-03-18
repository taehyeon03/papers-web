/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "arxiv.org" },
      { protocol: "https", hostname: "*.arxiv.org" },
    ],
  },
};

export default nextConfig;
