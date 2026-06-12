import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useStore } from '../store'
import RadarChart from '../components/RadarChart'
import ScoreBar from '../components/ScoreBar'

export default function Profile() {
  const { result, setCurrentStep } = useStore()
  useEffect(() => { setCurrentStep(1) }, [setCurrentStep])

  if (!result) return (
    <div className="card text-center py-12">
      <p className="text-gray-500 mb-4">暂无数据，请先进行测评</p>
      <Link to="/" className="btn-primary">返回首页</Link>
    </div>
  )

  const { framework, assessment } = result

  // 按分类聚合分数 → 雷达图
  const catScores = {}
  framework?.skill_points?.forEach(sp => {
    const sa = assessment?.skill_assessments?.find(s => s.skill_point_id === sp.id)
    if (sa) {
      if (!catScores[sp.category]) catScores[sp.category] = { total: 0, n: 0 }
      catScores[sp.category].total += sa.score
      catScores[sp.category].n += 1
    }
  })
  const radarData = Object.entries(catScores).length >= 3
    ? Object.entries(catScores).map(([cat, d]) => ({ axis: cat, value: d.n ? Math.round(d.total / d.n) : 0 }))
    : (assessment?.skill_assessments || []).slice(0, 8).map(sa => ({ axis: sa.skill_name, value: sa.score || 0 }))

  // 技能点得分 → 柱状图
  const skillData = framework?.skill_points?.map(sp => {
    const sa = assessment?.skill_assessments?.find(s => s.skill_point_id === sp.id)
    return { name: sp.name, value: sa?.score ?? 0 }
  }) || []

  const levelBadge = l => {
    const m = { expert: 'badge-red', advanced: 'badge-purple', intermediate: 'badge-yellow', junior: 'badge-blue', beginner: 'badge-green' }
    return m[l] || 'badge-green'
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">📊 能力画像</h1>
          <p className="text-gray-600">{framework?.position_name || '目标岗位'} · 技能分析</p>
        </div>
        <Link to="/learning" className="btn-primary">下一步：学习内容 →</Link>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card"><p className="stat-label">综合评分</p><p className="stat-value text-primary-600">{assessment?.overall_score ?? '--'}</p></div>
        <div className="stat-card"><p className="stat-label">技能点数</p><p className="stat-value text-green-600">{framework?.skill_points?.length || 0}</p></div>
        <div className="stat-card"><p className="stat-label">技能分类</p><p className="stat-value text-purple-600">{framework?.skill_categories?.length || 0}</p></div>
        <div className="stat-card"><p className="stat-label">能力等级</p><p className="stat-value text-orange-600">{assessment?.overall_level || '初级'}</p></div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RadarChart data={radarData} title={Object.keys(catScores).length >= 3 ? '分类能力雷达图' : '技能点评估雷达图'} />
        <ScoreBar data={skillData} title="技能点得分" />
      </div>

      {/* Skill Table */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">技能点详情</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['技能点', '分类', '要求等级', '得分', '描述'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-sm font-medium text-gray-700">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {framework?.skill_points?.map(sp => {
                const sa = assessment?.skill_assessments?.find(s => s.skill_point_id === sp.id)
                const sc = sa?.score
                return (
                  <tr key={sp.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{sp.name}</td>
                    <td className="px-4 py-3"><span className="badge badge-blue">{sp.category}</span></td>
                    <td className="px-4 py-3"><span className={`badge ${levelBadge(sp.required_level)}`}>{sp.required_level}</span></td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${sc >= 80 ? 'text-green-600' : sc >= 60 ? 'text-blue-600' : sc >= 40 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {sc != null ? `${sc}分` : '--'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{sp.description}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Assessment Summary */}
      {assessment && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">评估总结</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-green-700 mb-2">✅ 优势领域</h3>
              <ul className="space-y-1">{assessment.overall_strengths?.map((s, i) => <li key={i} className="text-gray-600 text-sm">• {s}</li>)}</ul>
            </div>
            <div>
              <h3 className="font-medium text-orange-700 mb-2">📈 待提升领域</h3>
              <ul className="space-y-1">{assessment.overall_weaknesses?.map((w, i) => <li key={i} className="text-gray-600 text-sm">• {w}</li>)}</ul>
            </div>
          </div>
          {assessment.conclusion && <div className="mt-4 p-4 bg-blue-50 rounded-lg"><p className="text-gray-700">{assessment.conclusion}</p></div>}
        </div>
      )}

      {/* 简历评估区块 */}
      {result.resume_profile && (
        <div className="card border-2 border-indigo-100 bg-gradient-to-br from-indigo-50 to-purple-50">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">📄 简历分析</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {result.resume_profile.education && (
              <div className="stat-card">
                <p className="stat-label">学历</p>
                <p className="stat-value text-indigo-600 text-base">{result.resume_profile.education}</p>
              </div>
            )}
            {result.resume_profile.experience_years > 0 && (
              <div className="stat-card">
                <p className="stat-label">工作年限</p>
                <p className="stat-value text-purple-600">{result.resume_profile.experience_years}年</p>
              </div>
            )}
            <div className="stat-card">
              <p className="stat-label">发现技能</p>
              <p className="stat-value text-green-600">{result.resume_profile.skills_found?.length || 0}项</p>
            </div>
          </div>

          {result.resume_profile.skills_found?.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-gray-700 mb-2">🛠️ 简历中的技能</h3>
              <div className="flex flex-wrap gap-2">
                {result.resume_profile.skills_found.map((s, i) => (
                  <span key={i} className="badge badge-blue">{s}</span>
                ))}
              </div>
            </div>
          )}

          {result.resume_profile.projects?.length > 0 && (
            <div className="mb-4">
              <h3 className="font-medium text-gray-700 mb-2">💼 项目经历</h3>
              <div className="space-y-2">
                {result.resume_profile.projects.map((p, i) => (
                  <div key={i} className="p-3 bg-white rounded-lg border border-gray-100">
                    <p className="font-medium text-gray-800">{p.name}</p>
                    <p className="text-sm text-gray-600 mt-1">{p.description}</p>
                    {p.technologies && <p className="text-xs text-indigo-600 mt-1">技术栈：{p.technologies}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.resume_profile.strengths_from_resume?.length > 0 && (
            <div>
              <h3 className="font-medium text-green-700 mb-2">💪 简历优势</h3>
              <ul className="space-y-1">
                {result.resume_profile.strengths_from_resume.map((s, i) => (
                  <li key={i} className="text-gray-600 text-sm">• {s}</li>
                ))}
              </ul>
            </div>
          )}

          {result.resume_initial_assessment?.summary && (
            <div className="mt-4 p-4 bg-indigo-100 rounded-lg">
              <p className="text-indigo-800 text-sm">{result.resume_initial_assessment.summary}</p>
            </div>
          )}
        </div>
      )}

      <div className="flex justify-end"><Link to="/learning" className="btn-primary">查看学习内容 →</Link></div>
    </div>
  )
}