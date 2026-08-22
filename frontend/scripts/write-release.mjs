import { fileURLToPath } from "node:url";
import path from "node:path";

import { writeReleaseMetadata } from "./release-metadata.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
writeReleaseMetadata(path.join(root, "public", "release.json"));
