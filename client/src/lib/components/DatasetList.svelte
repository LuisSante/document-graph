<script lang="ts">
	import type { DocumentMeta } from '$lib/types/document';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { currentDocument, paragraphs, loading, error } from '$lib/stores/document';

	export let documents: DocumentMeta[];

	let query = '';

	$: filteredDocuments = documents.filter((doc) =>
		doc.name.toLowerCase().includes(query.toLowerCase())
	);

	async function selectDocument(doc: DocumentMeta) {
		console.log('Selected', doc.id);
		currentDocument.set(doc);
		loading.set(true);
		error.set(null);
		
		try {
			// Navigate immediately to analysis page
			goto('/analysis');
			
			// Fetch paragraphs
			const res = await api.get(`/documents/${doc.id}/paragraphs`);
			paragraphs.set(res.data);
		} catch (err) {
			console.error(err);
			error.set('Failed to load document');
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
