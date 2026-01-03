import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CostAnalysis from './pages/CostAnalysis'
import SecurityFindings from './pages/SecurityFindings'
import Recommendations from './pages/Recommendations'
import Layout from './components/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cost" element={<CostAnalysis />} />
        <Route path="/security" element={<SecurityFindings />} />
        <Route path="/recommendations" element={<Recommendations />} />
      </Routes>
    </Layout>
  )
}

export default App
