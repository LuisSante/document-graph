<script lang="ts">
	import DatasetList from '$lib/components/DatasetList.svelte';
	import UploadDropzone from '$lib/components/UploadDropzone.svelte';
	import type { DocumentMeta } from '$lib/types/document';

	let { data } = $props();
	const documents: DocumentMeta[] = data.documents;

	console.log('Loaded documents:', documents);
</script>

<main class="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-6">
	<div class="w-full max-w-7xl space-y-10">

		<header class="text-center space-y-2">
			<h1 class="text-2xl font-semibold">Document Explorer</h1>
			<p class="text-gray-600">
				Select a document from the dataset or upload a new PDF
			</p>
		</header>

		<section class="grid grid-cols-1 md:grid-cols-2 gap-8">
			<div class="bg-white border rounded-lg p-6 shadow-sm">
				<h2 class="font-medium mb-4">Dataset (CUAD)</h2>
				<DatasetList {documents} />
			</div>

			<div class="bg-white border rounded-lg p-6 shadow-sm">
				<h2 class="font-medium mb-4">Upload PDF</h2>
				<UploadDropzone />
			</div>
		</section>

	</div>
</main>
