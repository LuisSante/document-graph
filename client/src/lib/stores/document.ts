import { writable } from 'svelte/store';
import type { Paragraph, DocumentMeta } from '$lib/types/document';

export const currentDocument = writable<DocumentMeta | null>(null);
export const pdfUrl = writable<string | null>(null);
export const paragraphs = writable<Paragraph[]>([]);
export const loading = writable<boolean>(false);
export const error = writable<string | null>(null);
