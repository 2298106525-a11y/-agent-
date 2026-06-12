import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(config => config, err => Promise.reject(err))
api.interceptors.response.use(res => res.data, err => { throw err })

export async function runFull(position, name = '学员', level = '初级') {
  return api.post('/full', { position, name, level })
}

/**
 * 上传简历PDF，返回解析后的文本
 */
export async function uploadResume(file) {
  const formData = new FormData()
  formData.append('file', file)
  const base = import.meta.env.DEV ? 'http://localhost:8000' : ''
  const res = await fetch(`${base}/api/upload-resume`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * SSE 流式调用完整流程 — 实时推送进度和 LLM 输出
 * 直连后端端口（绕过 Vite 代理，避免 SSE 缓冲）
 */
export function runFullStream(position, name = '学员', level = '初级', resumeText = null, callbacks = {}) {
  const { onProgress, onToken, onDone, onError } = callbacks
  const params = new URLSearchParams({ position, name, level })
  if (resumeText) params.set('resume_text', resumeText)
  // 开发环境直连后端，生产环境用相对路径
  const base = import.meta.env.DEV ? 'http://localhost:8000' : ''
  const url = `${base}/api/full/stream?${params}`
  const controller = new AbortController()

  ;(async () => {
    try {
      console.log('[SSE] connecting:', url)
      const res = await fetch(url, { signal: controller.signal })
      console.log('[SSE] response:', res.status, res.headers.get('content-type'))
      if (!res.ok) {
        const text = await res.text()
        console.error('[SSE] error response:', text)
        onError?.(`请求失败: ${res.status} ${text}`)
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let eventCount = 0

      while (true) {
        const { done, value } = await reader.read()
        if (done) { console.log('[SSE] stream done, events received:', eventCount); break }
        const chunk = decoder.decode(value, { stream: true })
        console.log('[SSE] chunk:', chunk.slice(0, 200))
        buffer += chunk
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ') && eventType) {
            try {
              const data = JSON.parse(line.slice(6))
              eventCount++
              console.log('[SSE] event:', eventType, data)
              if (eventType === 'progress') onProgress?.(data)
              else if (eventType === 'token') onToken?.(data)
              else if (eventType === 'done') onDone?.(data)
              else if (eventType === 'error') onError?.(data.message || '未知错误')
            } catch (e) { console.warn('[SSE] parse error:', e, line.slice(6)) }
            eventType = ''
          }
        }
      }
    } catch (err) {
      console.error('[SSE] fetch error:', err)
      if (err.name !== 'AbortError') onError?.(err.message || '请求失败')
    }
  })()

  return () => controller.abort()
}

export async function getDemo(position) {
  return api.get('/demo', { params: { position } })
}
export async function getResult(name) {
  return api.get(`/result/${encodeURIComponent(name)}`)
}
export async function getMaterials(name) {
  return api.get(`/materials/${encodeURIComponent(name)}`)
}
export async function healthCheck() {
  return api.get('/health')
}
export async function regenerate(name, stage) {
  return api.post('/regenerate', { name, stage })
}

// ============ 学生数据 API（数据库） ============

export async function listStudents() {
  return api.get('/students')
}

export async function getStudentFull(name) {
  return api.get(`/students/${encodeURIComponent(name)}/full`)
}

export async function toggleProgress(name, itemType, itemId) {
  return api.post(`/students/${encodeURIComponent(name)}/progress`, { item_type: itemType, item_id: itemId })
}

export async function saveTestScore(name, score, correct, total) {
  return api.post(`/students/${encodeURIComponent(name)}/test-score`, { score, correct, total })
}

export async function saveStudentResult(name, result, position = '', level = '初级', currentStep = 0) {
  return api.post(`/students/${encodeURIComponent(name)}/result`, { result, position, level, current_step: currentStep })
}

export async function saveStudentStep(name, currentStep) {
  return api.post(`/students/${encodeURIComponent(name)}/step`, { current_step: currentStep })
}

export async function deleteStudent(name) {
  return api.delete(`/students/${encodeURIComponent(name)}`)
}

// ============ 对话记忆 API ============

export async function getTutorHistory(name) {
  return api.get(`/tutor/history/${encodeURIComponent(name)}`)
}

export async function clearTutorHistory(name) {
  return api.delete(`/tutor/history/${encodeURIComponent(name)}`)
}

export default api