import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { runFullStream, getDemo, getResult, uploadResume } from '../api/client'
import api from '../api/client'
import { useStore } from '../store'
import LoadingButton from '../components/LoadingButton'

const STAGE_LABELS = [
  '📋 岗位需求分析', '📚 学习内容生成', '🏋️ 训练任务生成',
  '📝 测试考核生成', '📊 能力评估',
]

/** 尝试从 LLM 输出中提取 JSON 并格式化为可读内容 */
function formatStageOutput(stageIdx, raw, hasResume = false) {
  // 提取 JSON
  let json = null
  try {
    const match = raw.match(/\{[\s\S]*\}/)
    if (match) json = JSON.parse(match[0])
  } catch { /* JSON 不完整，返回原始文本 */ }
  if (!json) return null

  const lines = []
  try {
    // 根据是否有简历调整阶段索引
    // 无简历: 0=需求分析, 1=学习, 2=训练, 3=考核, 4=评估
    // 有简历: 0=需求分析, 1=简历评估, 2=学习, 3=训练, 4=考核, 5=评估
    const idx = stageIdx

    if (idx === 0) { // 岗位需求分析
        lines.push(`## ${json.position_name || '目标岗位'}`)
        if (json.position_description) lines.push(`> ${json.position_description}\n`)
        if (json.summary) lines.push(`**概述：** ${json.summary}\n`)
        for (const cat of json.skill_categories || []) {
          const skills = (json.skill_points || []).filter(s => s.category === cat)
          lines.push(`### 📂 ${cat}`)
          for (const s of skills) {
            lines.push(`- **${s.name}**（${s.required_level || ''}）${s.description ? '— ' + s.description : ''}`)
          }
          lines.push('')
        }
    } else if (hasResume && idx === 1) { // 简历评估
        lines.push(`## 📄 简历评估结果`)
        if (json.education) lines.push(`**学历：** ${json.education}`)
        if (json.experience_years) lines.push(`**工作年限：** ${json.experience_years}年`)
        if (json.skills_found?.length) lines.push(`\n### 发现的技能\n${json.skills_found.join('、')}`)
        if (json.projects?.length) {
          lines.push(`\n### 项目经历`)
          json.projects.forEach(p => lines.push(`- **${p.name}**：${p.description}`))
        }
        if (json.strengths_from_resume?.length) lines.push(`\n### 简历优势\n${json.strengths_from_resume.join('、')}`)
        if (json.overall_score) lines.push(`\n**初始评分：** ${json.overall_score}分`)
    } else if ((!hasResume && idx === 1) || (hasResume && idx === 2)) { // 学习内容
        const items = json.items || (Array.isArray(json) ? json : [json])
        lines.push(`## 📚 学习内容\n`)
        for (const item of items) {
          const spName = item.skill_point?.name || item.skill_point_id || ''
          lines.push(`### ${spName}`)
          if (item.summary) lines.push(`> ${item.summary}\n`)
          for (const m of item.modules || item.learning_modules || []) {
            lines.push(`**${m.title}**（${m.estimated_minutes || 30}分钟）`)
            if (m.content) {
              const preview = m.content.replace(/[#*_`]/g, '').slice(0, 200)
              lines.push(`  ${preview}...\n`)
            }
          }
        }
    } else if ((!hasResume && idx === 2) || (hasResume && idx === 3)) { // 训练任务
        lines.push(`## 🏋️ ${json.title || '训练计划'}`)
        if (json.description) lines.push(`> ${json.description}\n`)
        for (const t of json.tasks || []) {
          lines.push(`### ${t.title}`)
          lines.push(`- **类型：** ${t.type || ''} ｜ **难度：** ${t.difficulty || ''} ｜ **时长：** ${t.estimated_minutes || 30}分钟`)
          if (t.description) lines.push(`- ${t.description}`)
          if (t.requirements?.length) lines.push(`- **要求：** ${t.requirements.join('；')}`)
          lines.push('')
        }
    } else if ((!hasResume && idx === 3) || (hasResume && idx === 4)) { // 测试考核
        lines.push(`## 📝 ${json.title || '测试试卷'}`)
        if (json.description) lines.push(`> ${json.description}\n`)
        lines.push(`**总分：** ${json.total_score || '?'}分 ｜ **及格分：** ${json.passing_score || 60}分 ｜ **时限：** ${json.time_limit_minutes || 60}分钟\n`)
        for (const q of json.questions || []) {
          lines.push(`**${q.question_type || ''}** ${q.question_text}`)
          if (q.options?.length) {
            for (const o of q.options) lines.push(`  ${o}`)
          }
          lines.push(`  ✅ 答案：${q.correct_answer}\n`)
        }
    } else if ((!hasResume && idx === 4) || (hasResume && idx === 5)) { // 能力评估
        lines.push(`## 📊 能力评估报告`)
        lines.push(`**综合评分：** ${json.overall_score || '?'}分 ｜ **等级：** ${json.overall_level || '?'}\n`)
        if (json.overall_strengths?.length) {
          lines.push(`### ✅ 优势`)
          json.overall_strengths.forEach(s => lines.push(`- ${s}`))
          lines.push('')
        }
        if (json.overall_weaknesses?.length) {
          lines.push(`### 📈 待提升`)
          json.overall_weaknesses.forEach(w => lines.push(`- ${w}`))
          lines.push('')
        }
        for (const sa of json.skill_assessments || []) {
          lines.push(`**${sa.skill_name}**：${sa.score}分（${sa.current_level || ''}）`)
        }
        if (json.conclusion) lines.push(`\n> ${json.conclusion}`)
    }
  } catch { /* 格式化失败 */ }
  return lines.length ? lines.join('\n') : null
}

export default function Home() {
  const nav = useNavigate()
  const { result, setResult, setCurrentStep, studentName, setStudentName, setCompletedItems, switchStudent } = useStore()
  const [name, setName] = useState(studentName || '')
  const [showSetup, setShowSetup] = useState(false)
  const [form, setForm] = useState({ position: '', level: '初级' })
  const [resumeFile, setResumeFile] = useState(null)
  const [resumeText, setResumeText] = useState(null)
  const [resumeInfo, setResumeInfo] = useState(null) // { name, pages, chars }
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState(null)

  // 流式状态
  const [streaming, setStreaming] = useState(false)
  const [stageIdx, setStageIdx] = useState(-1)
  const [stageLabel, setStageLabel] = useState('')
  // 每个阶段的消息 { role: 'system'|'assistant', label, content, done }
  const [messages, setMessages] = useState([])
  const tokenBuf = useRef('')
  const currentStage = useRef(-1)
  const scrollRef = useRef(null)
  const abortRef = useRef(null)
  const flushTimer = useRef(null)

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  const handleCheck = async () => {
    if (!name.trim()) { setError('请输入姓名'); return }
    setChecking(true); setError(null)
    try {
      // 从数据库加载该学生的全部数据
      await switchStudent(name)

      // 检查是否有完整的 result 数据
      if (result?.framework) {
        console.log('[Home] 数据库有缓存，跳转伴学')
        nav('/tutor')
        return
      }

      // 数据库没有 result → 检查后端文件系统
      const data = await api.get(`/check/${encodeURIComponent(name)}`)
      setStudentName(name)
      if (data.exists) {
        setLoading(true)
        try {
          const cached = await getResult(name)
          if (cached && cached.status !== 'not_found' && cached.framework) {
            setResult(cached)
            setCurrentStep(1)
            nav('/tutor')
            return
          }
        } catch {}
        const checkpoint = data.checkpoint
        const pos = checkpoint?.position || 'Java后端开发工程师'
        const lvl = checkpoint?.level || '初级'
        await startStream(pos, name, lvl)
        return
      } else {
        setShowSetup(true)
      }
    } catch { setError('检查失败，请重试') }
    finally { setChecking(false); setLoading(false) }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.position.trim()) { setError('请输入目标岗位'); return }
    setError(null)
    await startStream(form.position, name, form.level)
  }

  /** 启动 SSE 流式流程 */
  function startStream(position, studentName, level) {
    return new Promise(resolve => {
      // 如果没有上传简历，清空 resumeText 避免显示 6 阶段
      if (!resumeFile) { setResumeText(null); setResumeInfo(null) }
      setStreaming(true); setLoading(true); setError(null)
      setStageIdx(-1); setStageLabel('准备中...')
      setMessages([{ role: 'system', content: '🚀 正在准备生成学习计划...' }])
      tokenBuf.current = ''
      currentStage.current = -1
      const labels = STAGE_LABELS

      /** 将当前阶段的 token 缓冲刷到 messages */
      const flushTokens = () => {
        if (currentStage.current < 0 || !tokenBuf.current) return
        const idx = currentStage.current
        const mappedIdx = Math.min(mapStage(idx), STAGE_LABELS.length - 1)
        const label = labels[mappedIdx] || `阶段 ${mappedIdx + 1}`
        setMessages(prev => {
          const next = [...prev]
          // 找到当前阶段的消息并更新
          const existIdx = next.findIndex(m => m.stageIdx === idx)
          if (existIdx >= 0) {
            next[existIdx] = { ...next[existIdx], content: tokenBuf.current }
          } else {
            next.push({ role: 'assistant', label, content: tokenBuf.current, stageIdx: idx })
          }
          return next
        })
      }

      /** 阶段完成时：格式化 JSON 为可读内容 */
      const finalizeStage = (stageIdx, rawText) => {
        const formatted = formatStageOutput(stageIdx, rawText, !!resumeText)
        return formatted || rawText  // 格式化失败则保留原始文本
      }

      // 有简历时后端6阶段(0=需求,1=简历,2=学习,3=训练,4=考核,5=评估)
      // 进度条始终5格：简历评估(阶段1)不单独显示
      const hasResume = !!resumeText
      const mapStage = (s) => {
        if (!hasResume) return Math.min(s, 4)  // 无简历: 0-4 → 0-4
        if (s <= 0) return 0                    // 需求分析 → 0
        if (s === 1) return 0                   // 简历评估 → 合并到0
        return Math.min(s - 1, 4)               // 2→1, 3→2, 4→3, 5→4
      }

      abortRef.current = runFullStream(position, studentName, level, resumeText, {
        onProgress(data) {
          // 上一阶段完成 → 格式化并标记
          flushTokens()
          const prevIdx = currentStage.current
          const prevRaw = tokenBuf.current
          setMessages(prev => prev.map(m =>
            m.stageIdx === prevIdx
              ? { ...m, done: true, content: finalizeStage(prevIdx, prevRaw || m.content), formatted: true }
              : m
          ))

          const idx = data.stage
          const mappedIdx = Math.min(mapStage(idx), STAGE_LABELS.length - 1)
          currentStage.current = idx
          tokenBuf.current = ''
          setStageIdx(mappedIdx)
          setStageLabel(data.label || labels[mappedIdx] || `阶段 ${mappedIdx + 1}`)

          // 插入新阶段的系统消息
          const label = data.label || labels[mappedIdx] || `阶段 ${mappedIdx + 1}`
          setMessages(prev => [...prev, { role: 'system', content: `⏳ ${label} 生成中...` }])
        },
        onToken(data) {
          tokenBuf.current += data.text
          // 节流：每 80ms 刷新一次
          if (!flushTimer.current) {
            flushTimer.current = setTimeout(() => {
              flushTokens()
              flushTimer.current = null
            }, 80)
          }
        },
        onDone(data) {
          flushTokens()
          // 最后阶段完成 → 格式化
          const lastIdx = currentStage.current
          const lastRaw = tokenBuf.current
          setStageIdx(4) // 进度条全部亮起
          setMessages(prev => {
            const next = prev.map(m =>
              m.stageIdx === lastIdx
                ? { ...m, done: true, content: finalizeStage(lastIdx, lastRaw || m.content), formatted: true }
                : m
            )
            return [...next, { role: 'system', content: '✅ 全部生成完成！正在跳转...' }]
          })

          if (!data || !data.framework) {
            setError('生成数据不完整，请重试')
            setStreaming(false); setLoading(false)
            resolve()
            return
          }
          setTimeout(() => {
            setResult(data); setCurrentStep(1); setStudentName(studentName)
            setStreaming(false); setLoading(false)
            nav('/profile')
            resolve()
          }, 800)
        },
        onError(msg) {
          setMessages(prev => [...prev, { role: 'system', content: `❌ 生成失败：${msg}` }])
          setError('生成失败：' + msg)
          setStreaming(false); setLoading(false)
          resolve()
        },
      })
    })
  }

  const handleDemo = async () => {
    setLoading(true); setError(null)
    try {
      const data = await getDemo('Java后端开发工程师')
      if (!data || !data.framework) { setError('返回数据格式错误'); return }
      setResult(data); setCurrentStep(1); setStudentName('演示用户'); nav('/profile')
    } catch (err) {
      console.error('[handleDemo]', err)
      setError('获取演示数据失败: ' + (err.message || '请检查后端服务'))
    } finally { setLoading(false) }
  }

  const handleCancel = () => {
    abortRef.current?.()
    setStreaming(false); setLoading(false)
    setMessages(prev => [...prev, { role: 'system', content: '❌ 已取消生成' }])
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">🎓 学练测一体化能力提升系统</h1>
        <p className="text-lg text-gray-600">打通学习、训练与测评全过程，实现能力成长的可量化、可验证与可追踪</p>
      </div>

      {/* ========== 流式对话框 ========== */}
      {streaming && (
        <div className="mb-8 bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          {/* 对话框头部 */}
          <div className="bg-gradient-to-r from-primary-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <span className="text-xl">🤖</span>
              </div>
              <div>
                <h2 className="text-white font-semibold">AI 学习助手</h2>
                <p className="text-white/70 text-xs">{stageLabel || '准备中...'}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center gap-1.5 text-xs text-white/80">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                生成中
              </span>
              <button onClick={handleCancel} className="px-3 py-1 text-sm text-white/80 hover:text-white hover:bg-white/20 rounded-lg transition-colors">✕ 取消</button>
            </div>
          </div>

          {/* 阶段进度条 */}
          <div className="px-6 py-3 bg-gray-50 border-b border-gray-100">
            <div className="flex gap-2">
              {STAGE_LABELS.map((label, i) => (
                <div key={i} className="flex-1 group">
                  <div className="relative">
                    <div className={`h-1.5 rounded-full transition-all duration-500 ${
                      i < stageIdx ? 'bg-green-500' : i === stageIdx ? 'bg-primary-500' : 'bg-gray-200'
                    }`} />
                    {i === stageIdx && <div className="absolute inset-0 h-1.5 rounded-full bg-primary-400 animate-ping" />}
                  </div>
                  <p className={`text-[9px] mt-1.5 truncate ${i === stageIdx ? 'text-primary-600 font-semibold' : i < stageIdx ? 'text-green-600' : 'text-gray-400'}`}>
                    {i < stageIdx ? '✓ ' : ''}{label.replace(/^[^\s]+\s/, '')}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* 对话消息区域 */}
          <div ref={scrollRef} className="px-6 py-4 max-h-[50vh] overflow-y-auto space-y-4 bg-gradient-to-b from-gray-50/50 to-white">
            {messages.map((msg, i) => {
              if (msg.role === 'system') {
                return (
                  <div key={i} className="flex justify-center">
                    <span className="inline-flex items-center gap-1.5 px-4 py-1.5 bg-gray-100 text-gray-500 text-xs rounded-full">
                      {msg.content}
                    </span>
                  </div>
                )
              }
              // assistant 消息 — AI 输出气泡
              return (
                <div key={i} className="flex gap-3">
                  <div className="shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center text-sm">
                    🤖
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-medium text-gray-700">{msg.label}</span>
                      {msg.done && <span className="text-[10px] text-green-600 bg-green-50 px-2 py-0.5 rounded-full">✓ 完成</span>}
                      {!msg.done && <span className="text-[10px] text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full animate-pulse">生成中</span>}
                    </div>
                    <div className="bg-white border border-gray-200 rounded-xl rounded-tl-sm p-4 shadow-sm">
                      {msg.formatted ? (
                        // 格式化后：排版样式
                        <div className="text-sm text-gray-700 leading-relaxed max-h-80 overflow-y-auto prose prose-sm max-w-none
                          [&_h2]:text-base [&_h2]:font-bold [&_h2]:text-gray-900 [&_h2]:mt-3 [&_h2]:mb-2
                          [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-gray-800 [&_h3]:mt-2 [&_h3]:mb-1
                          [&_p]:my-1
                          [&_li]:my-0.5 [&_li]:text-gray-600
                          [&_strong]:text-gray-800
                          [&_blockquote]:border-l-2 [&_blockquote]:border-primary-300 [&_blockquote]:pl-3 [&_blockquote]:py-1 [&_blockquote]:my-2 [&_blockquote]:bg-primary-50/50 [&_blockquote]:text-gray-600 [&_blockquote]:text-xs [&_blockquote]:rounded-r">
                          {msg.content.split('\n').map((line, li) => {
                            if (line.startsWith('## ')) return <h2 key={li}>{line.slice(3)}</h2>
                            if (line.startsWith('### ')) return <h3 key={li}>{line.slice(4)}</h3>
                            if (line.startsWith('> ')) return <blockquote key={li}><p>{line.slice(2)}</p></blockquote>
                            if (line.startsWith('- **')) {
                              const m = line.match(/^- \*\*(.+?)\*\*(.*)$/)
                              return m ? <p key={li}>• <strong>{m[1]}</strong>{m[2]}</p> : <p key={li}>{line}</p>
                            }
                            if (line.startsWith('- ')) return <p key={li}>• {line.slice(2)}</p>
                            if (line.startsWith('  ')) return <p key={li} className="ml-4 text-xs text-gray-500">{line.trim()}</p>
                            if (!line.trim()) return <div key={li} className="h-2" />
                            return <p key={li}>{line}</p>
                          })}
                        </div>
                      ) : (
                        // 流式中：等宽字体显示原始输出
                        <div className="font-mono text-xs text-gray-600 leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
                          {msg.content.slice(-1500)}
                          {!msg.done && <span className="inline-block w-1.5 h-3.5 bg-primary-500 ml-0.5 animate-pulse rounded-sm" />}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}

            {/* 空状态 */}
            {messages.length === 0 && (
              <div className="text-center py-8 text-gray-400 text-sm">
                <svg className="animate-spin h-8 w-8 mx-auto mb-3 text-primary-400" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                正在连接 AI 服务...
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========== 已登录学生信息卡片 ========== */}
      {studentName && !showSetup && !streaming && (
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-800">👋 欢迎回来，{studentName}！</h2>
            <button onClick={() => { setStudentName(''); setResult(null); setCompletedItems({ learning: {}, training: {}, testScore: null, testCorrect: null, testTotal: null }) }} className="text-sm text-gray-400 hover:text-primary-600 transition-colors">🔄 切换学生</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="p-4 bg-blue-50 rounded-lg text-center cursor-pointer hover:bg-blue-100 transition-colors" onClick={() => { setCurrentStep(1); nav('/tutor') }}>
              <span className="text-3xl block mb-2">🤖</span>
              <h3 className="font-semibold text-gray-800">进入伴学模式</h3>
              <p className="text-sm text-gray-600">AI对话、学习材料、练习题</p>
            </div>
            {result ? (
              <div className="p-4 bg-green-50 rounded-lg text-center cursor-pointer hover:bg-green-100 transition-colors" onClick={() => { setCurrentStep(1); nav('/profile') }}>
                <span className="text-3xl block mb-2">📊</span>
                <h3 className="font-semibold text-gray-800">查看学习报告</h3>
                <p className="text-sm text-gray-600">能力画像、学习内容、测试考核</p>
              </div>
            ) : (
              <div className="p-4 bg-purple-50 rounded-lg text-center cursor-pointer hover:bg-purple-100 transition-colors" onClick={handleDemo}>
                <span className="text-3xl block mb-2">{loading ? '⏳' : '📊'}</span>
                <h3 className="font-semibold text-gray-800">{loading ? '加载中...' : '开始能力测评'}</h3>
                <p className="text-sm text-gray-600">{loading ? '正在获取演示数据，请稍候...' : '生成专属学习计划和报告'}</p>
              </div>
            )}
          </div>
          {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">{error}</div>}
          <p className="text-sm text-gray-500 text-center">点击上方卡片继续学习，或使用顶部导航栏切换功能</p>
        </div>
      )}

      {/* ========== 输入表单 ========== */}
      {!studentName && !showSetup && !streaming && (
        <div className="card mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-6">开始学习之旅</h2>
          <div className="space-y-4">
            <div>
              <label className="label">请输入你的姓名</label>
              <input type="text" className="input text-lg py-3" placeholder="例如：张三"
                value={name} onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCheck()} />
              <p className="text-sm text-gray-500 mt-2">首次输入将为你定制专属学习计划，再次输入进入伴学模式</p>
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>}
            <LoadingButton onClick={handleCheck} loading={checking} loadingText="检查中..." className="btn-primary w-full text-lg py-3">🚀 继续</LoadingButton>
          </div>
        </div>
      )}

      {showSetup && !streaming && (
        <div className="card mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-800">👋 {name}，你好！请填写学习目标</h2>
            <button onClick={() => setShowSetup(false)} className="text-gray-500 hover:text-gray-700">返回</button>
          </div>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="label">目标岗位 *</label>
              <input type="text" className="input" placeholder="例如：Java后端开发工程师"
                value={form.position} onChange={e => setForm(p => ({ ...p, position: e.target.value }))} />
            </div>
            <div>
              <label className="label">目标级别</label>
              <select className="input" value={form.level} onChange={e => setForm(p => ({ ...p, level: e.target.value }))}>
                <option>入门</option><option>初级</option><option>中级</option><option>高级</option>
              </select>
            </div>
            <div>
              <label className="label">📄 上传简历（可选，支持PDF）</label>
              <div className="flex items-center gap-3">
                <label className="flex-1 flex items-center justify-center px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-primary-50 transition-colors">
                  <input type="file" accept=".pdf" className="hidden" onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (!file) return
                    setResumeFile(file)
                    setError(null)
                    try {
                      const data = await uploadResume(file)
                      setResumeText(data.text)
                      setResumeInfo({ name: file.name, pages: data.pages, chars: data.chars })
                    } catch (err) {
                      setError('简历解析失败: ' + err.message)
                      setResumeFile(null)
                      setResumeText(null)
                      setResumeInfo(null)
                    }
                  }} />
                  <span className="text-gray-500 text-sm">
                    {resumeFile ? `📎 ${resumeFile.name}` : '点击选择PDF文件'}
                  </span>
                </label>
                {resumeFile && (
                  <button type="button" onClick={() => { setResumeFile(null); setResumeText(null); setResumeInfo(null) }}
                    className="text-gray-400 hover:text-red-500 text-sm">✕</button>
                )}
              </div>
              {resumeInfo && (
                <p className="text-xs text-green-600 mt-1">✓ 解析成功：{resumeInfo.pages}页，{resumeInfo.chars}字</p>
              )}
              <p className="text-xs text-gray-400 mt-1">上传简历后，系统将根据简历内容生成更精准的能力画像</p>
            </div>
            {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>}
            <LoadingButton type="submit" loading={loading} loadingText="生成中，请耐心等待..." className="btn-primary w-full text-lg py-3">🎯 生成专属学习计划</LoadingButton>
          </form>
        </div>
      )}

      {/* 快速体验（未登录时显示） */}
      {!studentName && !streaming && (
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">快速体验</h2>
        <p className="text-gray-600 mb-4">不想填写？点击下方按钮直接查看演示效果：</p>
        <LoadingButton onClick={handleDemo} loading={loading} loadingText="加载演示数据..." className="btn-secondary w-full">📊 查看演示案例（Java后端开发工程师）</LoadingButton>
        {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mt-3">{error}</div>}
      </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
        {[
          { icon: '📊', title: '能力画像', desc: '四维评分体系，精准定位能力水平' },
          { icon: '📚', title: '个性化学习', desc: 'AI生成专属学习内容和训练计划' },
          { icon: '🤖', title: '智能伴学', desc: '随时提问，AI助教在线答疑' },
        ].map((f, i) => (
          <div key={i} className="card text-center">
            <span className="text-3xl mb-3 block">{f.icon}</span>
            <h3 className="font-semibold text-gray-800 mb-2">{f.title}</h3>
            <p className="text-sm text-gray-600">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
