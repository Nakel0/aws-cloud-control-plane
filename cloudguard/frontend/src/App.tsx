import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import CostOptimization from './pages/CostOptimization'
import SecurityPosture from './pages/SecurityPosture'
import Reliability from './pages/Reliability'
import Findings from './pages/Findings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cost" element={<CostOptimization />} />
        <Route path="/security" element={<SecurityPosture />} />
        <Route path="/reliability" element={<Reliability />} />
        <Route path="/findings" element={<Findings />} />
      </Routes>
    </Layout>
  )
}

export default App
