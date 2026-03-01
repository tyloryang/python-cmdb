import http from './http'

export function getApps(page = 1, pageSize = 20) {
  return http.get<any>('/api/v1/release/apps', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createApp(data: any) {
  return http.post<any>('/api/v1/release/apps', data).then((r) => r.data)
}

export function getReleases(page = 1, pageSize = 20) {
  return http.get<any>('/api/v1/release/releases', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createRelease(data: any) {
  return http.post<any>('/api/v1/release/releases', data).then((r) => r.data)
}

export function getRelease(id: number) {
  return http.get<any>(`/api/v1/release/releases/${id}`).then((r) => r.data)
}

export function deployRelease(id: number) {
  return http.post<any>(`/api/v1/release/releases/${id}/deploy`).then((r) => r.data)
}

export function rollbackRelease(id: number, toVersion: string, reason: string) {
  return http
    .post<any>(`/api/v1/release/releases/${id}/rollback`, null, {
      params: { to_version: toVersion, reason },
    })
    .then((r) => r.data)
}
