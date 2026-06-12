import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

const components = {
  code({ inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    if (!inline && match) {
      return (
        <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div" {...props}>
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      )
    }
    return <code className={className} {...props}>{children}</code>
  },
  h1: ({ children }) => <h1 className="text-2xl font-bold text-gray-900 mb-4">{children}</h1>,
  h2: ({ children }) => <h2 className="text-xl font-semibold text-gray-800 mb-3 mt-6">{children}</h2>,
  h3: ({ children }) => <h3 className="text-lg font-medium text-gray-700 mb-2 mt-4">{children}</h3>,
  p:  ({ children }) => <p className="text-gray-600 mb-3 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="list-disc list-inside text-gray-600 mb-3 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside text-gray-600 mb-3 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="text-gray-600">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-gray-800">{children}</strong>,
  table: ({ children }) => (
    <div className="overflow-x-auto mb-4">
      <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-gray-200">{children}</tbody>,
  th: ({ children }) => <th className="px-4 py-2 text-left text-sm font-medium text-gray-700">{children}</th>,
  td: ({ children }) => <td className="px-4 py-2 text-sm text-gray-600">{children}</td>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-primary-200 pl-4 italic text-gray-600 my-4">{children}</blockquote>
  ),
}

export default function MarkdownViewer({ content }) {
  if (!content) return <div className="text-gray-400 italic">暂无内容</div>
  return (
    <div className="prose prose-blue max-w-none">
      <ReactMarkdown components={components}>{content}</ReactMarkdown>
    </div>
  )
}