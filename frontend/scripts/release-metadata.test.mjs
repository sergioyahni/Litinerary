import { describe, expect, it } from "vitest";

import { releaseMetadata, resolveReleaseSha } from "./release-metadata.mjs";

describe("release metadata", () => {
  it("uses the Render commit SHA when present", () => {
    expect(
      resolveReleaseSha({
        RENDER_GIT_COMMIT: "ABCDEF1234567890abcdef1234567890abcdef12",
        VITE_RELEASE_SHA: "1111111",
      }),
    ).toBe("abcdef1234567890abcdef1234567890abcdef12");
  });

  it("falls back to unknown for unsafe values", () => {
    expect(resolveReleaseSha({ RENDER_GIT_COMMIT: "https://example.test/secret" })).toBe(
      "unknown",
    );
  });

  it("emits only safe release metadata", () => {
    expect(releaseMetadata({ GITHUB_SHA: "abcdef1", SECRET: "do-not-emit" })).toEqual({
      releaseSha: "abcdef1",
    });
  });
});
