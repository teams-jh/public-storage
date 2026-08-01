import { useRef, useMemo, useState, useCallback, useLayoutEffect } from 'react';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import { useTheme } from '@mui/material/styles';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';

import { getBallColor, Ball as LottoBall } from 'src/api/lottolibrary';

// ----------------------------------------------------------------------

type Props = {
  rounds: any[];
  includeBonus: boolean;
};

type LineCoords = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: string;
  count: number;
  showCount: boolean;
};

type RowConfig = {
  centerY: number;
  gapToNext: number;
  round: any;
};

export function AnalyticsRollover({ rounds, includeBonus }: Props) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  // Responsive constants
  const BALL_SIZE = isMobile ? 30 : 56;
  // Height of the content part of the row (ball + minimal padding)
  const ROW_CONTENT_HEIGHT = isMobile ? 44 : 80;
  const BALL_GAP = isMobile ? 6 : 20;
  const LEFT_PADDING = isMobile ? 70 : 100;

  // Gap settings
  const GAP_SMALL = 0;
  const GAP_LARGE = isMobile ? 30 : 50;

  // Refs for DOM measurement
  const containerRef = useRef<HTMLDivElement>(null);
  const ballRefsMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const [lines, setLines] = useState<LineCoords[]>([]);

  // Sort rounds descending (latest first)
  const sortedRounds = useMemo(() => [...rounds].sort((a, b) => b.drwNo - a.drwNo), [rounds]);

  // Helper to check if a round contains a number
  const roundHasNumber = useCallback(
    (r: any, n: number) => {
      if (r.numbers.includes(n)) return true;
      if (includeBonus && r.bonus === n) return true;
      return false;
    },
    [includeBonus]
  );

  // Helper to check rollover between two rounds
  const checkRolloverBetween = useCallback(
    (r1: any, r2: any) => {
      if (!r1 || !r2) return false;
      const nums1 = [...r1.numbers, ...(includeBonus ? [r1.bonus] : [])];
      const nums2 = [...r2.numbers, ...(includeBonus ? [r2.bonus] : [])];
      return nums1.some((n) => nums2.includes(n));
    },
    [includeBonus]
  );

  // Calculate Layout (Y positions and Gaps)
  const { rowConfigs, totalHeight } = useMemo(() => {
    let currentY = 0;
    const configs: RowConfig[] = [];

    sortedRounds.forEach((round, index) => {
      const nextRound = sortedRounds[index + 1];
      const hasRollover = checkRolloverBetween(round, nextRound);
      const gap = hasRollover ? GAP_LARGE : GAP_SMALL;

      // Center Y of this row
      const centerY = currentY + ROW_CONTENT_HEIGHT / 2;

      configs.push({
        centerY,
        gapToNext: gap,
        round,
      });

      // Advance Y
      if (index < sortedRounds.length - 1) {
        currentY += ROW_CONTENT_HEIGHT + gap;
      } else {
        currentY += ROW_CONTENT_HEIGHT;
      }
    });

    return { rowConfigs: configs, totalHeight: currentY };
  }, [sortedRounds, checkRolloverBetween, ROW_CONTENT_HEIGHT, GAP_SMALL, GAP_LARGE]);

  // Register ball ref
  const registerBallRef = useCallback(
    (drwNo: number, ballNum: number, element: HTMLDivElement | null) => {
      const key = `${drwNo}-${ballNum}`;
      if (element) {
        ballRefsMap.current.set(key, element);
      } else {
        ballRefsMap.current.delete(key);
      }
    },
    []
  );

  // Calculate lines based on actual DOM positions
  useLayoutEffect(() => {
    const calculateLines = () => {
      if (!containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const calculatedLines: LineCoords[] = [];

      rowConfigs.forEach((config, index) => {
        const nextIndex = index + 1;
        if (nextIndex >= rowConfigs.length) return;

        const currentRound = config.round;
        const nextRound = rowConfigs[nextIndex].round;

        const getDisplayBalls = (r: any) => {
          const nums = [...r.numbers].map((n: number, i: number) => ({
            val: n,
            type: 'main',
            originalIdx: i,
          }));
          if (includeBonus) {
            nums.push({ val: r.bonus, type: 'bonus', originalIdx: 6 });
          }
          return nums;
        };

        const currentBalls = getDisplayBalls(currentRound);
        const nextBalls = getDisplayBalls(nextRound);

        currentBalls.forEach((currBall) => {
          // Find this number in the next round
          const nextBallMatch = nextBalls.find((b) => b.val === currBall.val);

          if (nextBallMatch) {
            const ballNum = currBall.val;

            // Calculate Streak Length
            let streakCount = 1;
            let k = nextIndex + 1;
            while (k < rowConfigs.length) {
              if (roundHasNumber(rowConfigs[k].round, ballNum)) {
                streakCount++;
                k++;
              } else {
                break;
              }
            }

            // Determine if we should show the count
            let isLatest = true;
            if (index > 0) {
              if (roundHasNumber(rowConfigs[index - 1].round, ballNum)) {
                isLatest = false;
              }
            }

            const showCount = isLatest;

            // Get actual DOM positions
            const currentBallKey = `${currentRound.drwNo}-${ballNum}`;
            const nextBallKey = `${nextRound.drwNo}-${ballNum}`;

            const currentBallEl = ballRefsMap.current.get(currentBallKey);
            const nextBallEl = ballRefsMap.current.get(nextBallKey);

            if (currentBallEl && nextBallEl) {
              const currentRect = currentBallEl.getBoundingClientRect();
              const nextRect = nextBallEl.getBoundingClientRect();

              // Calculate center positions relative to container
              const x1 = currentRect.left - containerRect.left + currentRect.width / 2;
              const y1 = currentRect.top - containerRect.top + currentRect.height / 2;
              const x2 = nextRect.left - containerRect.left + nextRect.width / 2;
              const y2 = nextRect.top - containerRect.top + nextRect.height / 2;

              const color = getBallColor(ballNum);

              calculatedLines.push({
                x1,
                y1,
                x2,
                y2,
                color,
                count: streakCount,
                showCount,
              });
            }
          }
        });
      });

      setLines(calculatedLines);
    };

    // Calculate after DOM renders
    calculateLines();

    // Recalculate on resize
    const handleResize = () => {
      calculateLines();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [rowConfigs, includeBonus, roundHasNumber]);

  return (
    <Card sx={{ p: { xs: 1, sm: 3 }, borderRadius: 2, minHeight: 500 }}>
      {/* Center Container */}
      <Box sx={{ display: 'flex', justifyContent: 'center', overflowX: 'auto', pb: 2 }}>
        <Box ref={containerRef} sx={{ position: 'relative', width: 'fit-content' }}>
          {/* SVG Overlay for Lines */}
          <svg
            width="100%"
            height={totalHeight}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              pointerEvents: 'none',
              zIndex: 1,
              overflow: 'visible',
            }}
          >
            {lines.map((line, i) => (
              <g key={i}>
                <line
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke={line.color}
                  strokeWidth={isMobile ? '2' : '3'}
                  strokeOpacity="0.6"
                />

                {line.showCount && (
                  <text
                    x={(line.x1 + line.x2) / 2}
                    y={(line.y1 + line.y2) / 2}
                    fill="text.primary"
                    fontSize={isMobile ? '12' : '14'}
                    fontWeight="bold"
                    textAnchor="middle"
                    dominantBaseline="central"
                    style={{
                      fill: '#000',
                      paintOrder: 'stroke',
                      stroke: '#fff',
                      strokeWidth: '4px',
                    }}
                  >
                    {line.count}
                  </text>
                )}
              </g>
            ))}
          </svg>

          {/* Rows */}
          <Stack spacing={0}>
            {rowConfigs.map((config, i) => (
              <Stack
                key={config.round.drwNo}
                direction="row"
                alignItems="center"
                sx={{
                  height: ROW_CONTENT_HEIGHT,
                  mb: i < rowConfigs.length - 1 ? `${config.gapToNext}px` : 0,
                  position: 'relative',
                  zIndex: 2,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    width: LEFT_PADDING,
                    pl: isMobile ? 1 : 2,
                    color: 'text.secondary',
                    fontWeight: 600,
                    fontSize: isMobile ? '0.75rem' : '1rem',
                    flexShrink: 0,
                  }}
                >
                  {config.round.drwNo}회
                </Typography>

                <Stack direction="row" alignItems="center" spacing={`${BALL_GAP}px`}>
                  {config.round.numbers.map((num: number) => (
                    <Ball
                      key={num}
                      num={num}
                      size={BALL_SIZE}
                      fontSize={isMobile ? '0.85rem' : '1.25rem'}
                      onRef={(el) => registerBallRef(config.round.drwNo, num, el)}
                    />
                  ))}

                  {includeBonus && (
                    <>
                      <Typography
                        sx={{
                          mx: isMobile ? 0.5 : 1,
                          color: 'text.disabled',
                          fontSize: isMobile ? '1rem' : '1.5rem',
                        }}
                      >
                        +
                      </Typography>
                      <Ball
                        num={config.round.bonus}
                        size={BALL_SIZE}
                        fontSize={isMobile ? '0.85rem' : '1.25rem'}
                        onRef={(el) => registerBallRef(config.round.drwNo, config.round.bonus, el)}
                      />
                    </>
                  )}
                </Stack>
              </Stack>
            ))}
          </Stack>
        </Box>
      </Box>
    </Card>
  );
}

type BallProps = {
  num: number;
  size: number;
  fontSize: string;
  onRef?: (el: HTMLDivElement | null) => void;
};

function Ball({ num, size, fontSize, onRef }: BallProps) {
  return (
    <Box
      ref={onRef}
      sx={{
        display: 'inline-flex',
        flexShrink: 0,
      }}
    >
      <LottoBall
        sx={{
          width: size,
          height: size,
          fontSize,
          flexShrink: 0,
          background: `radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent 60%), ${getBallColor(
            num
          )}`,
          zIndex: 2,
          boxShadow: (theme) => theme.shadows[4],
        }}
      >
        {num}
      </LottoBall>
    </Box>
  );
}
