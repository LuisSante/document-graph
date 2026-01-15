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
  order: number;
  text: string;
  bbox: [number, number, number, number]; // pdf.js coords
  relationsCount: number;
}

export interface ParagraphRelation {
  fromId: string;
  toId: string;
  type: 'implicit' | 'explicit';
  score?: number;
}
