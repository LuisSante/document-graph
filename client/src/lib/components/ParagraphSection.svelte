<script>
    import { paragraphs, loading, error } from '$lib/stores/document';
</script>

<section class="h-full overflow-y-auto">
    {#if $loading}
        <div class="flex items-center justify-center h-full text-gray-500">
            Processing document...
        </div>
    {:else if $error}
        <div class="text-red-500 p-4">{$error}</div>
    {:else if $paragraphs.length === 0}
        <div class="text-gray-400 italic p-4">No paragraphs loaded</div>
    {:else}
        <div class="space-y-4">
            {#each $paragraphs as paragraph}
                <div class="p-3 bg-gray-50 rounded hover:bg-gray-100 transition text-sm">
                    <div class="text-xs text-gray-400 mb-1">
                        Page {paragraph.page} • Order {paragraph.order}
                    </div>
                    <p>{paragraph.text}</p>
                </div>
            {/each}
        </div>
    {/if}
</section>