/**
 * Central runtime configuration.
 * Set NEXT_PUBLIC_API_URL in .env.local (dev) or your deployment environment (prod).
 * Example: NEXT_PUBLIC_API_URL=https://your-backend.herokuapp.com
 */
export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
