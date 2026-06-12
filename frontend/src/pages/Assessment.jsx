import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useStore } from '../store'
import RadarChart from '../components/RadarChart'

const lvColor = {
  beginner: 'text-green-600 bg-green-100',
  junior: 'text-blue-600 bg-blue-100',
  intermediate: 'text-yellow-600 bg-yellow-100',
  advanced: 'text-orange-600 bg-orange-100',
  expert: 'text-red-600 bg-red-100',
}

function levelFromScore(score) {
  if (score >= 90) return 'expert'
  if (score >= 75) return 'advanced'
  if (score >= 60) return 'intermediate'
  if (score >= 40) return 'junior'
  return 'beginner'
}

export default function Assessment() {
  const { result, setCurrentStep, completedItems } = useStore()
  useEffect(() => { setCurrentStep(5) }, [setCurrentStep])

  if (!result) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无测评数据，请先完成测评</p>
      <Link to="/tutor" className="btn-primary">返回伴学模式</Link>
    </div>
  )

  const { assessment, framework, learning, training } = result
  if (!assessment || !assessment.skill_assessments?.length) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无评估数据</p>
      <p className="text-sm text-gray-400 mb-4">评估生成可能失败了，请重新生成</p>
      <Link to="/" className="btn-primary">返回首页重新生成</Link>
    </div>
  )

  const doneLearning = completedItems?.learning || {}
  const doneTraining = completedItems?.training || {}
  const testScore = completedItems?.testScore
  const testCorrect = completedItems?.testCorrect
  const testTotal = completedItems?.testTotal

  // 构建 skill_point_id → 相关模块/任务 的映射
  const skillModuleMap = useMemo(() => {
    const map = {}
    learning?.contents?.forEach(c => {
      const spId = c.skill_point?.id
      if (!spId) return
      if (!map[spId]) map[spId] = { modules: [], tasks: [] }
      c.learning_modules?.forEach(m => {
        if (m.id) map[spId].modules.push(m.id)
      })
    })
    training?.tasks?.forEach(t => {
      const spId = t.skill_point_id
      if (!spId) return
      if (!map[spId]) map[spId] = { modules: [], tasks: [] }
      if (t.id) map[spId].tasks.push(t.id)
    })
    return map
  }, [learning, training])

  // 总模块数和总任务数
  const totalModules = learning?.contents?.reduce((s, c) => s + (c.learning_modules?.length || 0), 0) || 1
  const totalTasks = training?.total_tasks || 1
  const totalTestQuestions = testTotal || 1

  // 全局完成率
  const globalModDone = Object.keys(doneLearning).length
  const globalTaskDone = Object.keys(doneTraining).length
  const globalTestRate = (testTotal > 0 && testCorrect != null) ? testCorrect / testTotal : 0

  // 三大项得分（学习40 + 训练40 + 考核20 = 100）
  const learningScore = Math.round((globalModDone / totalModules) * 40)
  const trainingScore = Math.round((globalTaskDone / totalTasks) * 40)
  const testScorePoints = Math.round(globalTestRate * 20)
  const dynamicOverall = Math.min(learningScore + trainingScore + testScorePoints, 100)
  const dynamicLevel = levelFromScore(dynamicOverall)

  // 每个技能点的得分（按完成率分配）
  const dynamicSkills = useMemo(() => {
    const skillCount = (assessment.skill_assessments || []).length || 1
    const perSkillMax = { learn: 40 / skillCount, train: 40 / skillCount, test: 20 / skillCount }

    return (assessment.skill_assessments || []).map(sa => {
      const spId = sa.skill_point_id
      const related = skillModuleMap[spId] || { modules: [], tasks: [] }

      const modDone = related.modules.filter(id => doneLearning[id]).length
      const modTotal = related.modules.length || 1
      const modRate = modDone / modTotal

      const taskDone = related.tasks.filter(id => doneTraining[id]).length
      const taskTotal = related.tasks.length || 1
      const taskRate = taskDone / taskTotal

      const skillLearn = Math.round(modRate * perSkillMax.learn)
      const skillTrain = Math.round(taskRate * perSkillMax.train)
      const skillTest = Math.round(globalTestRate * perSkillMax.test)
      const current = Math.min(Math.round(skillLearn + skillTrain + skillTest), 100)

      return {
        ...sa,
        baseScore: 0,
        currentScore: current,
        growth: current,
        modDone, modTotal,
        taskDone, taskTotal,
        skillLearn, skillTrain, skillTest,
      }
    })
  }, [assessment, skillModuleMap, doneLearning, doneTraining, globalTestRate])

  const radarData = dynamicSkills.map(d => ({ axis: d.skill_name, value: d.currentScore }))
  const lc = lvColor[dynamicLevel] || 'text-gray-600 bg-gray-100'

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📈 能力评估报告</h1>
          <p className="text-gray-600">{assessment.user_name} · {assessment.position_name}</p>
        </div>
        <Link to="/" className="btn-primary">返回首页</Link>
      </div>

      {/* 总分大卡片 */}
      <div className="card text-center py-8">
        <p className="stat-label mb-2">综合评分</p>
        <div className="inline-flex items-center justify-center w-32 h-32 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 shadow-lg mb-4">
          <span className="text-4xl font-bold text-white">{dynamicOverall}</span>
        </div>
        <div className="flex items-center justify-center gap-4">
          <span className={`badge text-lg px-4 py-1 ${lc}`}>{dynamicLevel}</span>
          <span className="text-gray-500">{assessment.assessment_date}</span>
        </div>
        <p className="text-gray-600 mt-2">学习(40分) + 训练(40分) + 考核(20分) = 100分</p>
      </div>

      {/* 三大项得分 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card text-center">
          <p className="stat-label">📚 学习得分</p>
          <p className="text-3xl font-bold text-green-600">{learningScore}<span className="text-base text-gray-400">/40</span></p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div className="bg-green-500 h-2 rounded-full" style={{ width: `${(learningScore / 40) * 100}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-1">{globalModDone}/{totalModules} 模块</p>
        </div>
        <div className="card text-center">
          <p className="stat-label">🏋️ 训练得分</p>
          <p className="text-3xl font-bold text-blue-600">{trainingScore}<span className="text-base text-gray-400">/40</span></p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${(trainingScore / 40) * 100}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-1">{globalTaskDone}/{totalTasks} 任务</p>
        </div>
        <div className="card text-center">
          <p className="stat-label">📝 考核得分</p>
          <p className="text-3xl font-bold text-purple-600">{testScorePoints}<span className="text-base text-gray-400">/20</span></p>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
            <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${(testScorePoints / 20) * 100}%` }} />
          </div>
          <p className="text-xs text-gray-500 mt-1">{testCorrect ?? 0}/{testTotal ?? 0} 正确</p>
        </div>
      </div>

      {/* 完成度统计 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="stat-card">
          <p className="stat-label">学习完成</p>
          <p className="stat-value text-green-600">{globalModDone}/{totalModules}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">训练完成</p>
          <p className="stat-value text-blue-600">{globalTaskDone}/{totalTasks}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">考核正确率</p>
          <p className="stat-value text-purple-600">{testTotal > 0 ? `${Math.round(globalTestRate * 100)}%` : '未考核'}</p>
        </div>
      </div>

      {/* 图表 + 得分条 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RadarChart data={radarData} title="技能点评估雷达图（含成长）" />
        <div className="card">
          <h3 className="font-medium text-gray-800 mb-4">技能点得分明细</h3>
          <div className="space-y-3">
            {dynamicSkills.map((d, i) => (
              <div key={d.skill_point_id || i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">{d.skill_name}</span>
                  <span className={`text-sm font-medium ${d.currentScore >= 80 ? 'text-green-600' : d.currentScore >= 60 ? 'text-blue-600' : d.currentScore >= 40 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {d.currentScore}分
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div className={`h-2 rounded-full transition-all duration-700 ${d.currentScore >= 80 ? 'bg-green-500' : d.currentScore >= 60 ? 'bg-blue-500' : d.currentScore >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${d.currentScore}%` }} />
                </div>
                <div className="flex gap-3 mt-1">
                  <span className="text-[10px] text-green-600">📚 {d.skillLearn}分({d.modDone}/{d.modTotal})</span>
                  <span className="text-[10px] text-blue-600">🏋️ {d.skillTrain}分({d.taskDone}/{d.taskTotal})</span>
                  <span className="text-[10px] text-purple-600">📝 {d.skillTest}分</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 优势 & 待提升 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="card">
          <h3 className="text-lg font-semibold text-green-700 mb-4">✅ 优势领域</h3>
          <ul className="space-y-2">{assessment.overall_strengths?.map((s, i) => <li key={i} className="flex items-start gap-2"><span className="text-green-500 mt-1">•</span><span className="text-gray-700">{s}</span></li>)}</ul>
        </div>
        <div className="card">
          <h3 className="text-lg font-semibold text-orange-700 mb-4">📈 待提升领域</h3>
          <ul className="space-y-2">{assessment.overall_weaknesses?.map((w, i) => <li key={i} className="flex items-start gap-2"><span className="text-orange-500 mt-1">•</span><span className="text-gray-700">{w}</span></li>)}</ul>
        </div>
      </div>

      {/* 技能点详细评估 */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">技能点详细评估</h3>
        <div className="space-y-6">
          {dynamicSkills.map((d, i) => (
            <div key={d.skill_point_id || i} className={`border rounded-lg p-4 ${d.growth > 0 ? 'border-green-200 bg-green-50/30' : 'border-gray-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">{d.skill_name}</h4>
                <div className="flex items-center gap-2">
                  <span className={`badge ${lvColor[d.current_level] || 'bg-gray-100 text-gray-600'}`}>{d.current_level}</span>
                  {d.growth > 0 && (
                    <span className="badge bg-green-100 text-green-700">↑ +{d.growth}分</span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-3">
                <div><p className="stat-label">📚 学习</p><p className="text-xl font-bold text-green-600">{d.skillLearn}<span className="text-sm text-gray-400">分</span></p><p className="text-xs text-gray-500">{d.modDone}/{d.modTotal}模块</p></div>
                <div><p className="stat-label">🏋️ 训练</p><p className="text-xl font-bold text-blue-600">{d.skillTrain}<span className="text-sm text-gray-400">分</span></p><p className="text-xs text-gray-500">{d.taskDone}/{d.taskTotal}任务</p></div>
                <div><p className="stat-label">📝 考核</p><p className="text-xl font-bold text-purple-600">{d.skillTest}<span className="text-sm text-gray-400">分</span></p></div>
              </div>
              {d.strengths?.length > 0 && <div className="mb-2"><p className="text-sm font-medium text-green-700 mb-1">优势：</p><div className="flex flex-wrap gap-1">{d.strengths.map((s, j) => <span key={j} className="badge badge-green">{s}</span>)}</div></div>}
              {d.weaknesses?.length > 0 && <div className="mb-2"><p className="text-sm font-medium text-orange-700 mb-1">待提升：</p><div className="flex flex-wrap gap-1">{d.weaknesses.map((w, j) => <span key={j} className="badge badge-yellow">{w}</span>)}</div></div>}
              {d.practice_recommendations?.length > 0 && <div><p className="text-sm font-medium text-blue-700 mb-1">练习建议：</p><ul className="list-disc list-inside text-sm text-gray-600">{d.practice_recommendations.map((r, j) => <li key={j}>{r}</li>)}</ul></div>}
            </div>
          ))}
        </div>
      </div>

      {/* 趋势 & 下阶段 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {assessment.growth_trend && <div className="card"><h3 className="text-lg font-semibold text-gray-800 mb-3">📊 成长趋势</h3><p className="text-gray-700">{assessment.growth_trend}</p></div>}
        {assessment.next_stage_plan && <div className="card"><h3 className="text-lg font-semibold text-gray-800 mb-3">🎯 下阶段计划</h3><p className="text-gray-700">{assessment.next_stage_plan}</p></div>}
      </div>

      {/* 综合评语 */}
      {assessment.conclusion && (
        <div className="card bg-gradient-to-r from-blue-50 to-indigo-50">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">📋 综合评语</h3>
          <p className="text-gray-700 leading-relaxed">{assessment.conclusion}</p>
        </div>
      )}

      <div className="flex justify-between">
        <Link to="/test" className="btn-secondary">← 返回测试考核</Link>
        <Link to="/" className="btn-primary">开始新的测评</Link>
      </div>
    </div>
  )
}
