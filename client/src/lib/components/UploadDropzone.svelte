<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { currentDocument, paragraphs, loading, error } from '$lib/stores/document';

	async function handleFile(file: File) {
		if (file.type !== 'application/pdf') return;

		loading.set(true);
		error.set(null);
		
		// Set a temporary document meta
		currentDocument.set({
			id: 'temp',
			name: file.name,
			origin: 'upload',
			processed: false
		});

		try {
			const formData = new FormData();
			formData.append('file', file);
			
			goto('/analysis');

			const res = await api.post('/documents/upload', formData, {
				headers: {
					'Content-Type': 'multipart/form-data'
				}
			});
			
			paragraphs.set(res.data);
		} catch (err) {
			console.error(err);
			error.set('Failed to upload document');
		} finally {
			loading.set(false);
		}
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		const file = e.dataTransfer?.files[0];
		if (file) handleFile(file);
	}

	function onSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFile(file);
	}
</script>

<div
	class="border-2 border-dashed rounded-lg p-6 text-center text-gray-500 hover:border-gray-400 transition"
	on:drop={onDrop}
	on:dragover|preventDefault
	role="button"
	tabindex="0"
>
	<p class="mb-2">Drag & drop a PDF here</p>

	<label class="cursor-pointer text-sm text-blue-600 hover:underline">
		or select a file
		<input type="file" accept="application/pdf" class="hidden" on:change={onSelect} />
	</label>
</div>
