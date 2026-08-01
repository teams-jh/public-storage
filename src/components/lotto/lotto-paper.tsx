import { useRef, useState, useLayoutEffect } from 'react';

import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { toast } from 'src/components/snackbar';

// ----------------------------------------------------------------------

const LOTTO_NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

type Props = {
  title?: string; // Used for accessibility or alternate render if needed, essentially unused in original
  headerText?: string;
  selectedNumbers: number[];
  disabledNumbers?: number[]; // Make optional
  onToggle?: (number: number) => void;
  onReset?: () => void;
  onAutoSelect?: () => void;
  maxSelection?: number; // Make optional
  color?: string;
  showLines?: boolean;
  readOnly?: boolean;
  extraLines?: { numbers: number[]; color: string }[];
  markingMode?: 'off' | 'on1' | 'on2';
};

export function LottoPaper({
  title,
  headerText = '1,000원',
  selectedNumbers,
  disabledNumbers = [],
  onToggle,
  onReset,
  onAutoSelect,
  maxSelection = 6,
  color = '#FF7575',
  showLines = false,
  readOnly = false,
  extraLines = [],
  markingMode = 'on1',
}: Props) {
  const mainColor = color;
  const selectedBgColor = color === '#FF7575' ? '#333' : color;

  const PAPER_WIDTH = 220;
  const CELL_WIDTH = 22;
  const CELL_HEIGHT = 23;
  const ROW_GAP = 1.3;
  const COL_GAP = 0.8;
  const FONT_SIZE = '13px';
  const CORNER_LINE = 5;

  const containerRef = useRef<HTMLDivElement>(null);
  const cellRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const [linePoints, setLinePoints] = useState<string>('');
  const [extraLinePoints, setExtraLinePoints] = useState<{ points: string; color: string }[]>([]);

  const extraLinesKey = JSON.stringify(extraLines);

  useLayoutEffect(() => {
    const calculatePath = () => {
      const container = containerRef.current;
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const scaleX = containerRect.width / container.offsetWidth || 1;
      const scaleY = containerRect.height / container.offsetHeight || 1;

      const getPointsString = (numbers: number[]) => {
        if (!numbers || numbers.length < 2) return '';
        return numbers
          .map((num) => {
            const cell = cellRefs.current[num];
            if (!cell) return null;
            const cellRect = cell.getBoundingClientRect();
            const x = (cellRect.left - containerRect.left + cellRect.width / 2) / scaleX;
            const y = (cellRect.top - containerRect.top + cellRect.height / 2) / scaleY;
            return `${x},${y}`;
          })
          .filter(Boolean)
          .join(' ');
      };

      const newLinePoints = showLines ? getPointsString(selectedNumbers) : '';
      setLinePoints((prev) => (prev !== newLinePoints ? newLinePoints : prev));

      if (extraLines && extraLines.length > 0) {
        const results = extraLines
          .map((line) => ({
            points: getPointsString(line.numbers),
            color: line.color,
          }))
          .filter((res) => res.points);

        const resultsKey = JSON.stringify(results);
        setExtraLinePoints((prev) => (JSON.stringify(prev) !== resultsKey ? results : prev));
      } else {
        setExtraLinePoints((prev) => (prev.length > 0 ? [] : prev));
      }
    };

    calculatePath();

    const observer = new ResizeObserver(calculatePath);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [selectedNumbers, showLines, extraLinesKey]);

  return (
    <Box
      ref={containerRef}
      sx={{
        width: PAPER_WIDTH,
        border: `1px solid ${mainColor}`,
        bgcolor: '#fff',
        position: 'relative',
        mx: 'auto',
        fontFamily: "'Roboto Mono', monospace",
        userSelect: 'none',
        borderRadius: '4px',
      }}
    >
      {/* SVG Overlay for Lines */}
      {(showLines || extraLinePoints.length > 0) && (
        <Box
          component="svg"
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 1,
          }}
        >
          {showLines && linePoints && (
            <polyline
              points={linePoints}
              fill="none"
              stroke="#ADFF2F"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ opacity: 0.8 }}
            />
          )}
          {extraLinePoints.map((line, idx) => (
            <polyline
              key={idx}
              points={line.points}
              fill="none"
              stroke={line.color}
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ opacity: 0.6 }}
            />
          ))}
        </Box>
      )}

      {/* Header */}
      <Box sx={{ height: 36, position: 'relative', borderBottom: `1px solid ${mainColor}` }}>
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: 0,
            width: '25%',
            height: '100%',
            borderRight: `1px solid ${mainColor}`,
            bgcolor: '#E0E0E0', // Grayish background for left part like image
          }}
        />
        <Box
          sx={{
            position: 'absolute',
            right: 0,
            top: 0,
            width: '75%',
            height: '100%',
            bgcolor: mainColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: '18px' }}>{headerText}</Typography>
        </Box>
      </Box>

      {/* Grid */}
      <Box sx={{ py: 1.5, px: 1, position: 'relative', zIndex: 2 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            rowGap: ROW_GAP,
            columnGap: COL_GAP,
          }}
        >
          {LOTTO_NUMBERS.map((num) => {
            const isSelected = selectedNumbers.includes(num);
            const isDisabled = disabledNumbers.includes(num);

            // Find any extra lines that include this number
            const extraLineMatches =
              markingMode === 'on2' ? extraLines.filter((line) => line.numbers.includes(num)) : [];

            return (
              <Box
                key={num}
                ref={(el: HTMLDivElement | null) => {
                  cellRefs.current[num] = el;
                }}
                onClick={() => !readOnly && !isDisabled && onToggle && onToggle(num)}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor:
                    readOnly || isDisabled ? (isDisabled ? 'not-allowed' : 'default') : 'pointer',
                  opacity: isDisabled ? 0.3 : 1,
                  position: 'relative',
                  width: CELL_WIDTH,
                  height: CELL_HEIGHT,
                  transition: 'all 0.15s ease',
                }}
              >
                {/* Brackets Background (Always show if not solid filled or based on preference) */}
                <Box
                  sx={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      height: '1px',
                      bgcolor: mainColor,
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      right: 0,
                      height: '1px',
                      bgcolor: mainColor,
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '1px',
                      height: CORNER_LINE,
                      bgcolor: mainColor,
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      left: 0,
                      width: '1px',
                      height: CORNER_LINE,
                      bgcolor: mainColor,
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      top: 0,
                      right: 0,
                      width: '1px',
                      height: CORNER_LINE,
                      bgcolor: mainColor,
                    }}
                  />
                  <Box
                    sx={{
                      position: 'absolute',
                      bottom: 0,
                      right: 0,
                      width: '1px',
                      height: CORNER_LINE,
                      bgcolor: mainColor,
                    }}
                  />
                </Box>

                {/* Marking Circles */}
                {markingMode !== 'off' && (
                  <>
                    {/* Main Selected Number Circle (on1, on2) */}
                    {isSelected && (
                      <Box
                        sx={{
                          position: 'absolute',
                          width: '100%',
                          height: '100%',
                          bgcolor: selectedBgColor,
                          borderRadius: '50%',
                          zIndex: 1,
                        }}
                      />
                    )}
                    {/* Extra Lines Circles (on2 only) */}
                    {markingMode === 'on2' &&
                      extraLineMatches.map((line, idx) => (
                        <Box
                          key={idx}
                          sx={{
                            position: 'absolute',
                            width: '100%',
                            height: '100%',
                            bgcolor: line.color,
                            borderRadius: '50%',
                            opacity: 0.4,
                            zIndex: isSelected ? 0 : 1, // Draw below selected circle if it exists
                          }}
                        />
                      ))}
                  </>
                )}

                {/* Number Text */}
                <Typography
                  sx={{
                    position: 'relative',
                    zIndex: 2,
                    fontWeight: isSelected && markingMode !== 'off' ? 600 : 500,
                    fontSize: FONT_SIZE,
                    color: isSelected && markingMode !== 'off' ? 'white' : mainColor,
                  }}
                >
                  {num}
                </Typography>
              </Box>
            );
          })}
        </Box>

        {/* Footer Buttons (Reset, etc) - Only show if not readOnly */}
        {!readOnly && (
          <Stack direction="row" justifyContent="space-between" sx={{ mt: 1.5, px: 0 }}>
            {['초기화', '자동선택', '나의번호등록'].map((label) => (
              <Box
                key={label}
                onClick={() => {
                  if (label === '초기화') {
                    onReset && onReset();
                  } else if (label === '자동선택') {
                    onAutoSelect && onAutoSelect();
                  } else {
                    toast.warning('지원하지 않는 기능입니다.');
                  }
                }}
                sx={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  height: 20,
                  '&:hover': { opacity: 0.7 },
                }}
              >
                <Box
                  sx={{
                    width: 4,
                    height: '100%',
                    borderTop: `1px solid ${mainColor}`,
                    borderLeft: `1px solid ${mainColor}`,
                    borderBottom: `1px solid ${mainColor}`,
                  }}
                />
                <Typography
                  sx={{
                    px: 0.5,
                    fontSize: '12px',
                    fontWeight: 500,
                    color: mainColor,
                    lineHeight: '20px',
                  }}
                >
                  {label}
                </Typography>
                <Box
                  sx={{
                    width: 4,
                    height: '100%',
                    borderTop: `1px solid ${mainColor}`,
                    borderRight: `1px solid ${mainColor}`,
                    borderBottom: `1px solid ${mainColor}`,
                  }}
                />
              </Box>
            ))}
          </Stack>
        )}
      </Box>
    </Box>
  );
}
