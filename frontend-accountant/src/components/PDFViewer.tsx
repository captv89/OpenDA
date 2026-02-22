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
  const [pageHeight, setPageHeight] = useState<number>(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const onDocumentLoad = useCallback(
    ({ numPages }: { numPages: number }) => setTotalPages(numPages),
    [setTotalPages]
  )

  const onPageLoad = useCallback(
    (page: { width: number; height: number }) => {
      setPageWidth(page.width)
      setPageHeight(page.height)
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
      <div ref={containerRef} className="pdf-overlay-container overflow-auto flex-1">
        <Document file={pdfUrl} onLoadSuccess={onDocumentLoad} className="flex justify-center">
          <Page
            pageNumber={currentPage}
            width={containerRef.current?.clientWidth ?? 700}
            onLoadSuccess={onPageLoad}
            renderAnnotationLayer
            renderTextLayer
          />
        </Document>

        {/* Bounding box highlight overlays */}
        {pageWidth > 0 &&
          pageHeight > 0 &&
          visibleItems.map((item) => {
            const bb = item.bounding_box!
            const containerW = containerRef.current?.clientWidth ?? pageWidth

            // Docling coords are in pt-space matching PDF page dimensions
            // Scale from PDF pt dimensions to rendered container pixels
            const scaleX = containerW / pageWidth
            const scaleY = (containerW * (pageHeight / pageWidth)) / pageHeight

            const left = bb.x1 * scaleX
            const top = bb.y1 * scaleY
            const width = (bb.x2 - bb.x1) * scaleX
            const height = (bb.y2 - bb.y1) * scaleY

            const isFocused = focusedItemId === item.item_id
            const isFlagged = item.flag_reasons.includes('HIGH_DEVIATION')
            const isReview = item.flag_reasons.length > 0 && !isFlagged

            return (
              <div
                key={item.item_id}
                title={item.description}
                className={`bbox-highlight ${isFlagged ? 'flagged' : ''} ${isReview ? 'review' : ''}`}
                style={{
                  left,
                  top,
                  width,
                  height,
                  opacity: isFocused ? 1 : 0.5,
                  zIndex: isFocused ? 10 : 1,
                  cursor: 'pointer',
                }}
                onClick={() => {
                  focusItem(item.item_id === focusedItemId ? null : item.item_id)
                }}
              />
            )
          })}
      </div>
    </div>
  )
}
