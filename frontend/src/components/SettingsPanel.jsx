import { useRef } from 'react'

const FONTS = [
  { key: 'nanumpen',             label: '손글씨 (NanumPen)'       },
  { key: 'nanumgothicbold',      label: '고딕 볼드'                },
  { key: 'nanumgothicextrabold', label: '고딕 엑스트라볼드'         },
  { key: 'nanummyeongjobold',    label: '명조 볼드'                },
  { key: 'nanumbarun',           label: '바른고딕'                 },
]

const PRESET_COLORS = [
  { hex: '#FFF5B4', label: '따뜻한 노랑' },
  { hex: '#FFFFFF', label: '흰색'        },
  { hex: '#000000', label: '검정'        },
  { hex: '#FFB3B3', label: '파스텔 핑크' },
  { hex: '#B3D9FF', label: '파스텔 블루' },
]

const THEMES = [
  { key: 'cartoon',   label: '카툰'   },
  { key: 'realistic', label: '실사'   },
  { key: 'minimal',   label: '미니멀' },
]

const CATEGORIES = [
  { key: 'food',    label: '음식/카페'   },
  { key: 'it',      label: 'IT서비스/앱' },
  { key: 'fashion', label: '패션/의류'   },
  { key: 'beauty',  label: '뷰티/화장품' },
  { key: 'other',   label: '기타'        },
]

const TEXT_POSITIONS = [
  { key: 'top',    label: '상단 (Top)'    },
  { key: 'bottom', label: '하단 (Bottom)' },
  { key: 'center', label: '중앙 (Center)' },
]

const PRODUCT_POSITIONS = [
  { key: 'bottom-center', label: '하단 중앙' },
  { key: 'bottom-left',   label: '하단 좌측' },
  { key: 'bottom-right',  label: '하단 우측' },
  { key: 'center-left',   label: '중앙 좌측' },
  { key: 'center-right',  label: '중앙 우측' },
]

export default function SettingsPanel({
  theme, onThemeChange,
  categoryKey, onCategoryChange,
  textPosition, onTextPositionChange,
  productFile, onProductFileChange,
  productPosition, onProductPositionChange,
  fontName, onFontNameChange,
  textColor, onTextColorChange,
  fontSizeRatio, onFontSizeRatioChange,
}) {
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) onProductFileChange(file)
  }

  const handleClearProduct = () => {
    onProductFileChange(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <section className="w-80 flex-shrink-0 bg-surface-container-low border-r border-outline-variant/15 p-8 overflow-y-auto">
      <h2 className="font-bold text-lg mb-8 tracking-tight text-on-surface">Configuration</h2>

      <div className="space-y-8">
        {/* 업종 선택 */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            Industry (업종 선택)
          </label>
          <select
            value={categoryKey}
            onChange={(e) => onCategoryChange(e.target.value)}
            className="w-full bg-surface-container-highest border-0 h-12 px-4 focus:ring-0 text-on-surface text-sm"
          >
            {CATEGORIES.map(({ key, label }) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* 이미지 스타일 */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            Image Style (이미지 스타일)
          </label>
          <div className="grid grid-cols-3 gap-2">
            {THEMES.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => onThemeChange(key)}
                className={
                  theme === key
                    ? 'py-3 px-2 bg-primary text-on-primary font-bold text-xs uppercase transition-all'
                    : 'py-3 px-2 bg-surface-container-high text-on-surface font-bold text-xs uppercase hover:bg-surface-container-highest transition-all'
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* 카피 위치 */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            Copy Position (카피 위치)
          </label>
          <select
            value={textPosition}
            onChange={(e) => onTextPositionChange(e.target.value)}
            className="w-full bg-surface-container-highest border-0 h-12 px-4 focus:ring-0 text-on-surface text-sm"
          >
            {TEXT_POSITIONS.map(({ key, label }) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        {/* 제품 이미지 업로드 */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            Product Image (제품 이미지)
          </label>
          {!productFile ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-outline-variant/30 p-8 flex flex-col items-center justify-center bg-surface-container-lowest hover:bg-white cursor-pointer group transition-colors"
            >
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors mb-2">
                cloud_upload
              </span>
              <span className="text-xs text-on-surface-variant text-center">
                파일을 드래그하거나 클릭하여 업로드
              </span>
            </div>
          ) : (
            <div className="space-y-2">
              <img
                src={URL.createObjectURL(productFile)}
                alt="제품 이미지"
                className="w-full h-32 object-contain bg-surface-container-lowest"
              />
              <button
                onClick={handleClearProduct}
                className="w-full text-xs text-on-surface-variant hover:text-error transition-colors py-1"
              >
                제거
              </button>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* 카피 문구 스타일 */}
        <div className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            Copy Style (문구 스타일)
          </label>

          {/* 폰트 선택 */}
          <select
            value={fontName}
            onChange={(e) => onFontNameChange(e.target.value)}
            className="w-full bg-surface-container-highest border-0 h-12 px-4 focus:ring-0 text-on-surface text-sm"
          >
            {FONTS.map(({ key, label }) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>

          {/* 색상 프리셋 + 커스텀 피커 */}
          <div className="flex items-center gap-2 flex-wrap">
            {PRESET_COLORS.map(({ hex, label }) => (
              <button
                key={hex}
                title={label}
                onClick={() => onTextColorChange(hex)}
                className="w-7 h-7 flex-shrink-0 transition-transform hover:scale-110"
                style={{
                  backgroundColor: hex,
                  border: textColor === hex ? '2px solid #005bb0' : '2px solid #9facd7',
                }}
              />
            ))}
            <input
              type="color"
              value={textColor}
              onChange={(e) => onTextColorChange(e.target.value)}
              title="직접 선택"
              className="w-7 h-7 cursor-pointer border-2 border-outline-variant p-0"
              style={{ borderRadius: 0 }}
            />
          </div>

          {/* 폰트 크기 슬라이더 */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-on-surface-variant">
              <span>크기</span>
              <span>{Math.round(fontSizeRatio * 1000) / 10}%</span>
            </div>
            <input
              type="range"
              min="30" max="90" step="5"
              value={Math.round(fontSizeRatio * 1000)}
              onChange={(e) => onFontSizeRatioChange(Number(e.target.value) / 1000)}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-[10px] text-on-surface-variant">
              <span>작게</span>
              <span>크게</span>
            </div>
          </div>
        </div>

        {/* 제품 위치 */}
        {productFile && (
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">
              Product Position (제품 위치)
            </label>
            <select
              value={productPosition}
              onChange={(e) => onProductPositionChange(e.target.value)}
              className="w-full bg-surface-container-highest border-0 h-12 px-4 focus:ring-0 text-on-surface text-sm"
            >
              {PRODUCT_POSITIONS.map(({ key, label }) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </section>
  )
}
