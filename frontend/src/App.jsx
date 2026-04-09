import { useState, useEffect, useRef } from 'react'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import SettingsPanel from './components/SettingsPanel'
import Workspace from './components/Workspace'
import LoadingOverlay from './components/LoadingOverlay'

export default function App() {
  const [theme, setTheme] = useState('cartoon')
  const [categoryKey, setCategoryKey] = useState('food')
  const [textPosition, setTextPosition] = useState('top')
  const [productFile, setProductFile] = useState(null)
  const [productPosition, setProductPosition] = useState('bottom-center')
  const [fontName, setFontName] = useState('nanumpen')
  const [textColor, setTextColor] = useState('#FFF5B4')
  const [fontSizeRatio, setFontSizeRatio] = useState(0.052)
  const [history, setHistory] = useState([])
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const pendingInputRef = useRef(null)
  const pollIntervalRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    pollIntervalRef.current = setInterval(async () => {
      try {
        const resp = await fetch(`/api/status/${jobId}`)
        const data = await resp.json()
        setJobStatus(data.status)

        if (data.status === 'done') {
          clearInterval(pollIntervalRef.current)
          setJobId(null)
          setJobStatus(null)
          setIsLoading(false)
          const userInput = pendingInputRef.current
          setHistory(prev => [
            ...prev,
            { turn: prev.length + 1, user_input: userInput, sd_prompt: data.sd_prompt, copy: data.copy, message: data.message },
          ])
          setResult({ image: data.image, copy: data.copy, message: data.message, sd_prompt: data.sd_prompt })
        } else if (data.status === 'error') {
          clearInterval(pollIntervalRef.current)
          setJobId(null)
          setJobStatus(null)
          setIsLoading(false)
          alert(`오류가 발생했습니다: ${data.detail}`)
        }
      } catch (_) {
        // 네트워크 오류 시 재시도
      }
    }, 2000)

    return () => clearInterval(pollIntervalRef.current)
  }, [jobId])

  const handleGenerate = async (userInput) => {
    setIsLoading(true)
    setJobStatus('pending')
    pendingInputRef.current = userInput

    const formData = new FormData()
    formData.append('user_input', userInput)
    formData.append('category_key', categoryKey)
    formData.append('theme_key', theme)
    formData.append('history', JSON.stringify(history))
    formData.append('product_position', productPosition)
    formData.append('text_position', textPosition)
    formData.append('font_name', fontName)
    formData.append('text_color', textColor)
    formData.append('font_size_ratio', fontSizeRatio)
    if (productFile) formData.append('product_image', productFile)

    try {
      const resp = await fetch('/api/generate', { method: 'POST', body: formData })
      if (!resp.ok) throw new Error(`서버 오류: ${resp.status}`)
      const data = await resp.json()
      setJobId(data.job_id)
    } catch (err) {
      alert(`오류가 발생했습니다: ${err.message}`)
      setIsLoading(false)
      setJobStatus(null)
    }
  }

  const handleReset = () => {
    setHistory([])
    setResult(null)
    setProductFile(null)
  }

  return (
    <div className="bg-surface text-on-surface">
      <Sidebar onReset={handleReset} />
      <Header />
      <main
        className="ml-64 mt-16 flex overflow-hidden"
        style={{ height: 'calc(100vh - 64px)' }}
      >
        <SettingsPanel
          theme={theme}
          onThemeChange={setTheme}
          categoryKey={categoryKey}
          onCategoryChange={setCategoryKey}
          textPosition={textPosition}
          onTextPositionChange={setTextPosition}
          productFile={productFile}
          onProductFileChange={setProductFile}
          productPosition={productPosition}
          onProductPositionChange={setProductPosition}
          fontName={fontName}
          onFontNameChange={setFontName}
          textColor={textColor}
          onTextColorChange={setTextColor}
          fontSizeRatio={fontSizeRatio}
          onFontSizeRatioChange={setFontSizeRatio}
        />
        <Workspace
          history={history}
          result={result}
          isLoading={isLoading}
          onGenerate={handleGenerate}
        />
      </main>
      {isLoading && <LoadingOverlay status={jobStatus} />}
    </div>
  )
}
