import http from './http'

export function getAlertRules(page = 1, pageSize = 20) {
  return http.get<any>('/v1/monitor/alert-rules', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createAlertRule(data: any) {
  return http.post<any>('/v1/monitor/alert-rules', data).then((r) => r.data)
}

export function updateAlertRule(id: number, data: any) {
  return http.put<any>(`/v1/monitor/alert-rules/${id}`, data).then((r) => r.data)
}

export function deleteAlertRule(id: number) {
  return http.delete(`/v1/monitor/alert-rules/${id}`).then((r) => r.data)
}

export function getAlertEvents(status?: string, page = 1, pageSize = 20) {
  return http
    .get<any>('/v1/monitor/alert-events', { params: { status, page, page_size: pageSize } })
    .then((r) => r.data)
}
