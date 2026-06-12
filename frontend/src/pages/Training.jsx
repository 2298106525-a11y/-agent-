import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useStore } from '../store'

const typeMap = {
  exercise: { text: '练习', color: 'badge-blue' },
  case_study: { text: '案例分析', color: 'badge-green' },
  simulation: { text: '模拟实操', color: 'badge-purple' },
  mini_project: { text: '小项目', color: 'badge-yellow' },
  full_project: { text: '完整项目', color: 'badge-red' },
  peer_review: { text: '互评', color: 'badge-blue' },
}
const diffMap = {
  beginner: 'bg-green-100 text-green-800',
  junior: 'bg-blue-100 text-blue-800',
  intermediate: 'bg-yellow-100 text-yellow-800',
  advanced: 'bg-orange-100 text-orange-800',
  expert: 'bg-red-100 text-red-800',
}

export default function Training() {
  const { result, setCurrentStep, completedItems, completeTraining } = useStore()
  useEffect(() => { setCurrentStep(3) }, [setCurrentStep])
  const [expanded, setExpanded] = useState(null)
  const doneTraining = completedItems?.training || {}

  if (!result) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无测评数据，请先完成测评</p>
      <Link to="/tutor" className="btn-primary">返回伴学模式</Link>
    </div>
  )

  const { training } = result

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🏋️ 训练任务</h1>
          <p className="text-gray-600">共 {training?.total_tasks || 0} 个任务 · 预计 {training?.total_estimated_hours?.toFixed(1) || 0} 小时</p>
        </div>
        <div className="flex gap-2">
          <Link to="/learning" className="btn-secondary">← 上一步</Link>
          <Link to="/test" className="btn-primary">下一步：测试考核 →</Link>
        </div>
      </div>

      {/* 进度条 */}
      <div className="card">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">训练进度</span>
          <span className="text-sm text-gray-500">{Object.keys(doneTraining).length}/{training?.total_tasks || 0}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div className="bg-green-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${training?.total_tasks ? Math.round(Object.keys(doneTraining).length / training.total_tasks * 100) : 0}%` }} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card"><p className="stat-label">训练任务</p><p className="stat-value text-primary-600">{training?.total_tasks || 0}</p></div>
        <div className="stat-card"><p className="stat-label">已完成</p><p className="stat-value text-green-600">{Object.keys(doneTraining).length}</p></div>
        <div className="stat-card"><p className="stat-label">预计时长</p><p className="stat-value text-purple-600">{training?.total_estimated_hours?.toFixed(1) || 0}h</p></div>
      </div>

      {training?.title && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">{training.title}</h2>
          {training.description && <p className="text-gray-600">{training.description}</p>}
        </div>
      )}

      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800">训练任务列表</h2>
        {training?.tasks?.map((task, i) => {
          const open = expanded === i
          const tip = typeMap[task.type] || { text: task.type, color: 'badge-blue' }
          const dc = diffMap[task.difficulty] || 'bg-gray-100 text-gray-800'
          const taskId = task.id || `TASK_${i + 1}`
          const isDone = !!doneTraining[taskId]
          return (
            <div key={taskId} className={`card cursor-pointer transition-colors ${isDone ? 'border-green-300 bg-green-50/30' : ''}`} onClick={() => setExpanded(open ? null : i)}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {isDone
                      ? <span className="text-green-600 font-bold">✓</span>
                      : <span className="text-primary-600 font-bold">T{i + 1}</span>
                    }
                    <h3 className={`text-lg font-medium ${isDone ? 'text-green-700' : 'text-gray-900'}`}>{task.title}</h3>
                  </div>
                  <p className="text-gray-600 text-sm line-clamp-2">{task.description}</p>
                </div>
                <div className="flex items-center gap-2 ml-4 shrink-0">
                  <span className={`badge ${tip.color}`}>{tip.text}</span>
                  <span className={`badge ${dc}`}>{task.difficulty}</span>
                  <span className="text-sm text-gray-500">{task.estimated_minutes || 30} min</span>
                  <svg className={`w-5 h-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              {open && (
                <div className="mt-4 pt-4 border-t border-gray-200 space-y-4" onClick={e => e.stopPropagation()}>
                  <div><h4 className="font-medium text-gray-700 mb-1">任务描述</h4><p className="text-gray-600">{task.description}</p></div>
                  {task.requirements?.length > 0 && (
                    <div><h4 className="font-medium text-gray-700 mb-1">任务要求</h4>
                      <ul className="list-disc list-inside text-gray-600 text-sm space-y-1">{task.requirements.map((r, j) => <li key={j}>{r}</li>)}</ul>
                    </div>
                  )}
                  {task.hints?.length > 0 && (
                    <div><h4 className="font-medium text-gray-700 mb-1">提示</h4>
                      <ul className="list-disc list-inside text-gray-600 text-sm space-y-1">{task.hints.map((h, j) => <li key={j}>{h}</li>)}</ul>
                    </div>
                  )}
                  {task.evaluation_criteria?.length > 0 && (
                    <div><h4 className="font-medium text-gray-700 mb-1">评价标准</h4>
                      <ul className="list-disc list-inside text-gray-600 text-sm space-y-1">{task.evaluation_criteria.map((e, j) => <li key={j}>{e}</li>)}</ul>
                    </div>
                  )}
                  {task.reference_solution && (
                    <div><h4 className="font-medium text-gray-700 mb-1">参考解法</h4>
                      <div className="bg-gray-50 p-3 rounded-lg text-sm text-gray-600">{task.reference_solution}</div>
                    </div>
                  )}
                  <div className="pt-2 border-t border-gray-100 flex justify-end">
                    <button onClick={() => completeTraining(taskId)}
                      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${isDone ? 'text-gray-600 bg-gray-100 hover:bg-red-50 hover:text-red-600' : 'text-white bg-green-600 hover:bg-green-700'}`}>
                      {isDone ? '↩ 取消完成' : '✓ 标记完成'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {training?.scenarios?.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-800">训练场景</h2>
          {training.scenarios.map((sc, i) => (
            <div key={sc.id || i} className="card">
              <h3 className="text-lg font-medium text-gray-900 mb-2">{sc.title}</h3>
              <p className="text-gray-600 mb-3">{sc.description}</p>
              {sc.context && <div className="bg-blue-50 p-3 rounded-lg mb-3"><p className="text-sm text-blue-800"><span className="font-medium">场景背景：</span>{sc.context}</p></div>}
              {sc.expected_outcome && <p className="text-sm text-gray-600"><span className="font-medium">预期产出：</span>{sc.expected_outcome}</p>}
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between">
        <Link to="/learning" className="btn-secondary">← 返回学习内容</Link>
        <Link to="/test" className="btn-primary">查看测试考核 →</Link>
      </div>
    </div>
  )
}