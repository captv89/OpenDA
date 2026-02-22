import axios from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { DAStatusResponse, DeviationReport, AuditLogEntry } from '@/types'

const BASE = import.meta.env.VITE_API_BASE ?? ''
const USER_ID = import.meta.env.VITE_OPERATOR_USER_ID ?? 'operator-001'

export const api = axios.create({
    baseURL: `${BASE}/api/v1`,
    headers: { 'X-User-Id': USER_ID },
})

export const keys = {
    status: (daId: string) => ['da', daId, 'status'] as const,
    deviation: (daId: string) => ['da', daId, 'deviation'] as const,
    auditLog: (daId: string) => ['da', daId, 'audit-log'] as const,
}

export function useDAStatus(daId: string | null) {
    return useQuery<DAStatusResponse>({
        queryKey: keys.status(daId ?? ''),
        queryFn: () => api.get<DAStatusResponse>(`/da/${daId}/status`).then(r => r.data),
        enabled: !!daId,
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

export function useApproveDA(daId: string) {
    const qc = useQueryClient()
    return useMutation<unknown, Error, { justification: string }>({
        mutationFn: ({ justification }) => {
            const fd = new FormData()
            fd.append('operator_remarks', justification)
            return api.post(`/da/${daId}/approve`, fd).then(r => r.data)
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: keys.status(daId) })
            qc.invalidateQueries({ queryKey: keys.auditLog(daId) })
        },
    })
}

export function useRejectDA(daId: string) {
    const qc = useQueryClient()
    return useMutation<unknown, Error, { reason: string }>({
        mutationFn: ({ reason }) => {
            const fd = new FormData()
            fd.append('reason', reason)
            return api.post(`/da/${daId}/reject`, fd).then(r => r.data)
        },
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: keys.status(daId) })
            qc.invalidateQueries({ queryKey: keys.auditLog(daId) })
        },
    })
}
