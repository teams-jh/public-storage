# public-storage Design Guide

이 문서는 **public-storage** 프로젝트의 UI/UX 디자인 원칙과 컴포넌트 스타일링 가이드를 정의합니다.
---

## 📐 아이콘-텍스트 수직 중앙 정렬 규칙 (Icon & Text Vertical Alignment)

### 🚨 기본 원칙: 아이콘의 세로 중심 높이와 텍스트의 수직 중앙 정렬 일치

- **상단 쏠림(Top Alignment) 방지**: 아이콘 크기가 텍스트보다 상대적으로 클 때, 텍스트가 아이콘의 상단에 붙어 시각적 불균형을 이루지 않도록 **반드시 수직 중앙 정렬(`items-center` / `align-items: center`)**을 적용합니다.
- **중심축 일치**: 텍스트의 세로 중심선이 아이콘의 중앙 가운데 높이에 정확히 일치하도록 배치합니다.

### 🎨 코드 작성 가이드

#### 1. Tailwind CSS (권장)
항상 컨테이너에 `flex items-center`를 기본 적용합니다.
```tsx
// ❌ Bad: 텍스트가 아이콘 상단에 붙는 현상 발생 (기본 items-start 또는 flex 미적용)
<div className="flex gap-2">
  <Icon className="w-8 h-8" />
  <span>아이콘 상단에 붙는 텍스트</span>
</div>

// ⭕ Good: 아이콘의 중앙 높이에 텍스트가 완벽하게 수직 중앙 정렬됨
<div className="flex items-center gap-2">
  <Icon className="w-8 h-8 shrink-0" />
  <span className="leading-none">중앙 정렬된 텍스트</span>
</div>
```

#### 2. 다중 라인 (제목 + 설명) 텍스트와 대형 아이콘 조합
```tsx
// ⭕ Good: 대형 아이콘 옆 2줄 텍스트 수직 중앙 정렬
<div className="flex items-center gap-3">
  <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0">
    <Icon className="w-6 h-6" />
  </div>
  <div className="flex flex-col justify-center min-w-0">
    <h4 className="text-sm font-bold leading-snug">제목 텍스트</h4>
    <p className="text-xs text-slate-500 leading-normal">설명 텍스트</p>
  </div>
</div>
```

#### 3. MUI (Material-UI) 환경
```tsx
// ⭕ Good: MUI Box flex 기반 수직 중앙 정렬 (Stack 사용 금지 규칙 준수)
<Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
  <SvgIcon sx={{ fontSize: 32 }} />
  <Typography variant="body1">수직 중앙 정렬 텍스트</Typography>
</Box>
```
