import ReactECharts from 'echarts-for-react'

export default function RadarChart({ data, title = '能力雷达图' }) {
  if (!data?.length) {
    return (
      <div className="card flex items-center justify-center h-64">
        <p className="text-gray-400">暂无数据</p>
      </div>
    )
  }

  const option = {
    title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold', color: '#1f2937' } },
    tooltip: { trigger: 'item' },
    radar: {
      indicator: data.map(d => ({ name: d.axis, max: 100 })),
      shape: 'polygon',
      splitNumber: 5,
      axisName: { color: '#4b5563', fontSize: 13 },
      splitLine: { lineStyle: { color: '#e5e7eb' } },
      splitArea: { show: true, areaStyle: { color: ['rgba(59,130,246,0.05)', 'rgba(59,130,246,0.1)'] } },
    },
    series: [{
      type: 'radar',
      data: [{
        value: data.map(d => d.value),
        name: '能力值',
        areaStyle: { color: 'rgba(59,130,246,0.2)' },
        lineStyle: { color: '#3b82f6', width: 2 },
        itemStyle: { color: '#3b82f6' },
      }],
    }],
  }

  return (
    <div className="card">
      <ReactECharts option={option} style={{ height: '350px' }} />
    </div>
  )
}