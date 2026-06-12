import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { StoreProvider, useStore } from './store'
import Layout from './components/Layout'
import Home from './pages/Home'
import Profile from './pages/Profile'
import Learning from './pages/Learning'
import Training from './pages/Training'
import Test from './pages/Test'
import Assessment from './pages/Assessment'
import Tutor from './pages/Tutor'

// 已登录用户（有 studentName）即可访问所有功能页
// 数据页面内部自行处理无 result 的情况
function Guard({ children }) {
  const { studentName } = useStore()
  return studentName ? children : <Navigate to="/" replace />
}

function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tutor" element={<Guard><Tutor /></Guard>} />
        <Route path="/tutor/:name" element={<Tutor />} />
        <Route path="/profile" element={<Guard><Profile /></Guard>} />
        <Route path="/learning" element={<Guard><Learning /></Guard>} />
        <Route path="/training" element={<Guard><Training /></Guard>} />
        <Route path="/test" element={<Guard><Test /></Guard>} />
        <Route path="/assessment" element={<Guard><Assessment /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <StoreProvider>
        <AppRoutes />
      </StoreProvider>
    </BrowserRouter>
  )
}