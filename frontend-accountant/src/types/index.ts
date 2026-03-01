/** Shared TypeScript types mirroring the Python schemas. */

export type DAStatus =
    | 'UPLOADING'
    | 'AI_PROCESSING'
    | 'PENDING_ACCOUNTANT_REVIEW'
    | 'PENDING_OPERATOR_APPROVAL'
    | 'APPROVED'
    | 'REJECTED'
    | 'PUSHED_TO_ERP'

export type FlagReason =
    | 'LOW_CONFIDENCE'
    | 'MISSING_PDA_LINE'
    | 'HIGH_DEVIATION'
    | 'MISSING_FROM_FDA'

export type ItemStatus = 'OK' | 'REQUIRES_REVIEW' | 'CONFIRMED' | 'OVERRIDDEN'

export type Category =
    | 'PILOTAGE'
    | 'TOWAGE'
    | 'PORT_DUES'
    | 'AGENCY_FEE'
    | 'LAUNCH_HIRE'
    | 'WASTE_DISPOSAL'
    | 'OTHER'

export interface BoundingBox {
    page: number
    x1: number
    y1: number
    x2: number
    y2: number
}

export interface DeviationLineItem {
    item_id: string
    category: Category
    description: string
    pda_value: number | null
    fda_value: number | null
    abs_variance: number | null
    pct_variance: number | null
    status: ItemStatus
    flag_reasons: FlagReason[]
    confidence_score: number | null
    bounding_box: BoundingBox | null
    accountant_note: string
}

export interface DeviationReport {
    da_id: string
    port_call_id: string
    total_estimated: number
    total_actual: number
    items: DeviationLineItem[]
}

export interface DAStatusResponse {
    da_id: string
    port_call_id: string
    vessel_name: string | null
    status: DAStatus
    flagged_items_count: number
    total_estimated: number | null
    total_actual: number | null
    extraction_model: string | null
    llm_provider: string | null
    created_at: string
    updated_at: string
}

export interface AuditLogEntry {
    id: string
    actor: string
    previous_status: string | null
    new_status: string
    note: string | null
    llm_provider: string | null
    created_at: string
}

export interface SubmitPayload {
    items: Array<{
        item_id: string
        status: ItemStatus
        accountant_note: string
    }>
}
