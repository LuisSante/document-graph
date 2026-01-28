import { writable } from 'svelte/store';
import type { Paragraph, DocumentMeta, ParagraphRelation } from '$lib/types/document';

export const currentDocument = writable<DocumentMeta | null>(null);
export const pdfUrl = writable<string | null>(null);
export const paragraphs = writable<Paragraph[]>([]); //nodes
export const relations = writable<ParagraphRelation[]>([]); //edges
export const loading = writable<boolean>(false);
export const error = writable<string | null>(null);
export const selectedParagraph = writable<Paragraph | null>(null);
export const contradictions = writable<any[]>([]);
export const paragraphPositions = writable<Map<string, number>>(new Map());
