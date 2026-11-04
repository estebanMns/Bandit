import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  { ignores: [".next/**", "next-env.d.ts", "public/sw.js"] },
  ...nextVitals,
  ...nextTypescript,
];

export default config;
