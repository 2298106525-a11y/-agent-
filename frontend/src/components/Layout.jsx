import { Link, useLocation } from 'react-router-dom'
import ErrorBoundary from './ErrorBoundary'
import { useStore } from '../store'

const guestSteps = [
  { path: '/', label: '开始', icon: '🎯', alwaysEnabled: true },
  { path: '/profile', label: '画像', icon: '📊' },
  { path: '/learning', label: '学习', icon: '📚' },
  { path: '/training', label: '训练', icon: '🏋️' },
  { path: '/test', label: '考核', icon: '📝' },
  { path: '/assessment', label: '评估', icon: '📈' },
]

// 已登录学生：开始 → 伴学模式
const loggedInSteps = [
  { path: '/tutor', label: '开始', icon: '🎯', alwaysEnabled: true },
  { path: '/profile', label: '画像', icon: '📊' },
  { path: '/learning', label: '学习', icon: '📚' },
  { path: '/training', label: '训练', icon: '🏋️' },
  { path: '/test', label: '考核', icon: '📝' },
  { path: '/assessment', label: '评估', icon: '📈' },
]

function StepNav({ className, itemClass, activeClass, doneClass, idleClass, compact = false, loggedIn, hasResult }) {
  const location = useLocation()
  const { currentStep } = useStore()
  const steps = loggedIn ? loggedInSteps : guestSteps

  return (
    <nav className={className}>
      {steps.map((step, idx) => {
        const active = location.pathname === step.path || (step.path === '/tutor' && location.pathname.startsWith('/tutor'))
        const done = idx < currentStep && hasResult
        const enabled = step.alwaysEnabled || loggedIn

        const cls = `${itemClass} ${
          active ? activeClass :
          done ? doneClass :
          enabled ? idleClass :
          'text-gray-300 cursor-not-allowed'
        }`

        if (!enabled) {
          return (
            <span key={step.path} className={cls} title="请先输入学生姓名">
              <span className={compact ? 'text-base' : 'text-lg'}>{step.icon}</span>
              {<span className={compact ? 'text-[10px]' : 'text-sm'}>{step.label}</span>}
            </span>
          )
        }

        return (
          <Link key={step.path} to={step.path} className={cls}>
            <span className={compact ? 'text-base' : 'text-lg'}>{step.icon}</span>
            {<span className={compact ? 'text-[10px]' : 'text-sm'}>{step.label}</span>}
            {done && !compact && <span className="text-green-500 ml-0.5">✓</span>}
          </Link>
        )
      })}
    </nav>
  )
}

export default function Layout({ children }) {
  const { reset, currentStep, result, studentName } = useStore()
  const location = useLocation()
  const isTutor = location.pathname.startsWith('/tutor')
  const loggedIn = !!studentName
  const hasResult = !!result

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex flex-col">
      {/* Desktop Header */}
      <header className="bg-white/90 backdrop-blur-sm shadow-sm border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 shrink-0">
            <span className="text-2xl">🎓</span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-tight">学练测一体化</h1>
              <p className="text-xs text-gray-500">
                {loggedIn ? `学员: ${studentName}` : '能力提升系统 v2.0'}
              </p>
            </div>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <StepNav
              className="flex items-center gap-1"
              itemClass="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              activeClass="bg-primary-100 text-primary-700"
              doneClass="text-green-600 hover:bg-green-50"
              idleClass="text-gray-500 hover:bg-gray-100"
              loggedIn={loggedIn}
              hasResult={hasResult}
            />
          </div>
        </div>
      </header>

      {/* Mobile top steps */}
      {!isTutor && (
        <div className="md:hidden bg-white border-b border-gray-100 px-2 py-2">
          <StepNav
            className="flex items-center justify-between"
            itemClass="flex flex-col items-center px-1 py-1 rounded-lg transition-colors"
            activeClass="text-primary-600 bg-primary-50"
            doneClass="text-green-500"
            idleClass="text-gray-400"
            compact
            loggedIn={loggedIn}
            hasResult={hasResult}
          />
        </div>
      )}

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>

      {/* Mobile bottom tabs (tutor page) */}
      {isTutor && (
        <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-50 pb-safe">
          <div className="flex justify-around py-2">
            {(loggedIn ? loggedInSteps : guestSteps).slice(0, 4).map(step => (
              <Link key={step.path} to={step.path} className="flex flex-col items-center text-xs px-2 py-1 text-gray-400">
                <span className="text-lg">{step.icon}</span><span>{step.label}</span>
              </Link>
            ))}
            <Link to="/" className="flex flex-col items-center text-xs px-2 py-1 text-gray-400">
              <span className="text-lg">🏠</span><span>首页</span>
            </Link>
          </div>
        </nav>
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 mt-auto">
        <p className="text-center text-sm text-gray-500 py-4">
          桂林电子科技大学 · 第二十一届研电赛"润建"专项赛 · 方向二
        </p>
      </footer>
    </div>
  )
}