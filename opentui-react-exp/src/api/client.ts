export class ApiError extends Error {
	status: number;
	data: unknown;
	constructor(status: number, message: string, data?: unknown) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.data = data;
	}
}

type RequestOptions = {
	method?: string;
	headers?: Record<string, string>;
	body?: BodyInit | null;
	signal?: AbortSignal;
};
type ClientOptions = { baseUrl?: string; timeoutMs?: number };

const getEnv = (key: string): string | undefined =>
	typeof process === "undefined"
		? undefined
		: process.env
			? process.env[key]
			: undefined;

export class ApiClient {
	baseUrl: string;
	timeoutMs: number;
	constructor(options: ClientOptions = {}) {
		const envBaseUrl = getEnv("ARTIFACT_MINER_API_URL");
		const envTimeout = getEnv("ARTIFACT_MINER_TIMEOUT");
		this.baseUrl = options.baseUrl ?? envBaseUrl ?? "http://127.0.0.1:8000";
		this.timeoutMs = options.timeoutMs ?? (Number(envTimeout) || 30000);
	}
	private async request<T>(
		path: string,
		options: RequestOptions = {},
	): Promise<T> {
		const url = `${this.baseUrl}${path}`;
		const timeoutSignal =
			typeof AbortSignal !== "undefined" && "timeout" in AbortSignal
				? AbortSignal.timeout(this.timeoutMs)
				: undefined;
		const response = await fetch(url, {
			...options,
			signal: options.signal ?? timeoutSignal,
		});
		const contentType = response.headers.get("content-type") || "";
		const isJson = contentType.includes("application/json");
		const data =
			response.status === 204
				? undefined
				: isJson
					? await response.json()
					: await response.text();
		if (!response.ok) {
			const message =
				data && typeof data === "object" && "detail" in data
					? String((data as { detail: string }).detail)
					: response.statusText || "Request failed";
			throw new ApiError(response.status, message, data);
		}
		return data as T;
	}
	get<T>(path: string): Promise<T> {
		return this.request<T>(path, { method: "GET" });
	}
	post<T>(path: string, body?: unknown): Promise<T> {
		const hasBody = body !== undefined;
		return this.request<T>(path, {
			method: "POST",
			headers: hasBody ? { "Content-Type": "application/json" } : undefined,
			body: hasBody ? JSON.stringify(body) : undefined,
		});
	}
	put<T>(path: string, body?: unknown): Promise<T> {
		const hasBody = body !== undefined;
		return this.request<T>(path, {
			method: "PUT",
			headers: hasBody ? { "Content-Type": "application/json" } : undefined,
			body: hasBody ? JSON.stringify(body) : undefined,
		});
	}
	delete<T>(path: string): Promise<T> {
		return this.request<T>(path, { method: "DELETE" });
	}
	uploadFile<T>(
		path: string,
		file: Blob,
		fieldName = "file",
		extraFields?: Record<string, string>,
	): Promise<T> {
		const formData = new FormData();
		formData.append(fieldName, file);
		if (extraFields) {
			for (const [key, value] of Object.entries(extraFields)) {
				formData.append(key, value);
			}
		}
		return this.request<T>(path, { method: "POST", body: formData });
	}
}
