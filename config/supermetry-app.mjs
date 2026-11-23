// Diagnostics-only build metadata. Never import this into renderer/web builds.
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export function generatedSupermetryConfig() {
  return { diagnostics: { sessionPings: false } };
}

export function writeSupermetryConfig(_env = process.env, path = new URL('./supermetry-app.generated.json', import.meta.url)) {
  const config = generatedSupermetryConfig();
  const target = path instanceof URL ? fileURLToPath(path) : path;
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, JSON.stringify(config) + '\n', { mode: 0o600 });
  return config;
}
