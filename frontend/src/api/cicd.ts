import http from './http'

export function getPipelines(page = 1, pageSize = 20) {
  return http.get<any>('/api/v1/cicd/pipelines', { params: { page, page_size: pageSize } }).then((r) => r.data)
}

export function createPipeline(data: any) {
  return http.post<any>('/api/v1/cicd/pipelines', data).then((r) => r.data)
}

export function deletePipeline(id: number) {
  return http.delete(`/api/v1/cicd/pipelines/${id}`).then((r) => r.data)
}

export function getPipeline(id: number) {
  return http.get<any>(`/api/v1/cicd/pipelines/${id}`).then((r) => r.data)
}

export function triggerPipeline(pipelineId: number) {
  return http.post<any>(`/api/v1/cicd/pipelines/${pipelineId}/trigger`).then((r) => r.data)
}

export function getBuilds(pipelineId: number, page = 1, pageSize = 20) {
  return http
    .get<any>(`/api/v1/cicd/pipelines/${pipelineId}/builds`, { params: { page, page_size: pageSize } })
    .then((r) => r.data)
}

export function getBuild(buildId: number) {
  return http.get<any>(`/api/v1/cicd/builds/${buildId}`).then((r) => r.data)
}
