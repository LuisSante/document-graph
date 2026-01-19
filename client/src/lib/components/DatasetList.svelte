<script lang="ts">
	import type { DocumentMeta } from '$lib/types/document';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { currentDocument, paragraphs, loading, error, pdfUrl, selectedParagraph } from '$lib/stores/document';
	import { PUBLIC_DEV_LOCAL } from '$env/static/public';

	export let documents: DocumentMeta[];
	let query = '';

	$: filteredDocuments = documents.filter((doc) =>
		doc.name.toLowerCase().includes(query.toLowerCase())
	);

	async function selectDocument(doc: DocumentMeta) {
		currentDocument.set(doc);
		pdfUrl.set(`${PUBLIC_DEV_LOCAL}/${doc.id}/pdf`);
		loading.set(true);
		error.set(null);
		selectedParagraph.set(null);
		
		try {
			const formData = new FormData();
			formData.append('document_id', doc.id);
			
			const res = await api.post('/process', formData);
			if (res.data && res.data.nodes) {
				console.log('Setting paragraphs:', res.data.nodes);
				
				paragraphs.set(res.data.nodes);
			
				goto('/analysis');
			
			} else {
				paragraphs.set([]);
			}
		} catch (err) {
			error.set('Error processing document');
		} finally {
			loading.set(false);
		}
	}
</script>

<input
	type="text"
	placeholder="Search document..."
	class="w-full mb-3 px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring"
	bind:value={query}
/>

<ul class="space-y-2 max-h-80 overflow-y-auto pr-1">
	{#if filteredDocuments.length === 0}
		<li class="text-sm text-gray-500 italic">
			No documents found
		</li>
	{:else}
		{#each filteredDocuments as doc}
			<li>
				<button
					class="w-full text-left px-3 py-2 rounded hover:bg-gray-100 transition cursor-pointer"
					on:click={() => selectDocument(doc)}
				>
					 📄 {doc.name}
				</button>
			</li>
		{/each}
	{/if}
</ul>
