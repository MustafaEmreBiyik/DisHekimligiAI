import { describe, it, expect } from "vitest";
import axios from "axios";

// We only test the pure utility function, not the axios instance itself.
// The axios instance requires a live Next.js environment (localStorage, etc.)
// so we import only the helper.
import { getApiErrorMessage } from "@/lib/api";

describe("getApiErrorMessage", () => {
  it("returns the fallback string when the error is unknown", () => {
    expect(getApiErrorMessage("not an error object", "default")).toBe("default");
  });

  it("returns the Error message when a standard Error is passed", () => {
    const err = new Error("network failure");
    expect(getApiErrorMessage(err, "default")).toBe("network failure");
  });

  it("returns the fallback when error is null", () => {
    expect(getApiErrorMessage(null, "fallback text")).toBe("fallback text");
  });

  it("extracts detail from an AxiosError response body", () => {
    const axiosError = new axios.AxiosError(
      "Request failed",
      "ERR_BAD_RESPONSE",
      undefined,
      undefined,
      {
        data: { detail: "Geçersiz kimlik bilgileri" },
        status: 401,
        statusText: "Unauthorized",
        headers: {},
        config: { headers: axios.defaults.headers as never },
      }
    );
    expect(getApiErrorMessage(axiosError, "default")).toBe("Geçersiz kimlik bilgileri");
  });

  it("falls back to the AxiosError message when response has no detail", () => {
    const axiosError = new axios.AxiosError("Timeout exceeded");
    expect(getApiErrorMessage(axiosError, "default")).toBe("Timeout exceeded");
  });
});
