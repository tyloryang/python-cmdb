import http from './http'

export function getDashboardSummary() {
    return http.get<any>('/v1/dashboard/summary').then((r) => r.data)
}
