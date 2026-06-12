import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import { useStore } from '../store'

const qType = {
  single_choice: { text: '单选题', color: 'badge-blue' },
  multi_choice: { text: '多选题', color: 'badge-purple' },
  true_false: { text: '判断题', color: 'badge-green' },
  short_answer: { text: '简答题', color: 'badge-yellow' },
  coding: { text: '编程题', color: 'badge-red' },
  case_analysis: { text: '案例分析', color: 'badge-blue' },
  project: { text: '项目考核', color: 'badge-red' },
}

/** 提取选项字母前缀: "D. 以上都是" → "D" */
function normAns(ans) {
  if (!ans) return ''
  return ans.trim().match(/^([A-Z])/i)?.[1]?.toUpperCase() || ans.trim()
}

export default function Test() {
  const { result, setCurrentStep, completedItems, saveTestScore } = useStore()
  useEffect(() => { setCurrentStep(4) }, [setCurrentStep])

  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [showAns, setShowAns] = useState({})
  // AI 批改状态: { [qid]: { score, feedback, loading } }
  const [aiGrades, setAiGrades] = useState({})

  if (!result) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无测评数据，请先完成测评</p>
      <Link to="/tutor" className="btn-primary">返回伴学模式</Link>
    </div>
  )

  const paper = result?.test_papers?.[0]
  if (!paper || !paper.questions?.length) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无试卷数据</p>
      <p className="text-sm text-gray-400 mb-4">试卷生成可能失败了，请重新生成</p>
      <Link to="/" className="btn-primary">返回首页重新生成</Link>
    </div>
  )

  // 题型分布
  const dist = {}
  paper.questions?.forEach(q => { const t = q.question_type || 'other'; dist[t] = (dist[t] || 0) + 1 })
  const pieOpt = {
    title: { text: '题型分布', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c}题 ({d}%)' },
    series: [{ type: 'pie', radius: '60%', data: Object.entries(dist).map(([t, c]) => ({ name: qType[t]?.text || t, value: c })) }],
  }

  // 选择答案（单选直接覆盖，多选切换逗号分隔列表）
  const select = (qid, val, isMulti) => {
    if (submitted) return
    if (isMulti) {
      setAnswers(p => {
        const current = (p[qid] || '').split(',').map(s => s.trim()).filter(Boolean)
        const idx = current.indexOf(val)
        if (idx >= 0) current.splice(idx, 1)
        else current.push(val)
        return { ...p, [qid]: current.join(', ') }
      })
    } else {
      setAnswers(p => ({ ...p, [qid]: val }))
    }
  }

  const toggle = qid => setShowAns(p => ({ ...p, [qid]: !p[qid] }))

  // 评分（修复：用 normAns 提取字母前缀比较）
  const grade = () => {
    let score = 0, correct = 0
    const details = {}
    paper.questions?.forEach(q => {
      const ua = answers[q.id] || ''
      let ok = false
      if (q.question_type === 'single_choice' || q.question_type === 'true_false') {
        ok = normAns(ua) === normAns(q.correct_answer)
      } else if (q.question_type === 'multi_choice') {
        const us = new Set(ua.split(',').map(s => normAns(s)).filter(Boolean))
        const cs = new Set(q.correct_answer.split(',').map(s => normAns(s)).filter(Boolean))
        ok = us.size === cs.size && [...us].every(x => cs.has(x))
      } else {
        // 简答/编程：检查 AI 批改结果
        const ag = aiGrades[q.id]
        if (ag?.score != null) {
          ok = ag.score >= 60
          score += Math.round(q.score * ag.score / 100)
          return // 不走下面的 score += q.score
        }
        ok = null // 待批改
      }
      if (ok) { score += q.score; correct++ }
      details[q.id] = ok
    })
    return { score, correct, details }
  }

  const submit = () => {
    setSubmitted(true)
    const all = {}; paper.questions?.forEach(q => { all[q.id] = true }); setShowAns(all)
  }

  // AI 批改简答/编程题
  const gradeWithAI = useCallback(async (q) => {
    const ua = answers[q.id]
    if (!ua?.trim()) return
    setAiGrades(p => ({ ...p, [q.id]: { loading: true } }))
    try {
      const base = import.meta.env.DEV ? 'http://localhost:8000' : ''
      const res = await fetch(`${base}/api/tutor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: result?.framework?.position_name || '学员',
          message: `请批改以下题目，给出0-100的分数和简短点评。只回复JSON格式：{"score":分数,"feedback":"点评"}\n\n题目：${q.question_text}\n\n学生答案：${ua}`,
          history: [],
        }),
      })
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let reply = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.slice(6))
              if (d.text) reply += d.text
            } catch {}
          }
        }
      }
      // 提取 JSON
      const match = reply.match(/\{[\s\S]*?\}/)
      if (match) {
        const parsed = JSON.parse(match[0])
        setAiGrades(p => ({ ...p, [q.id]: { score: parsed.score || 0, feedback: parsed.feedback || '' } }))
      } else {
        setAiGrades(p => ({ ...p, [q.id]: { score: 50, feedback: reply.slice(0, 200) } }))
      }
    } catch {
      setAiGrades(p => ({ ...p, [q.id]: { score: 0, feedback: 'AI批改失败，请重试' } }))
    }
  }, [answers, result])

  const { score, correct, details } = submitted ? grade() : { score: 0, correct: 0, details: {} }
  const total = paper.questions?.length || 0
  const autoCount = paper.questions?.filter(q => ['single_choice', 'multi_choice', 'true_false'].includes(q.question_type)).length || 0
  const essayCount = total - autoCount
  const essayGraded = Object.keys(aiGrades).filter(k => aiGrades[k]?.score != null).length
  const pct = paper.total_score > 0 ? Math.round(score / paper.total_score * 100) : 0

  useEffect(() => {
    if (submitted && autoCount > 0) {
      saveTestScore(score, correct, autoCount)
    }
  }, [submitted]) // eslint-disable-line

  const reset = () => {
    setAnswers({}); setSubmitted(false); setShowAns({}); setAiGrades({})
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📝 测试考核</h1>
          <p className="text-gray-600">{paper.title}</p>
        </div>
        <div className="flex gap-2">
          <Link to="/training" className="btn-secondary">← 上一步</Link>
          <Link to="/assessment" className="btn-primary">下一步：能力评估 →</Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card"><p className="stat-label">题目数量</p><p className="stat-value text-primary-600">{total}</p></div>
        <div className="stat-card"><p className="stat-label">总分</p><p className="stat-value text-green-600">{paper.total_score || 0}</p></div>
        <div className="stat-card"><p className="stat-label">及格分</p><p className="stat-value text-orange-600">{paper.passing_score || 60}</p></div>
        <div className="stat-card"><p className="stat-label">时限</p><p className="stat-value text-purple-600">{paper.time_limit_minutes || 60} min</p></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="card"><ReactECharts option={pieOpt} style={{ height: 300 }} /></div>
        <div className="card">
          <h3 className="font-medium text-gray-800 mb-4">题型说明</h3>
          <div className="space-y-2">
            {Object.entries(dist).map(([t, c]) => (
              <div key={t} className="flex items-center justify-between">
                <span className={`badge ${qType[t]?.color || 'badge-blue'}`}>{qType[t]?.text || t}</span>
                <span className="text-gray-600">{c}题</span>
              </div>
            ))}
          </div>
          {!submitted && <p className="mt-4 pt-4 border-t border-gray-200 text-sm text-gray-500">已答: {Object.keys(answers).length} / {total} 题</p>}
        </div>
      </div>

      {/* 成绩面板 */}
      {submitted && (
        <div className="card bg-gradient-to-r from-blue-50 to-indigo-50">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 考试成绩</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center"><p className="stat-label">得分</p><p className={`text-3xl font-bold ${score >= (paper.passing_score || 60) ? 'text-green-600' : 'text-red-600'}`}>{score}</p></div>
            <div className="text-center"><p className="stat-label">正确率</p><p className={`text-3xl font-bold ${pct >= 60 ? 'text-green-600' : 'text-red-600'}`}>{pct}%</p></div>
            <div className="text-center"><p className="stat-label">客观题</p><p className="text-3xl font-bold text-blue-600">{correct}/{autoCount}</p></div>
            <div className="text-center"><p className="stat-label">主观题</p><p className="text-3xl font-bold text-purple-600">{essayGraded}/{essayCount}</p></div>
          </div>
          {essayCount > 0 && essayGraded < essayCount && (
            <p className="mt-3 text-sm text-orange-600 text-center">💡 简答/编程题需点击「AI批改」评分</p>
          )}
          <div className="mt-4 flex justify-end"><button onClick={reset} className="btn-secondary">重新作答</button></div>
        </div>
      )}

      {!submitted && (
        <div className="flex justify-between items-center">
          <p className="text-sm text-gray-500">已答 {Object.keys(answers).length} / {total} 题</p>
          <button onClick={submit} className="btn-primary px-8 py-3 text-lg" disabled={!Object.keys(answers).length}>📤 提交试卷</button>
        </div>
      )}

      {/* 题目 */}
      {paper.questions?.map((q, i) => {
        const ti = qType[q.question_type] || { text: q.question_type, color: 'badge-blue' }
        const ua = answers[q.id]
        const ok = details[q.id]
        const isTF = q.question_type === 'true_false'
        const isMulti = q.question_type === 'multi_choice'
        const isEssay = !['single_choice', 'multi_choice', 'true_false'].includes(q.question_type) && !isTF
        const opts = isTF ? ['正确', '错误'] : q.options
        const ag = aiGrades[q.id]

        return (
          <div key={q.id || i} className={`card ${submitted ? (ok === true ? 'border-green-300 bg-green-50/50' : ok === false ? 'border-red-300 bg-red-50/50' : 'border-yellow-300 bg-yellow-50/50') : ''}`}>
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-primary-600 font-bold text-lg">Q{i + 1}</span>
                <span className={`badge ${ti.color}`}>{ti.text}</span>
                <span className="text-sm text-gray-500">{q.score}分</span>
                {submitted && ok === true && <span className="text-green-600 font-bold">✓</span>}
                {submitted && ok === false && <span className="text-red-600 font-bold">✗</span>}
                {submitted && ok === null && <span className="text-yellow-600 font-bold">⏳待批改</span>}
              </div>
              <button onClick={() => toggle(q.id)} className="text-sm text-primary-600 hover:text-primary-700">{showAns[q.id] ? '隐藏答案' : '查看答案'}</button>
            </div>
            <p className="text-gray-800 mb-3">{q.question_text}</p>

            {/* 选项（单选/多选/判断） */}
            {opts?.length > 0 && (
              <div className="space-y-2 mb-3 ml-4">
                {opts.map((opt, oi) => {
                  // 多选：检查是否在逗号分隔列表中
                  const sel = isMulti
                    ? (ua || '').split(',').map(s => s.trim()).includes(opt)
                    : ua === opt
                  return (
                    <button key={oi} onClick={() => select(q.id, opt, isMulti)} disabled={submitted}
                      className={`block w-full text-left px-4 py-2 rounded-lg border text-sm transition-colors ${
                        sel && submitted && ok === true ? 'border-green-500 bg-green-100 text-green-800'
                        : sel && submitted && ok === false ? 'border-red-500 bg-red-100 text-red-800'
                        : sel ? 'border-primary-500 bg-primary-50 text-primary-800'
                        : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                      } ${submitted ? 'cursor-default' : 'cursor-pointer'}`}>
                      <span className="mr-2">{isMulti ? (sel ? '☑' : '☐') : (sel ? '🔘' : '⚪')}{opt}</span>
                    </button>
                  )
                })}
              </div>
            )}

            {/* 简答/编程题输入 */}
            {isEssay && (
              <div className="mb-3 ml-4">
                <textarea className="input min-h-[100px] resize-y" placeholder="请输入你的答案..."
                  value={answers[q.id] || ''} onChange={e => select(q.id, e.target.value, false)} disabled={submitted} />
                {submitted && (
                  <div className="mt-2 flex items-center gap-2">
                    {ag?.score != null ? (
                      <div className={`p-3 rounded-lg text-sm flex-1 ${ag.score >= 60 ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                        <span className="font-bold">AI评分：{ag.score}分</span>
                        {ag.feedback && <p className="mt-1">{ag.feedback}</p>}
                      </div>
                    ) : ag?.loading ? (
                      <span className="text-sm text-gray-500 animate-pulse">AI 批改中...</span>
                    ) : (
                      <button onClick={() => gradeWithAI(q)} className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors">
                        🤖 AI批改
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 答案解析 */}
            {showAns[q.id] && (
              <div className="mt-4 pt-4 border-t border-gray-200 space-y-2">
                <div className="bg-green-50 p-3 rounded-lg"><p className="text-sm font-medium text-green-800">答案：{q.correct_answer}</p></div>
                {q.explanation && <div className="bg-blue-50 p-3 rounded-lg"><p className="text-sm text-blue-800"><span className="font-medium">解析：</span>{q.explanation}</p></div>}
              </div>
            )}
          </div>
        )
      })}

      <div className="flex justify-between">
        <Link to="/training" className="btn-secondary">← 返回训练任务</Link>
        <Link to="/assessment" className="btn-primary">查看能力评估 →</Link>
      </div>
    </div>
  )
}
