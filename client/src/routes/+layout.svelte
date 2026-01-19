<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { loading } from '$lib/stores/document';
	import { fade } from 'svelte/transition';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if $loading}
	<div 
		transition:fade 
		class="fixed top-4 right-4 z-50 flex items-center gap-3 bg-white border border-gray-200 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-gray-700"
	>
		<div class="animate-spin rounded-full h-4 w-4 border-2 border-gray-600 border-t-transparent"></div>
		Loading...
	</div>
{/if}

{@render children()}
