import { expect, test } from "bun:test";
import { ApiClient, ApiError } from "./client";

const withMockFetch = async (
	mock: typeof fetch,
	fn: () => Promise<void>
): Promise<void> => {
	const originalFetch = globalThis.fetch;
	globalThis.fetch = mock;
	try {
		await fn();
	} finally {
		globalThis.fetch = originalFetch;
	}
};

test("ApiClient.get returns JSON", async () => {
	await withMockFetch(async (url) => {
		expect(String(url)).toBe("http://example.test/health");
		return new Response(JSON.stringify({ ok: true }), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	}, async () => {
		const client = new ApiClient({ baseUrl: "http://example.test" });
		const result = await client.get<{ ok: boolean }>("/health");
		expect(result.ok).toBe(true);
	});
});

test("ApiClient throws ApiError with detail", async () => {
	await withMockFetch(async () => {
		return new Response(JSON.stringify({ detail: "Bad request" }), {
			status: 400,
			headers: { "Content-Type": "application/json" },
		});
	}, async () => {
		const client = new ApiClient({ baseUrl: "http://example.test" });
		await expect(client.get("/broken")).rejects.toThrow(ApiError);
		await expect(client.get("/broken")).rejects.toMatchObject({
			status: 400,
			message: "Bad request",
		});
	});
});

test("ApiClient.uploadFile sends FormData", async () => {
	let captured: RequestInit | undefined;
	await withMockFetch(async (_url, options) => {
		captured = options;
		return new Response(JSON.stringify({ ok: true }), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	}, async () => {
		const client = new ApiClient({ baseUrl: "http://example.test" });
		await client.uploadFile("/zip/upload", new Blob(["zip"]), "file", {
			portfolio_id: "abc",
		});
	});

	expect(captured?.method).toBe("POST");
	expect(captured?.body instanceof FormData).toBe(true);
	const formData = captured?.body as FormData;
	expect(formData.get("file")).toBeTruthy();
	expect(formData.get("portfolio_id")).toBe("abc");
});
