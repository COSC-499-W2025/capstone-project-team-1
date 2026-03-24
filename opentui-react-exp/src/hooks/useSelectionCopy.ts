/**
 * Auto-copy selected text to clipboard and show a toast notification.
 *
 * When the user highlights text (mouse drag on a `selectable` element),
 * the selected text is automatically copied to the clipboard via OSC 52
 * and a brief toast is shown.
 */
import { useEffect } from "react";
import { useRenderer } from "@opentui/react";
import type { Selection } from "@opentui/core";
import { useToast } from "../components/Toast";

export function useSelectionCopy() {
	const renderer = useRenderer();
	const toast = useToast();

	useEffect(() => {
		function onSelection(selection: Selection) {
			const text = selection.getSelectedText();
			if (!text) return;

			renderer.copyToClipboardOSC52(text);
			toast.show({
				message: "Copied to clipboard",
				variant: "success",
				duration: 1500,
			});
		}

		renderer.on("selection", onSelection);
		return () => {
			renderer.off("selection", onSelection);
		};
	}, [renderer, toast]);
}
