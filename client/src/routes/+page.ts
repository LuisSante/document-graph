import type { PageLoad } from './$types';
import type { DocumentMeta } from '$lib/types/document';
import { api } from '$lib/api/client';

export const load: PageLoad = async () => {
	const res = await api.get<DocumentMeta[]>('/list_documents');
    
	return {
		documents: res.data
	};
};
