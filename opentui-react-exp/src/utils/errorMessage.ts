import { ApiError } from "../api/client";

export function toErrorMessage(error: unknown): string {
	if (error instanceof ApiError) {
		return error.message;
	}
	if (error instanceof Error) {
		return error.message;
	}
	return "Unexpected error";
}
