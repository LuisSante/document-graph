<script lang="ts">
    import { onDestroy } from 'svelte';
    import * as pdfjsLib from 'pdfjs-dist';
    // @ts-ignore
    import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
    import { 
		selectedParagraph, 
		paragraphs, 
		relations,
		paragraphPositions,
        pdfUrl
	} from '$lib/stores/document';
	import type { Paragraph, ParagraphRelation } from '$lib/types/document';
    
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

                // Draw relations count
                if (p.relationsCount > 0) {
                    const text = p.relationsCount.toString();
                    // Increased font size
                    context.font = 'bold 16px Arial';
                    const textWidth = context.measureText(text).width;
                    
                    // Increased padding and specific dimensions
                    const bgPadding = 8;
                    const boxHeight = 26;
                    const boxX = (x2 * scale) + 2;
                    // Center vertically relative to the top of the paragraph, or just slight offset
                    const boxY = (y1 * scale);
                    
                    // Draw background for text (larger box)
                    context.fillStyle = 'rgba(255, 0, 0, 0.7)';
                    context.fillRect(boxX, boxY, textWidth + (bgPadding * 2), boxHeight);
                    
                    // Draw text (centered in Y)
                    context.fillStyle = 'white';
                    context.textBaseline = 'middle';
                    context.fillText(text, boxX + bgPadding, boxY + (boxHeight / 2));
                }
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

    /*-------------------------------------------------------------------*/

    let relatedParagraphs: (Paragraph & { relationType: 'reference' | 'semantic_similarity' })[] = [];

    function fetchRelatedParagraphs(
        paragraph: Paragraph | null,
        allParagraphs: Paragraph[],
        allRelations: ParagraphRelation[]
    ) {
        if (!paragraph) {
            relatedParagraphs = [];
            return;
        }

        console.log('All Relations:', allRelations);
        relatedParagraphs = allRelations
            .filter((r) => r.source === paragraph.id || r.target === paragraph.id)
            .map((r) => {
                const targetId = r.source === paragraph.id ? r.target : r.source;
                const targetParagraph = allParagraphs.find((p) => p.id === targetId);

                if (!targetParagraph) return null;

                return {
                    ...targetParagraph,
                    relationType: r.type
                };
            })
            .filter((p): p is Paragraph & { relationType: 'reference' | 'semantic_similarity' } => p !== null);
    }

    $: fetchRelatedParagraphs($selectedParagraph, $paragraphs, $relations);

</script>

<main class="flex h-screen w-full box-border p-4 gap-4">
    <div class="flex-1 min-w-0 rounded-lg border border-gray-200 p-4">
        <div
            class="h-full w-full overflow-auto bg-gray-50 flex flex-col items-center p-4 gap-4 relative"
            style="direction: rtl;" 
        >
            <div style="direction: ltr; width: 100%; display: flex; flex-direction: column; align-items: center; gap: 1rem;">
                
                {#if !$pdfUrl}
                    <div class="flex items-center justify-center text-gray-400 h-full w-full absolute">
                        No document loaded
                    </div>
                {/if}

                {#if pdfDoc}
                    {#each pages as pageNum (pageNum)}
                        <div class="shadow-lg bg-white relative">
                            <canvas use:renderPage={pageNum} on:click={(e) => handlePageClick(e, pageNum)}></canvas>
                        </div>
                    {/each}
                {/if}
            </div>
        </div>
    </div>

    <div class="flex-1 min-w-0 rounded-lg border border-gray-200 p-4">
        <div class="h-full overflow-y-auto p-4">
            {#if !$selectedParagraph}
                <div class="text-gray-500">Select a paragraph to see its relations.</div>
            {:else}
            
                <div class="mb-6">
                    <div class="flex justify-between items-start mb-6">
                        <h3 class="font-bold">Selected Paragraph</h3>
                        <div class="flex flex-col gap-1 text-xs">
                            <div class="flex items-center gap-2">
                                <div class="w-3 h-3 bg-blue-200 border border-blue-800"></div>
                                <span>Reference</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <div class="w-3 h-3 bg-green-300 border border-green-800"></div>
                                <span>Semantic Similarity</span>
                            </div>
                        </div>
                    </div>
                    <p class="text-sm text-gray-700 p-3 bg-gray-100 rounded border-l-4 border-yellow-500">
                        {$selectedParagraph.text}
                    </p>
                </div>
        
                {#if relatedParagraphs.length > 0}
                    <div>
                        <h3 class="font-bold mb-3">Related Paragraphs</h3>
                        <div class="flex flex-col gap-3">
                            {#each relatedParagraphs as p}
                                <div
                                    class="p-3 rounded-lg text-sm transition-all border {p.relationType === 'reference' ? 'bg-blue-100 border-blue-200' : 'bg-green-100 border-green-200'}"
                                >
                                    <span class="text-xs font-bold uppercase block mb-1 opacity-60">{p.relationType}</span>
                                    {p.text}
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            {/if}
        </div>
    </div>
</main>
