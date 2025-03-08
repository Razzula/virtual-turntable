import { describe, test, expect } from "vitest";
import { base64ToBlob } from "../src/utils/blob";

describe("base64ToBlob", () => {
    test("should convert a valid base64 string to a Blob", () => {
        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQImWNgYGD4DwQMLCwsLCws+v///wMAJAcGGEVZySAAAAAASUVORK5CYII=";

        const blob = base64ToBlob(base64Image);

        expect(blob).toBeInstanceOf(Blob);
        expect(blob.type).toBe("image/png");
    });

    test("should default to image/png if MIME type is missing", () => {
        const base64Data =
            "data:;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQImWNgYGD4DwQMLCwsLCws+v///wMAJAcGGEVZySAAAAAASUVORK5CYII=";

        const blob = base64ToBlob(base64Data);

        expect(blob.type).toBe("image/png");
    });

    test("should handle invalid base64 input gracefully", () => {
        const invalidBase64 = "data:image/png;base64,invalid-base64-data";

        expect(() => base64ToBlob(invalidBase64)).toThrow();
    });
});
