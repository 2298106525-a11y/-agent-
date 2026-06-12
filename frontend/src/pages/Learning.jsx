import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useStore } from '../store'
import MarkdownViewer from '../components/MarkdownViewer'

export default function Learning() {
  const { result, setCurrentStep, completedItems, completeLearning, studentName } = useStore()
  useEffect(() => { setCurrentStep(2) }, [setCurrentStep])
  // 调试：监听 completedItems 变化
  useEffect(() => { console.log('[Learning] completedItems变化:', Object.keys(completedItems?.learning || {}).length, '个模块') }, [completedItems])
  const [expanded, setExpanded] = useState(null)

  if (!result) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无测评数据，请先完成测评</p>
      <Link to="/tutor" className="btn-primary">返回伴学模式</Link>
    </div>
  )

  const { learning } = result
  const doneLearning = completedItems?.learning || {}
  const totalModules = learning?.contents?.reduce((sum, c) => sum + (c.learning_modules?.length || 0), 0) || 0
  const doneCount = Object.keys(doneLearning).length

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📚 学习内容</h1>
          <p className="text-gray-600">共 {totalModules} 个模块 · 已掌握 {doneCount} 个 · 预计 {learning?.total_minutes || 0} 分钟</p>
        </div>
        <div className="flex gap-2">
          <Link to="/profile" className="btn-secondary">← 上一步</Link>
          <Link to="/training" className="btn-primary">下一步：训练任务 →</Link>
        </div>
      </div>

      {/* 进度条 */}
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">学习进度</span>
          <span className="text-sm text-gray-500">{doneCount}/{totalModules}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div className="bg-green-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${totalModules ? Math.round(doneCount / totalModules * 100) : 0}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card"><p className="stat-label">学习模块</p><p className="stat-value text-primary-600">{totalModules}</p></div>
        <div className="stat-card"><p className="stat-label">已掌握</p><p className="stat-value text-green-600">{doneCount}</p></div>
        <div className="stat-card"><p className="stat-label">技能覆盖</p><p className="stat-value text-purple-600">{learning?.contents?.length || 0}</p></div>
      </div>

      {learning?.contents?.map((content, ci) => (
        <div key={ci} className="card">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">{content.skill_point?.name || `技能点 ${ci + 1}`}</h2>
              <p className="text-gray-600 mt-1">{content.summary}</p>
            </div>
            <span className="badge badge-blue">{content.skill_point?.category}</span>
          </div>

          {content.key_concepts?.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">核心概念：</h3>
              <div className="flex flex-wrap gap-2">
                {content.key_concepts.map((c, i) => <span key={i} className="badge badge-green">{c}</span>)}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {content.learning_modules?.map((mod, mi) => {
              const key = `${ci}-${mi}`
              const open = expanded === key
              const modId = mod.id || `MOD_${ci}_${mi}`
              const isDone = !!doneLearning[modId]
              return (
                <div key={mi} className={`border rounded-lg overflow-hidden transition-colors ${isDone ? 'border-green-300 bg-green-50/30' : 'border-gray-200'}`}>
                  <button className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
                    onClick={() => setExpanded(open ? null : key)}>
                    <div className="flex items-center gap-3">
                      {isDone
                        ? <span className="text-green-600 font-bold">✓</span>
                        : <span className="text-primary-600 font-medium">M{mi + 1}</span>
                      }
                      <span className={`font-medium ${isDone ? 'text-green-700' : 'text-gray-800'}`}>{mod.title}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">{mod.estimated_minutes || 30} min</span>
                      <svg className={`w-5 h-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </button>
                  {open && (
                    <div className="p-4 border-t border-gray-200">
                      <MarkdownViewer content={mod.content} />
                      <div className="mt-4 pt-3 border-t border-gray-100 flex justify-end">
                        <button onClick={() => completeLearning(modId)}
                          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${isDone ? 'text-gray-600 bg-gray-100 hover:bg-red-50 hover:text-red-600' : 'text-white bg-green-600 hover:bg-green-700'}`}>
                          {isDone ? '↩ 取消掌握' : '✓ 已掌握'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}

      <div className="flex justify-between">
        <Link to="/profile" className="btn-secondary">← 返回能力画像</Link>
        <Link to="/training" className="btn-primary">查看训练任务 →</Link>
      </div>
    </div>
  )
}
