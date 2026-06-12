import ReactECharts from 'echarts-for-react'

export default function ScoreBar({ data, title = '得分排行' }) {
  if (!data?.length) {
    return (
      <div className="card flex items-center justify-center h-64">
        <p className="text-gray-400">暂无数据</p>
      </div>
    )
  }

  const option = {
    title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'bold', color: '#1f2937' } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: '{b}: {c}' },
    grid: { left: '3%', right: '8%', bottom: '3%', top: '15%', containLabel: true },
    xAxis: { type: 'value', max: 100 },
    yAxis: { type: 'category', data: data.map(d => d.name).reverse(), axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar',
      data: data.map(d => ({
        value: d.value,
        itemStyle: {
          color: d.value >= 80 ? '#22c55e' : d.value >= 60 ? '#3b82f6' : d.value >= 40 ? '#f59e0b' : '#ef4444',
          borderRadius: [0, 4, 4, 0],
        },
      })).reverse(),
      label: { show: true, position: 'right', formatter: '{c}', fontSize: 12 },
      barWidth: '60%',
    }],
  }

  return (
    <div className="card">
      <ReactECharts option={option} style={{ height: `${Math.max(200, data.length * 40 + 80)}px` }} />
    </div>
  )
}