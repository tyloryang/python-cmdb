import http from './http'

export function getChannels(page = 1, pageSize = 20) {
  return http
    .get<any>('/api/v1/notification/channels', { params: { page, page_size: pageSize } })
    .then((r) => r.data)
}

export function createChannel(data: any) {
  return http.post<any>('/api/v1/notification/channels', data).then((r) => r.data)
}

export function deleteChannel(id: number) {
  return http.delete(`/api/v1/notification/channels/${id}`).then((r) => r.data)
}

export function testChannel(id: number) {
  return http.post<any>(`/api/v1/notification/channels/${id}/test`).then((r) => r.data)
}
