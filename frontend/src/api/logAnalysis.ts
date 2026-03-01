import http from './http'

export function getWatchers(page = 1, pageSize = 20) {
  return http.get<any>('/v1/log-analysis/watchers', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createWatcher(data: any) {
  return http.post<any>('/v1/log-analysis/watchers', data).then((r) => r.data)
}

export function updateWatcher(id: number, data: any) {
  return http.patch<any>(`/v1/log-analysis/watchers/${id}`, data).then((r) => r.data)
}

export function deleteWatcher(id: number) {
  return http.delete(`/v1/log-analysis/watchers/${id}`).then((r) => r.data)
}

export function startWatcher(id: number) {
  return http.post<any>(`/v1/log-analysis/watchers/${id}/start`).then((r) => r.data)
}

export function pauseWatcher(id: number) {
  return http.post<any>(`/v1/log-analysis/watchers/${id}/pause`).then((r) => r.data)
}

export function runWatcher(id: number) {
  return http.post<any>(`/v1/log-analysis/watchers/${id}/run`).then((r) => r.data)
}

export function getTemplates(watcherId: number, page = 1, pageSize = 20, orderBy = 'hit_count') {
  return http
    .get<any>(`/v1/log-analysis/watchers/${watcherId}/templates`, {
      params: { page, page_size: pageSize, order_by: orderBy },
    })
    .then((r) => r.data)
}

export function askLogs(watcherId: number, question: string, hours = 24) {
  return http
    .post<any>(`/v1/log-analysis/watchers/${watcherId}/ask`, { question, hours })
    .then((r) => r.data)
}
