import { useState, useRef, useEffect } from 'react'

export default function Workspace({ history, result, isLoading, onGenerate }) {
  const [userInput, setUserInput] = useState('')
  const resultRef = useRef(null)

  // 새 결과 생성 시 스크롤
  useEffect(() => {
    if (result && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [result])

  const handleGenerate = () => {
    if (!userInput.trim()) { alert('광고 내용을 입력해 주세요.'); return }
    onGenerate(userInput.trim())
    setUserInput('')
  }

  // 현재 result 제외한 이전 히스토리 (최신순)
  const previousHistory = history.length > 1 ? [...history.slice(0, -1)].reverse() : []

  const downloadImage = () => {
    if (!result) return
    const a = document.createElement('a')
    a.href = `data:image/png;base64,${result.image}`
    a.download = 'ad_image.png'
    a.click()
  }

return (
    <section className="flex-1 bg-surface p-12 overflow-y-auto">
      <div className="max-w-4xl mx-auto space-y-12">

        {/* 입력 */}
        <div className="space-y-6">
          <h2 className="font-bold text-2xl tracking-tight text-on-surface">
            어떤 광고를 만들고 싶으신가요?
          </h2>
          <div className="bg-surface-container-lowest p-1 shadow-[0_12px_32px_-4px_rgba(42,52,57,0.08)] flex">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              placeholder={
                history.length === 0
                  ? '예) 아메리카노 한 잔으로 시작하는 따뜻한 하루'
                  : '피드백 또는 새로운 요청을 입력하세요'
              }
              className="flex-1 border-0 bg-transparent px-6 py-4 focus:ring-0 text-on-surface"
            />
            <button
              onClick={handleGenerate}
              disabled={isLoading}
              className="bg-primary text-on-primary px-10 py-4 font-bold tracking-widest uppercase transition-all hover:bg-primary-dim active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              GENERATE
            </button>
          </div>
        </div>

        {/* AI 메시지 */}
        {result?.message && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
              <span className="material-symbols-outlined text-on-primary" style={{ fontSize: '16px' }}>smart_toy</span>
            </div>
            <div className="bg-surface-container-low border border-outline-variant/15 px-5 py-4 text-sm text-on-surface leading-relaxed max-w-xl">
              {result.message}
            </div>
          </div>
        )}

        {/* 결과 */}
        {result && (
          <div ref={resultRef} className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg tracking-tight text-on-surface">
                Generated Result
              </h3>
              <button
                onClick={downloadImage}
                className="p-2 bg-surface-container-high text-on-surface-variant hover:text-primary transition-colors"
              >
                <span className="material-symbols-outlined">download</span>
              </button>
            </div>
            <div
              className="bg-surface-container-lowest border border-outline-variant/15 overflow-hidden"
              style={{ aspectRatio: '1/1', maxWidth: '640px' }}
            >
              <img
                src={`data:image/png;base64,${result.image}`}
                alt="생성된 광고 이미지"
                className="w-full h-full object-cover"
              />
            </div>
            {result.sd_prompt && (
              <div className="mt-3 p-3 bg-surface-container-low border border-outline-variant/15 max-w-xl">
                <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-1">SD Prompt (debug)</p>
                <p className="text-xs text-on-surface-variant font-mono break-all">{result.sd_prompt}</p>
              </div>
            )}
          </div>
        )}

        {/* 히스토리 */}
        {previousHistory.length > 0 && (
          <div className="space-y-4">
            <hr className="border-outline-variant/20" />
            <h3 className="font-bold text-base tracking-tight text-on-surface-variant">
              이전 생성 히스토리
            </h3>
            <div className="space-y-3">
              {previousHistory.map((turn) => (
                <div
                  key={turn.turn}
                  className="bg-surface-container-low p-6 border border-outline-variant/15"
                >
                  <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-2">
                    턴 {turn.turn}
                  </p>
                  <p className="text-sm text-on-surface font-medium mb-1">{turn.user_input}</p>
                  {turn.message && (
                    <p className="text-xs text-on-surface-variant whitespace-pre-line">{turn.message}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </section>
  )
}
