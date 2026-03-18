import { createContext, useCallback, useContext, useState, useEffect, type ReactNode } from "react";
import { useTerminalDimensions } from "@opentui/react";
import { theme } from "../types";

type ToastVariant = "info" | "success" | "warning" | "error";

interface ToastOptions {
	message: string;
	title?: string;
	variant?: ToastVariant;
	/** Auto-dismiss duration in ms. Default 5000 */
	duration?: number;
}

interface ToastState extends Omit<ToastOptions, "duration"> {
	variant: ToastVariant;
}

interface ToastContextValue {
	show: (options: ToastOptions) => void;
	error: (err: unknown) => void;
	dismiss: () => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const VARIANT_COLORS: Record<ToastVariant, string> = {
	info: theme.cyan,
	success: theme.success,
	warning: theme.warning,
	error: theme.error,
};

export function ToastProvider({ children }: { children: ReactNode }) {
	const [toast, setToast] = useState<ToastState | null>(null);
	const [timeoutId, setTimeoutId] = useState<ReturnType<typeof setTimeout> | null>(null);

	const dismiss = useCallback(() => setToast(null), []);

	const show = useCallback((options: ToastOptions) => {
		if (timeoutId) clearTimeout(timeoutId);
		setToast({
			message: options.message,
			title: options.title,
			variant: options.variant ?? "info",
		});
		const id = setTimeout(() => {
			setToast(null);
		}, options.duration ?? 5000);
		setTimeoutId(id);
	}, [timeoutId]);

	const error = useCallback((err: unknown) => {
		const message = err instanceof Error ? err.message : "An unknown error occurred";
		show({ variant: "error", message });
	}, [show]);

	return (
		<ToastContext.Provider value={{ show, error, dismiss }}>
			{children}
			{toast ? <ToastDisplay toast={toast} onDismiss={dismiss} /> : null}
		</ToastContext.Provider>
	);
}

function ToastDisplay({ toast, onDismiss }: { toast: ToastState; onDismiss: () => void }) {
	const { width } = useTerminalDimensions();
	const color = VARIANT_COLORS[toast.variant];

	return (
		<box
			position="absolute"
			top={2}
			right={2}
			maxWidth={Math.min(60, width - 6)}
			paddingLeft={2}
			paddingRight={2}
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgMedium}
			borderLeft
			borderRight
			borderTop={false}
			borderBottom={false}
			borderColor={color}
			onMouseDown={onDismiss}
		>
			{toast.title ? (
				<text fg={theme.textPrimary}>
					<strong>{toast.title}</strong>
				</text>
			) : null}
			<text fg={theme.textSecondary}>{toast.message}</text>
		</box>
	);
}

export function useToast(): ToastContextValue {
	const ctx = useContext(ToastContext);
	if (!ctx) throw new Error("useToast must be used within a ToastProvider");
	return ctx;
}
