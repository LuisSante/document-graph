<script>
    import PdfSection from '$lib/components/PdfSection.svelte';
    import ParagraphSection from '$lib/components/ParagraphSection.svelte';
</script>

<main class="flex h-screen w-full box-border p-4 gap-4">
    <section class="flex-1 min-w-0 rounded-lg border border-gray-200 p-4">
        <PdfSection />
    </section>

    <section class="flex-1 min-w-0 rounded-lg border border-gray-200 p-4">
        <ParagraphSection />
    </section>
</main>
