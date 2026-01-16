<script lang="ts">
    import { onDestroy } from 'svelte';
    import { pdfUrl } from '$lib/stores/document';
    import * as pdfjsLib from 'pdfjs-dist';
    // @ts-ignore
    import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

    let loading = false;
    let error: string | null = null;
    let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
    let pages: number[] = [];
    let loadTask: any = null;

    $: if ($pdfUrl) {
        loadDocument($pdfUrl);
    }

    async function loadDocument(url: string) {
        loading = true;
        error = null;
        pdfDoc = null;
        pages = [];

        try {
            if (loadTask) {
                loadTask.destroy();
            }

            loadTask = pdfjsLib.getDocument(url);
            pdfDoc = await loadTask.promise;
            
            if (pdfDoc) {
                pages = Array.from({ length: pdfDoc.numPages }, (_, i) => i + 1);
            }
        } catch (err: any) {
            if (err.name !== 'RenderingCancelledException') {
                console.error('Error loading PDF:', err);
                error = 'Failed to load PDF';
            }
        } finally {
            loading = false;
        }
    }

    function renderPage(node: HTMLCanvasElement, pageNum: number) {
        let renderTask: any = null;

        async function render() {
            if (!pdfDoc) return;

            try {
                const page = await pdfDoc.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1.5 });
                
                node.height = viewport.height;
                node.width = viewport.width;
                
                const context = node.getContext('2d');

                if (context) {
                    const renderContext = {
                        canvasContext: context,
                        viewport: viewport
                    };
                    
                    renderTask = page.render(renderContext as any);
                    await renderTask.promise;
                }
            } catch (err: any) {
                if (err.name !== 'RenderingCancelledException') {
                    console.error(`Error rendering page ${pageNum}:`, err);
                }
            }
        }

        render();

        return {
            destroy() {
                if (renderTask) {
                    renderTask.cancel();
                }
            }
        };
    }

    onDestroy(() => {
        if (loadTask) {
            loadTask.destroy();
        }
    });

</script>

<div class="h-full w-full overflow-auto bg-gray-50 flex flex-col items-center p-4 gap-4 relative">
    {#if !$pdfUrl}
        <div class="flex items-center justify-center text-gray-400 h-full w-full absolute">
            No document loaded
        </div>
    {/if}

    {#if loading}
        <div class="absolute inset-0 flex items-center justify-center bg-white/50 z-20">
            <span class="text-blue-600 font-medium">Loading PDF...</span>
        </div>
    {/if}
    
    {#if error}
         <div class="flex items-center justify-center h-full text-red-500 w-full absolute">{error}</div>
    {/if}

    {#if pdfDoc}
        {#each pages as pageNum (pageNum)}
            <div class="shadow-lg bg-white">
                <canvas use:renderPage={pageNum}></canvas>
            </div>
        {/each}
    {/if}
</div>
