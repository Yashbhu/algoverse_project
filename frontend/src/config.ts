// src/config.ts
const isLocalhost = window.location.hostname === "localhost";

export const API_BASE_URL = isLocalhost
  ? "http://localhost:6969"
  : "https://osint-1-r7m0.onrender.com";