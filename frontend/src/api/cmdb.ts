import http from './http'

export function getServers(page = 1, pageSize = 20) {
  return http.get<any>('/api/v1/cmdb/servers', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createServer(data: any) {
  return http.post<any>('/api/v1/cmdb/servers', data).then((r) => r.data)
}

export function deleteServer(id: number) {
  return http.delete(`/api/v1/cmdb/servers/${id}`).then((r) => r.data)
}

export function getServer(id: number) {
  return http.get<any>(`/api/v1/cmdb/servers/${id}`).then((r) => r.data)
}
