/**
 * PDFViewer — renders the FDA PDF with reactive bounding-box overlays.
 *
 * How bboxes work:
 *   - Docling outputs normalised coordinates (0–1) relative to page dimensions
 *   - We scale them to the rendered canvas width/height at display time
 *   - The focused item's bbox is highlighted with a stronger border
 *
 * Dependency: react-pdf (wraps pdf.js)
 * Worker is loaded from CDN to avoid bundling issues.
 */
import { useCallback, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

import { useDAStore } from '@/store/daStore'
import type { DeviationLineItem } from '@/types'

// pdf.js worker — served from CDN (matches react-pdf v9 peer dep)
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface Props {
  pdfUrl: string
  items: DeviationLineItem[]
}

export function PDFViewer({ pdfUrl, items }: Props) {
  const currentPage = useDAStore((s) => s.currentPage)
  const setCurrentPage = useDAStore((s) => s.setCurrentPage)
  const setTotalPages = useDAStore((s) => s.setTotalPages)
  const focusedItemId = useDAStore((s) => s.focusedItemId)
  const focusItem = useDAStore((s) => s.focusItem)

  const [pageWidth, setPageWidth] = useState<number>(0)
  // Native PDF dimensions in PDF points (from the pdf.js PDFPageProxy.view array).
  // These are ~595 × 842 pt for A4 regardless of the CSS render size and are
  // required to correctly map BOTTOMLEFT bbox coords → CSS pixel positions.
  const [pdfNativeWidth, setPdfNativeWidth] = useState<number>(0)
  const [pdfNativeHeight, setPdfNativeHeight] = useState<number>(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const onDocumentLoad = useCallback(
    ({ numPages }: { numPages: number }) => setTotalPages(numPages),
    [setTotalPages]
  )

  const onPageLoad = useCallback(
    (page: { width: number; height: number; view: number[] }) => {
      setPageWidth(page.width)
      // view = [x0, y0, x1, y1] in PDF points (e.g. [0, 0, 595.28, 841.89])
      setPdfNativeWidth(page.view[2] - page.view[0])
      setPdfNativeHeight(page.view[3] - page.view[1])
    },
    []
  )

  // Only show bboxes for items on the current page
  const visibleItems = items.filter(
    (i) => i.bounding_box && i.bounding_box.page === currentPage
  )

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Page navigation toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-100 rounded-lg text-sm text-slate-700">
        <button
          className="px-3 py-1 rounded hover:bg-slate-200 disabled:opacity-40"
          disabled={currentPage <= 1}
          onClick={() => setCurrentPage(currentPage - 1)}
        >
          ← Prev
        </button>
        <span className="font-medium">Page {currentPage}</span>
        <button
          className="px-3 py-1 rounded hover:bg-slate-200 disabled:opacity-40"
          onClick={() => setCurrentPage(currentPage + 1)}
        >
          Next →
        </button>
      </div>

      {/* PDF canvas + overlay */}
      <div ref={containerRef} className="overflow-auto flex-1 flex justify-center bg-slate-50">
        <div className="relative inline-block">
          <Document file={pdfUrl} onLoadSuccess={onDocumentLoad}>
            <Page
              pageNumber={currentPage}
              width={containerRef.current?.clientWidth ?? 700}
              onLoadSuccess={onPageLoad}
              renderAnnotationLayer
              renderTextLayer
            />
          </Document>

          {/* Bounding box highlight overlays — positioned relative to page top-left */}
          {pdfNativeWidth > 0 &&
            pdfNativeHeight > 0 &&
            visibleItems.map((item) => {
              const bb = item.bounding_box!
              // scale: maps PDF points → rendered CSS pixels.
              // pageWidth (from react-pdf callback) is in CSS px; pdfNativeWidth is
              // in PDF pt. Their ratio is the uniform scale for both axes.
              const scale = pageWidth / pdfNativeWidth

              // Docling BOTTOMLEFT origin: y=0 at bottom, increases upward.
              // CSS origin: y=0 at top, increases downward. Flip with native PDF height.
              const left = bb.x1 * scale
              const top = (pdfNativeHeight - bb.y2) * scale
              const width = (bb.x2 - bb.x1) * scale
              const height = Math.max((bb.y2 - bb.y1) * scale, 14)

              const isFocused = focusedItemId === item.item_id
              const isFlagged = item.flag_reasons.includes('HIGH_DEVIATION')
              const isReview = item.flag_reasons.length > 0 && !isFlagged

              return (
                <div
                  key={item.item_id}
                  title={item.description}
                  onClick={() => focusItem(item.item_id === focusedItemId ? null : item.item_id)}
                  className={`bbox-highlight cursor-pointer ${isFlagged ? 'flagged' : ''} ${isReview ? 'review' : ''} ${isFocused ? 'opacity-100 z-10' : 'opacity-50 z-[1]'}`}
                  style={{ left, top, width, height }}
                />
              )
            })}
        </div>
      </div>
    </div>
  )
}
