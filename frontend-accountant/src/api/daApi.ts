/**
 * Axios API client — all calls proxied via Vite dev server to :8000.
 * Production: set VITE_API_BASE to the deployed backend URL.
 */
import axios from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
    DAStatusResponse,
    DeviationReport,
    AuditLogEntry,
    SubmitPayload,
} from '@/types'

const BASE = import.meta.env.VITE_API_BASE ?? ''
const USER_ID = import.meta.env.VITE_ACCOUNTANT_USER_ID ?? 'accountant-001'

export const api = axios.create({
    baseURL: `${BASE}/api/v1`,
    headers: { 'X-User-Id': USER_ID },
})

// ── Query keys ──────────────────────────────────────────────────────────────

export const keys = {
    status: (daId: string) => ['da', daId, 'status'] as const,
    deviation: (daId: string) => ['da', daId, 'deviation'] as const,
    auditLog: (daId: string) => ['da', daId, 'audit-log'] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useDAStatus(daId: string | null) {
    return useQuery<DAStatusResponse>({
        queryKey: keys.status(daId ?? ''),
        queryFn: () => api.get<DAStatusResponse>(`/da/${daId}/status`).then(r => r.data),
        enabled: !!daId,
        refetchInterval: (query) => {
            const status = query.state.data?.status
            // Poll until processing is complete
            if (status === 'UPLOADING' || status === 'AI_PROCESSING') return 3_000
            return false
        },
    })
}

export function useDeviationReport(daId: string | null) {
    return useQuery<DeviationReport>({
        queryKey: keys.deviation(daId ?? ''),
        queryFn: () => api.get<DeviationReport>(`/da/${daId}/deviation-report`).then(r => r.data),
        enabled: !!daId,
    })
}

export function useAuditLog(daId: string | null) {
    return useQuery<AuditLogEntry[]>({
        queryKey: keys.auditLog(daId ?? ''),
        queryFn: () => api.get<AuditLogEntry[]>(`/da/${daId}/audit-log`).then(r => r.data),
        enabled: !!daId,
    })
}

// ── Mutations ─────────────────────────────────────────────────────────────────

export function useUploadDA() {
    const qc = useQueryClient()
    return useMutation<{ da_id: string; job_id: string; status: string }, Error, FormData>({
        mutationFn: (form) =>
            api.post('/da/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data),
        onSuccess: (data) => {
            // Prefetch status immediately
            qc.invalidateQueries({ queryKey: keys.status(data.da_id) })
        },
    })
}

export function useSubmitToOperator(daId: string) {
    const qc = useQueryClient()
    return useMutation<unknown, Error, SubmitPayload>({
        mutationFn: (payload) =>
            api
                .put(`/da/${daId}/submit-to-operator`, payload, {
                    headers: { 'Content-Type': 'application/json' },
                })
                .then(r => r.data),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: keys.status(daId) })
            qc.invalidateQueries({ queryKey: keys.auditLog(daId) })
        },
    })
}
