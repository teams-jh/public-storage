import React, { memo } from 'react';

export type LottoCellProps = {
  num: number;
  bgColor: string;
  textColor: string;
  overlayColor?: string;
  content: string | number;
  onClick?: () => void;
  onContextMenu?: (e: React.MouseEvent<HTMLDivElement>) => void;
  cursor?: string;
  consecutiveColors?: string[];
  isExcluded?: boolean;
  minWidth?: number;
};

export const LottoCell = memo(
  ({
    num,
    bgColor,
    textColor,
    overlayColor,
    content,
    onClick,
    onContextMenu,
    isExcluded,
    cursor = 'default',
    minWidth = 16,
    ...restProps
  }: LottoCellProps) => (
    <React.Fragment key={num}>
      <div
        onClick={onClick}
        onContextMenu={onContextMenu}
        style={{
          flex: 1,
          minWidth: `${minWidth}px`,
          aspectRatio: '1/1',
          backgroundColor: bgColor,
          borderRadius: '20%',
          cursor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: 'clamp(8px, 1.8vw, 12px)',
          color: textColor,
          position: 'relative',
          overflow: 'hidden',
          transition: 'background-color 0.5s ease, box-shadow 0.5s ease',
          boxShadow: restProps.consecutiveColors
            ? restProps.consecutiveColors.length === 1
              ? `inset 0 0 0 5px ${restProps.consecutiveColors[0]}`
              : (() => {
                  const colors = restProps.consecutiveColors!;
                  const getC = (idx: number) => colors[idx % colors.length];

                  const sTop = `inset 0 5px 0 0 ${getC(0)}`;
                  const sRight = `inset -5px 0 0 0 ${getC(1)}`;
                  const sBot = `inset 0 -5px 0 0 ${colors.length > 2 ? getC(2) : getC(1)}`;
                  const sLeft = `inset 5px 0 0 0 ${colors.length > 3 ? getC(3) : getC(0)}`;

                  return `${sTop}, ${sRight}, ${sBot}, ${sLeft}`;
                })()
            : 'none',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: isExcluded ? 'rgba(0, 0, 0, 0.12)' : overlayColor || 'transparent',
            pointerEvents: 'none',
            transition: 'background-color 0.5s ease',
          }}
        />
        {isExcluded && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
              zIndex: 2,
              padding: '2px',
            }}
          >
            <svg
              width="100%"
              height="100%"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ff3d3d"
              strokeWidth="3"
              strokeLinecap="round"
            >
              <line x1="4" y1="4" x2="20" y2="20" />
              <line x1="20" y1="4" x2="4" y2="20" />
            </svg>
          </div>
        )}
        <span style={{ position: 'relative', zIndex: 1, opacity: isExcluded ? 0.35 : 1 }}>
          {content}
        </span>
      </div>
    </React.Fragment>
  )
);
