<script lang="ts">
    import { onDestroy } from 'svelte';
    import { pdfUrl, paragraphs, selectedParagraph } from '$lib/stores/document';
    import * as pdfjsLib from 'pdfjs-dist';
    // @ts-ignore
    import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;
    
    const scale = 1.5;

    let loading = false;
    let error: string | null = null;
    let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
    let pages: number[] = [];
    let loadTask: any = null;
    let pageNodes: (HTMLCanvasElement | null)[] = [];

    $: if ($pdfUrl) {
        loadDocument($pdfUrl);
    }

    function drawBoundingBoxes(pageNum: number) {
        const canvas = pageNodes[pageNum - 1];
        if (!canvas || !pdfDoc) return;
        const context = canvas.getContext('2d');
        if (!context) return;

        $paragraphs.forEach(p => {
            if (p.page === pageNum) {
                const [x1, y1, x2, y2] = p.bbox;
                
                if ($selectedParagraph && $selectedParagraph.id === p.id) {
                    context.strokeStyle = 'rgba(255, 215, 0, 1)'; // Gold for selected
                    context.lineWidth = 2;
                } else {
                    context.strokeStyle = 'rgba(0, 0, 255, 0.5)'; // Blue for others
                    context.lineWidth = 1;
                }
                context.strokeRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
            }
        });
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

    function handlePageClick(event: MouseEvent, pageNum: number) {
        const canvas = pageNodes[pageNum - 1];
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        const clickedParagraph = $paragraphs.find(p => {
            if (p.page !== pageNum) return false;
            
            const [x1, y1, x2, y2] = p.bbox;
            return x >= x1 * scale && x <= x2 * scale && y >= y1 * scale && y <= y2 * scale;
        });

        if (clickedParagraph) {
            $selectedParagraph = clickedParagraph;
        }
    }

    function renderPage(node: HTMLCanvasElement, pageNum: number) {
        let renderTask: any = null;
        pageNodes[pageNum - 1] = node;

        async function render() {
            if (!pdfDoc) return;

            try {
                const page = await pdfDoc.getPage(pageNum);
                const viewport = page.getViewport({ scale: scale });
                
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

                    drawBoundingBoxes(pageNum);
                }
            } catch (err: any) {
                if (err.name !== 'RenderingCancelledException') {
                    console.error(`Error rendering page ${pageNum}:`, err);
                }
            }
        }

        render();

        return {
            update() {
                render();
            },
            destroy() {
                if (renderTask) {
                    renderTask.cancel();
                }
            }
        };
    }

    $: if(pdfDoc && $paragraphs) {
        pages.forEach(pageNum => {
            const canvas = pageNodes[pageNum - 1];
            if (canvas) {
                // The action will re-render when paragraphs change, but we need to trigger update for selected paragraph
            }
        });
    }

    $: if ($selectedParagraph && pageNodes.length > 0) {
        pages.forEach(pageNum => {
            const canvas = pageNodes[pageNum - 1];
            if(canvas){
                const context = canvas.getContext('2d');
                if(context && pdfDoc){
                    pdfDoc.getPage(pageNum).then(page => {
                        const viewport = page.getViewport({ scale: scale });
                        const renderContext = {
                            canvasContext: context,
                            viewport: viewport
                        };
                        page.render(renderContext as any).promise.then(() => {
                            drawBoundingBoxes(pageNum);
                        });
                    });
                }
            }
        });
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
            <div class="shadow-lg bg-white relative">
                <canvas use:renderPage={pageNum} on:click={(e) => handlePageClick(e, pageNum)}></canvas>
            </div>
        {/each}
    {/if}
</div>
