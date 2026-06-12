import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api, { getTutorHistory, clearTutorHistory } from '../api/client'
import { useStore } from '../store'
import MarkdownViewer from '../components/MarkdownViewer'

// sessionStorage 作为快速缓存（DB 为准）
const storageKey = name => `skill_trainer_tutor_${name}`
const loadMsgs = name => { try { const r = sessionStorage.getItem(storageKey(name)); return r ? JSON.parse(r) : [] } catch { return [] } }
const saveMsgs = (name, msgs) => { try { sessionStorage.setItem(storageKey(name), JSON.stringify(msgs)) } catch {} }

export default function Tutor() {
  const { name: urlName } = useParams()
  const nav = useNavigate()
  const { studentName, setStudentName, result, setResult, completedItems } = useStore()
  const name = urlName || studentName || ''
  const [student, setStudent] = useState(null)
  const [materials, setMaterials] = useState(null)
  const [messages, setMessages] = useState(() => loadMsgs(name))  // 先用 sessionStorage 快速显示
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [regenerating, setRegenerating] = useState(null) // 当前正在重新生成的阶段
  const [initLoading, setInitLoading] = useState(true)
  const [tab, setTab] = useState('chat')
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { saveMsgs(name, messages) }, [name, messages])

  // 保存学生名到 store（如果从 URL 进入）
  useEffect(() => {
    if (urlName && urlName !== studentName) {
      setStudentName(urlName)
    }
  }, [urlName, studentName, setStudentName])

  useEffect(() => {
    if (!name) {
      setInitLoading(false)
      return
    }

    (async () => {
      try {
        const data = await api.get(`/check/${encodeURIComponent(name)}`)
        setStudent(data)

        // 从数据库加载对话历史（优先级高于 sessionStorage）
        try {
          const histRes = await getTutorHistory(name)
          if (histRes?.messages?.length) {
            setMessages(histRes.messages)
            saveMsgs(name, histRes.messages)  // 同步到 sessionStorage
          } else if (!messages.length) {
            setMessages([{ role: 'assistant', content: `👋 欢迎回来，${name}！\n\n我是你的AI学习助手。\n\n📋 **查看学习计划** · 🏋️ **出练习题** · 📝 **进行测验** · ❓ **答疑解惑**\n\n请在下方输入问题，或点击快捷操作。` }])
          }
        } catch {
          // DB 加载失败，保留 sessionStorage 中的数据
          if (!messages.length) {
            setMessages([{ role: 'assistant', content: `👋 欢迎回来，${name}！\n\n我是你的AI学习助手。\n\n📋 **查看学习计划** · 🏋️ **出练习题** · 📝 **进行测验** · ❓ **答疑解惑**\n\n请在下方输入问题，或点击快捷操作。` }])
          }
        }
      } catch { if (!messages.length) setMessages([{ role: 'assistant', content: '加载学生数据失败，请返回重试。' }]) }
      finally { setInitLoading(false) }

      try { const d = await api.get(`/materials/${encodeURIComponent(name)}`); setMaterials(d.materials) } catch {}
    })()
  }, [name])

  // 没有名字 → 回首页
  if (!name && !initLoading) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-500 mb-4">未找到学生信息</p>
        <Link to="/" className="btn-primary">返回首页</Link>
      </div>
    )
  }

  const send = useCallback(async text => {
    if (!text.trim() || loading) return
    const msg = text.trim(); setInput('')
    setMessages(p => [...p, { role: 'user', content: msg }]); setLoading(true)

    // 流式接收 AI 回复（后端从 DB 读取历史，不需要传 history）
    let reply = ''
    try {
      const base = import.meta.env.DEV ? 'http://localhost:8000' : ''
      const res = await fetch(`${base}/api/tutor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, message: msg }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      // 先插入一条空的 assistant 消息，后续不断更新
      setMessages(p => [...p, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.text) {
              reply += data.text
              const r = reply // 捕获当前值
              setMessages(p => { const next = [...p]; next[next.length - 1] = { role: 'assistant', content: r }; return next })
            }
            if (data.error) throw new Error(data.error)
          } catch (e) { if (e.message && !e.message.includes('JSON')) throw e }
        }
      }
    } catch (err) {
      console.error('[Tutor] error:', err)
      if (!reply) {
        setMessages(p => { const next = [...p]; next[next.length - 1] = { role: 'assistant', content: '请求失败：' + (err.message || '请重试') }; return next })
      }
    } finally { setLoading(false) }
  }, [name, loading, messages])

  const handleSend = () => send(input)
  const handleKeyDown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }
  const clearChat = async () => {
    sessionStorage.removeItem(storageKey(name))
    setMessages([{ role: 'assistant', content: '对话已清空。' }])
    try { await clearTutorHistory(name) } catch (e) { console.warn('[Tutor] clear DB history failed:', e) }
  }

  // 重新生成弹窗状态
  const [regenDialog, setRegenDialog] = useState(null) // { stage, label }
  const [regenPrompt, setRegenPrompt] = useState('')

  // 执行重新生成
  const doRegenerate = async () => {
    const { stage, label } = regenDialog
    const prompt = regenPrompt.trim()
    setRegenDialog(null)
    setRegenPrompt('')
    if (regenerating) return
    setRegenerating(stage)

    const userMsg = prompt ? `重新生成${label}，需求：${prompt}` : `重新生成${label}`
    setMessages(p => [...p, { role: 'user', content: userMsg }, { role: 'assistant', content: `⏳ 正在根据你的需求重新生成${label}，请稍候...` }])

    try {
      const base = import.meta.env.DEV ? 'http://localhost:8000' : ''
      const res = await fetch(`${base}/api/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name, stage,
          extra_prompt: prompt,
          completed_items: completedItems,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '请求失败' }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
      setMessages(p => {
        const next = [...p]
        next[next.length - 1] = { role: 'assistant', content: `✅ ${label}已根据你的需求重新生成！点击顶部标签查看。` }
        return next
      })
    } catch (err) {
      setMessages(p => {
        const next = [...p]
        next[next.length - 1] = { role: 'assistant', content: `❌ 重新生成失败：${err.message}` }
        return next
      })
    } finally { setRegenerating(null) }
  }

  const quicks = [
    { label: '📋 学习计划', msg: '帮我查看当前的学习计划' },
    { label: '🏋️ 练习题', msg: '给我出几道练习题' },
    { label: '📝 小测验', msg: '我想进行一次小测验' },
    { label: '📊 能力报告', msg: '帮我查看能力评估报告' },
  ]

  const regenActions = [
    { stage: 'learning', label: '📚 学习内容', desc: '重新生成所有学习模块' },
    { stage: 'training', label: '🏋️ 训练计划', desc: '重新生成训练任务' },
    { stage: 'test', label: '📝 考核试卷', desc: '重新生成测试试卷' },
  ]

  if (initLoading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <svg className="animate-spin h-12 w-12 text-primary-600 mx-auto mb-4" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <p className="text-gray-600">加载中...</p>
      </div>
    </div>
  )

  const matSections = [
    { key: 'framework', icon: '📋', title: '岗位分析' },
    { key: 'learning', icon: '📚', title: '学习内容' },
    { key: 'training', icon: '🏋️', title: '训练任务' },
    { key: 'test', icon: '📝', title: '测试试卷' },
    { key: 'assessment', icon: '📊', title: '评估报告' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="card mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">🤖 伴学模式</h1>
            <p className="text-gray-600">学员：{name}{student?.checkpoint?.position && ` · 目标：${student.checkpoint.position}`}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={clearChat} className="btn-secondary text-sm">清空对话</button>
            <Link to="/" className="btn-secondary text-sm">🔄 切换学生</Link>
          </div>
        </div>

        {student?.checkpoint && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-800">📊 学习进度：已完成 {Math.min(student.checkpoint.done + 1, 5)}/5 阶段</p>
            <div className="w-full bg-blue-200 rounded-full h-2 mt-2">
              <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{ width: `${(Math.min(student.checkpoint.done + 1, 5) / 5) * 100}%` }} />
            </div>
          </div>
        )}

        <div className="mt-4 flex gap-2 border-b border-gray-200">
          {[{ id: 'chat', label: '💬 AI对话' }, { id: 'materials', label: '📚 学习材料' }].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${tab === t.id ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat */}
      {tab === 'chat' && (
        <>
          <div className="card mb-6">
            <p className="text-sm font-medium text-gray-700 mb-3">快捷操作：</p>
            <div className="flex flex-wrap gap-2">
              {quicks.map((q, i) => <button key={i} onClick={() => send(q.msg)} disabled={loading} className="btn-secondary text-sm disabled:opacity-50">{q.label}</button>)}
            </div>
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-sm font-medium text-gray-700 mb-2">🔄 根据需求重新生成：</p>
              <div className="flex flex-wrap gap-2">
                {regenActions.map((a, i) => (
                  <button key={i} onClick={() => { setRegenDialog(a); setRegenPrompt('') }} disabled={!!regenerating}
                    className={`text-sm px-3 py-1.5 rounded-lg border transition-colors ${regenerating === a.stage ? 'border-primary-300 bg-primary-50 text-primary-600 animate-pulse' : 'border-gray-200 bg-white text-gray-600 hover:border-primary-300 hover:bg-primary-50'} disabled:opacity-50`}>
                    {regenerating === a.stage ? '⏳ 生成中...' : a.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="card mb-6">
            <div className="space-y-4 max-h-[55vh] overflow-y-auto p-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] p-3 rounded-lg ${m.role === 'user' ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 p-3 rounded-lg flex gap-1">
                    {[0, 0.1, 0.2].map((d, i) => <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: `${d}s` }} />)}
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          </div>

          <div className="card">
            <div className="flex gap-4">
              <textarea ref={el => { if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px' } }}
                className="input flex-1 resize-none min-h-[44px] max-h-[120px]"
                placeholder="输入问题... (Shift+Enter 换行)"
                value={input} rows={1}
                onChange={e => { setInput(e.target.value); e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px' }}
                onKeyDown={handleKeyDown} disabled={loading} />
              <button onClick={handleSend} className="btn-primary px-6 self-end" disabled={loading || !input.trim()}>发送</button>
            </div>
          </div>
        </>
      )}

      {/* Materials */}
      {tab === 'materials' && (
        <div className="space-y-6">
          {!materials || !Object.keys(materials).length ? (
            <div className="card text-center py-12"><p className="text-gray-500">暂无学习材料</p><p className="text-sm text-gray-400 mt-2">请先完成学习计划生成</p></div>
          ) : matSections.filter(s => materials[s.key]).map(s => (
            <div key={s.key} className="card">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">{s.icon} {s.title}</h2>
              <div className="max-h-[40vh] overflow-y-auto"><MarkdownViewer content={materials[s.key].content} /></div>
            </div>
          ))}
        </div>
      )}

      {/* 重新生成需求弹窗 */}
      {regenDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setRegenDialog(null)}>
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-6" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-gray-900 mb-2">🔄 重新生成{regenDialog.label}</h3>
            <p className="text-sm text-gray-500 mb-4">描述你的需求，AI 会根据你的要求定制内容。也可以留空直接重新生成。</p>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">你的需求（可选）</label>
              <textarea className="input min-h-[100px] resize-y" rows={3}
                placeholder={"例如：\n• Java基础已经学过了，跳过\n• 加深Spring Boot和MyBatis的训练\n• 考核难度降低一些\n• 多出一些编程实战题"}
                value={regenPrompt} onChange={e => setRegenPrompt(e.target.value)} />
            </div>

            {/* 快捷标签 */}
            <div className="flex flex-wrap gap-2 mb-4">
              {['跳过已学过的', '加深难度', '降低难度', '多出编程题', '加强薄弱环节'].map(tag => (
                <button key={tag} onClick={() => setRegenPrompt(p => p ? `${p}，${tag}` : tag)}
                  className="text-xs px-3 py-1 rounded-full border border-gray-200 text-gray-600 hover:border-primary-300 hover:bg-primary-50 transition-colors">
                  {tag}
                </button>
              ))}
            </div>

            <div className="flex gap-3 justify-end">
              <button onClick={() => setRegenDialog(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">取消</button>
              <button onClick={doRegenerate} className="px-6 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors">
                开始生成
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="h-20 md:h-0" />
    </div>
  )
}