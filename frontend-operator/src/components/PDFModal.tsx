/**
 * PDFModal — lightbox overlay showing the FDA PDF for evidence review.
 * Operator can click any row in DeviationTable to open the modal,
 * which scrolls to the page containing the selected item's bounding box.
 */
import { useCallback, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import type { DeviationLineItem } from '@/types'

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface Props {
  pdfUrl: string
  items: DeviationLineItem[]
  selectedItemId: string | null
  onClose: () => void
}

export function PDFModal({ pdfUrl, items, selectedItemId, onClose }: Props) {
  const selectedItem = items.find((i) => i.item_id === selectedItemId)
  const [currentPage, setCurrentPage] = useState<number>(
    selectedItem?.bounding_box?.page ?? 1
  )
  const [totalPages, setTotalPages] = useState(1)
  const [pageWidth, setPageWidth] = useState(0)
  const [pageHeight, setPageHeight] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)

  const onDocLoad = useCallback(({ numPages }: { numPages: number }) => setTotalPages(numPages), [])
  const onPageLoad = useCallback(
    (page: { width: number; height: number }) => {
      setPageWidth(page.width)
      setPageHeight(page.height)
    },
    []
  )

  // Items visible on the current page
  const pageItems = items.filter((i) => i.bounding_box?.page === currentPage)

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-slate-800 text-sm">FDA Document</span>
            {selectedItem && (
              <span className="text-xs text-slate-500 italic">
                — {selectedItem.description}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {/* Page nav */}
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <button
                className="px-2 py-0.5 rounded hover:bg-slate-100 disabled:opacity-40"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => p - 1)}
              >
                ←
              </button>
              <span>{currentPage} / {totalPages}</span>
              <button
                className="px-2 py-0.5 rounded hover:bg-slate-100 disabled:opacity-40"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
              >
                →
              </button>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700 text-xl leading-none"
            >
              ✕
            </button>
          </div>
        </div>

        {/* PDF canvas */}
        <div ref={containerRef} className="relative overflow-auto flex-1 flex justify-center bg-slate-100 p-4">
          <div className="relative inline-block">
            <Document file={pdfUrl} onLoadSuccess={onDocLoad}>
              <Page
                pageNumber={currentPage}
                width={Math.min(containerRef.current?.clientWidth ?? 700, 750)}
                onLoadSuccess={onPageLoad}
                renderAnnotationLayer
                renderTextLayer
              />
            </Document>

            {/* Bounding box overlays */}
            {pageWidth > 0 &&
              pageItems.map((item) => {
                const bb = item.bounding_box!
                const displayW = Math.min(containerRef.current?.clientWidth ?? 700, 750)
                const scaleX = displayW / pageWidth
                const scaleY = (displayW * (pageHeight / pageWidth)) / pageHeight

                const isSelected = item.item_id === selectedItemId

                return (
                  <div
                    key={item.item_id}
                    className="absolute border-2 pointer-events-none transition-all"
                    style={{
                      left: bb.x1 * scaleX,
                      top: bb.y1 * scaleY,
                      width: (bb.x2 - bb.x1) * scaleX,
                      height: (bb.y2 - bb.y1) * scaleY,
                      borderColor: isSelected ? '#ef4444' : '#3b82f6',
                      backgroundColor: isSelected ? 'rgba(239,68,68,0.1)' : 'rgba(59,130,246,0.1)',
                      zIndex: isSelected ? 10 : 1,
                    }}
                  />
                )
              })}
          </div>
        </div>
      </div>
    </div>
  )
}
