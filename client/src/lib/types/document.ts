export interface DocumentMeta {
	id: string;
	name: string;
	origin: 'dataset' | 'upload';
	processed: boolean;
}

export interface Paragraph {
	id: string;
	documentId: string;
	page: number;
	paragraph_enum: number;
	text: string;
	bbox: [number, number, number, number]; // pdf.js coords
	relationsCount: number;
}

export interface ParagraphRelation {
	source: string;
	target: string;
	type: 'reference' | 'semantic_similarity';
	score?: number;
}
