<script lang="ts">
	import { selectedParagraph } from '$lib/stores/document';
	import type { Paragraph } from '$lib/types/document';

	let relatedParagraphs: (Paragraph & { relationType: 'reference' | 'semantic_similarity' })[] = [];

	async function fetchRelatedParagraphs(paragraph: Paragraph | null) {
		if (!paragraph) {
			relatedParagraphs = [];
			return;
		}

	}

	$: fetchRelatedParagraphs($selectedParagraph);
</script>

<section class="h-full overflow-y-auto p-4">
	{#if !$selectedParagraph}
		<div class="text-gray-500">Select a paragraph to see its relations.</div>
	{:else}
		<div class="mb-4">
			<h3 class="font-bold">Selected Paragraph</h3>
			<p class="text-sm text-gray-700 p-2 bg-gray-100 rounded">{$selectedParagraph.text}</p>
		</div>

		{#if relatedParagraphs.length > 0}
			<div>
				<h3 class="font-bold mb-2">Related Paragraphs</h3>
				<div class="flex flex-col gap-2">
					{#each relatedParagraphs as p}
						<div
							class="p-2 rounded text-sm"
							class:bg-blue-100={p.relationType === 'reference'}
							class:text-blue-800={p.relationType === 'reference'}
							class:bg-green-100={p.relationType === 'semantic_similarity'}
							class:text-green-800={p.relationType === 'semantic_similarity'}
						>
							{p.text}
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</section>