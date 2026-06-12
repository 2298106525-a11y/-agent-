import { Component } from 'react'
import { Link } from 'react-router-dom'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) { return { hasError: true, error } }
  componentDidCatch(error, info) { console.error('[ErrorBoundary]', error, info) }

  render() {
    if (this.state.hasError) {
      return (
        <div className="card text-center py-16">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">页面出现错误</h2>
          <p className="text-gray-600 mb-6">{this.state.error?.message || '未知错误'}</p>
          <div className="flex justify-center gap-4">
            <button onClick={() => this.setState({ hasError: false, error: null })} className="btn-secondary">重试</button>
            <Link to="/" className="btn-primary">返回首页</Link>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}