/**
 * Zustand store — client-side state for the accountant review session.
 * Server state (DA data, deviation report) lives in react-query cache.
 */
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { DeviationLineItem, ItemStatus } from '@/types'

interface ItemEdit {
    status: ItemStatus
    accountant_note: string
}

interface DAStore {
    /** The DA ID currently being reviewed */
    activeDAId: string | null
    setActiveDAId: (id: string | null) => void

    /** PDF blob URL served by the API (or local preview) */
    pdfUrl: string | null
    setPdfUrl: (url: string | null) => void

    /** Current rendered PDF page (1-indexed) */
    currentPage: number
    setCurrentPage: (page: number) => void
    totalPages: number
    setTotalPages: (n: number) => void

    /** Which item the accountant has focused (for bbox highlight sync) */
    focusedItemId: string | null
    focusItem: (id: string | null) => void

    /** Per-item edits keyed by item_id */
    edits: Record<string, ItemEdit>
    setItemStatus: (itemId: string, status: ItemStatus) => void
    setItemNote: (itemId: string, note: string) => void

    /** Initialise edits from deviation report items */
    initEdits: (items: DeviationLineItem[]) => void

    /** Reset everything for a new upload */
    reset: () => void
}

export const useDAStore = create<DAStore>()(
    devtools(
        (set) => ({
            activeDAId: null,
            setActiveDAId: (id) => set({ activeDAId: id }),

            pdfUrl: null,
            setPdfUrl: (url) => set({ pdfUrl: url }),

            currentPage: 1,
            setCurrentPage: (page) => set({ currentPage: page }),
            totalPages: 1,
            setTotalPages: (n) => set({ totalPages: n }),

            focusedItemId: null,
            focusItem: (id) => set({ focusedItemId: id }),

            edits: {},
            setItemStatus: (itemId, status) =>
                set((s) => ({
                    edits: {
                        ...s.edits,
                        [itemId]: { ...(s.edits[itemId] ?? { accountant_note: '' }), status },
                    },
                })),
            setItemNote: (itemId, note) =>
                set((s) => ({
                    edits: {
                        ...s.edits,
                        [itemId]: { ...(s.edits[itemId] ?? { status: 'OK' }), accountant_note: note },
                    },
                })),

            initEdits: (items) =>
                set({
                    edits: Object.fromEntries(
                        items.map((i) => [
                            i.item_id,
                            { status: i.status, accountant_note: i.accountant_note ?? '' },
                        ])
                    ),
                }),

            reset: () =>
                set({
                    activeDAId: null,
                    pdfUrl: null,
                    currentPage: 1,
                    totalPages: 1,
                    focusedItemId: null,
                    edits: {},
                }),
        }),
        { name: 'OpenDA-Accountant' }
    )
)
