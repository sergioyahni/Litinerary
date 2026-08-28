import fs from "node:fs";
import path from "node:path";

const SAFE_SHA = /^[0-9a-fA-F]{7,40}$/;

export function resolveReleaseSha(env = process.env) {
  for (const name of ["RENDER_GIT_COMMIT", "VITE_RELEASE_SHA", "GITHUB_SHA"]) {
    const value = env[name];
    if (typeof value === "string" && SAFE_SHA.test(value.trim())) {
      return value.trim().toLowerCase();
    }
  }
  return "unknown";
}

export function releaseMetadata(env = process.env) {
  return { releaseSha: resolveReleaseSha(env) };
}

export function writeReleaseMetadata(outputPath, env = process.env) {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(
    outputPath,
    `${JSON.stringify(releaseMetadata(env), null, 2)}\n`,
    "utf8",
  );
}
