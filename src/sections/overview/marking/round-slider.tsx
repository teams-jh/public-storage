import { m, animate, useMotionValue } from 'framer-motion';
import { useRef, useMemo, useState, useEffect, useCallback } from 'react';

import { alpha, styled, useTheme } from '@mui/material/styles';
import { Box, Paper, InputBase, Typography } from '@mui/material';

// ----------------------------------------------------------------------

const TICK_WIDTH = 12;
const SLIDER_HEIGHT = 80;
const BUBBLE_WIDTH = 72;
const BUBBLE_HEIGHT = 40;

const RootStyle = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  userSelect: 'none',
  touchAction: 'none',
  paddingTop: 60,
  paddingBottom: 20,
}));

const RulerContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '100%',
  height: SLIDER_HEIGHT,
  overflow: 'hidden',
  backgroundColor: theme.palette.background.neutral,
  borderRadius: theme.shape.borderRadius,
  border: `1px solid ${alpha(theme.palette.divider, 0.8)}`,
  cursor: 'grab',
  '&:active': {
    cursor: 'grabbing',
  },
}));

const Pointer = styled(Box)(({ theme }) => ({
  position: 'absolute',
  left: '50%',
  top: 0,
  bottom: 0,
  width: 2,
  backgroundColor: theme.palette.primary.main,
  zIndex: 10,
  pointerEvents: 'none',
  '&::after': {
    content: '""',
    position: 'absolute',
    top: -10,
    left: -6,
    borderLeft: '7px solid transparent',
    borderRight: '7px solid transparent',
    borderTop: `10px solid ${theme.palette.primary.main}`,
  },
  '&::before': {
    content: '""',
    position: 'absolute',
    bottom: -10,
    left: -6,
    borderLeft: '7px solid transparent',
    borderRight: '7px solid transparent',
    borderBottom: `10px solid ${theme.palette.primary.main}`,
  },
}));

const BubbleWrapper = styled(Box)(({ theme }) => ({
  position: 'absolute',
  top: 5,
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 20,
}));

const Bubble = styled(Paper)(({ theme }) => ({
  width: BUBBLE_WIDTH,
  height: BUBBLE_HEIGHT,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  borderRadius: theme.shape.borderRadius,
  fontSize: '1.25rem',
  fontWeight: theme.typography.fontWeightBold,
  cursor: 'pointer',
  position: 'relative',
  boxShadow: theme.shadows[12],
  transition: theme.transitions.create(['transform', 'background-color'], {
    duration: theme.transitions.duration.shorter,
  }),
  '&:hover': {
    backgroundColor: theme.palette.primary.dark,
    transform: 'scale(1.05)',
  },
  '&::after': {
    content: '""',
    position: 'absolute',
    bottom: -8,
    left: '50%',
    marginLeft: -8,
    borderLeft: '8px solid transparent',
    borderRight: '8px solid transparent',
    borderTop: `8px solid ${theme.palette.primary.main}`,
  },
}));

const RulerContent = styled(m.div)({
  display: 'flex',
  height: '100%',
  alignItems: 'flex-start',
  position: 'absolute',
  willChange: 'transform',
});

const Tick = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'isMajor',
})<{ isMajor?: boolean }>(({ isMajor, theme }) => ({
  width: 1,
  height: isMajor ? 24 : 12,
  backgroundColor: alpha(theme.palette.text.primary, isMajor ? 0.3 : 0.1),
  position: 'absolute',
  top: 0,
}));

const Label = styled(Typography)(({ theme }) => ({
  position: 'absolute',
  top: 30,
  transform: 'translateX(-50%)',
  fontSize: '0.875rem',
  color: theme.palette.text.secondary,
  pointerEvents: 'none',
  fontWeight: theme.typography.fontWeightMedium,
}));

// ----------------------------------------------------------------------

type Props = {
  min: number;
  max: number;
  value: number;
  onChange: (value: number) => void;
};

export default function RoundSlider({ min, max, value, onChange }: Props) {
  const theme = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingRef = useRef(false);

  const [isEditing, setIsEditing] = useState(false);
  const [inputValue, setInputValue] = useState(value.toString());
  const [containerWidth, setContainerWidth] = useState(0);

  const x = useMotionValue(0);

  // Measure container width and initialize position
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const width = containerRef.current.offsetWidth;
        setContainerWidth(width);

        // Initial set without animation
        const centerX = width / 2;
        const targetX = centerX - (value - min) * TICK_WIDTH;
        x.set(targetX);
      }
    };

    // Use a small timeout to ensure layout is ready
    const timer = setTimeout(measure, 50);
    window.addEventListener('resize', measure);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', measure);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync position when value changes from outside (not from dragging)
  useEffect(() => {
    if (!containerWidth || isEditing || isDraggingRef.current) return;

    const centerX = containerWidth / 2;
    const targetX = centerX - (value - min) * TICK_WIDTH;

    animate(x, targetX, {
      type: 'spring',
      stiffness: 300,
      damping: 30,
      restDelta: 0.01,
    });
  }, [value, min, containerWidth, isEditing, x]);

  const updateValueFromX = useCallback(
    (currentX: number) => {
      const centerX = containerWidth / 2;
      const newValue = Math.round(min + (centerX - currentX) / TICK_WIDTH);
      const clampedValue = Math.max(min, Math.min(max, newValue));
      if (clampedValue !== value) {
        onChange(clampedValue);
      }
    },
    [min, max, value, onChange, containerWidth]
  );

  const handleDragStart = () => {
    isDraggingRef.current = true;
  };

  const handleDrag = () => {
    updateValueFromX(x.get());
  };

  const handleDragEnd = () => {
    isDraggingRef.current = false;
    // Snap to the closest tick
    const centerX = containerWidth / 2;
    const targetX = centerX - (value - min) * TICK_WIDTH;
    animate(x, targetX, {
      type: 'spring',
      stiffness: 400,
      damping: 40,
    });
  };

  const handleBubbleClick = () => {
    setInputValue(value.toString());
    setIsEditing(true);
  };

  const handleInputBlur = () => {
    setIsEditing(false);
    const num = parseInt(inputValue, 10);
    if (!isNaN(num)) {
      const clampedValue = Math.max(min, Math.min(max, num));
      onChange(clampedValue);
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleInputBlur();
    }
  };

  const ticks = useMemo(() => {
    const items = [];
    // Only render a subset of ticks if performance is an issue, but 1200 is fine for simple Boxes
    for (let i = min; i <= max; i++) {
      const isMajor = i % 10 === 0;
      items.push(
        <Box key={i} sx={{ position: 'absolute', left: (i - min) * TICK_WIDTH }}>
          <Tick isMajor={isMajor} />
          {isMajor && <Label>{i}</Label>}
        </Box>
      );
    }
    return items;
  }, [min, max]);

  const rulerWidth = (max - min) * TICK_WIDTH;

  return (
    <RootStyle>
      <BubbleWrapper>
        <Bubble onClick={handleBubbleClick}>
          {isEditing ? (
            <InputBase
              autoFocus
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onBlur={handleInputBlur}
              onKeyDown={handleInputKeyDown}
              sx={{
                color: 'inherit',
                fontWeight: 'inherit',
                fontSize: 'inherit',
                '& input': { textAlign: 'center', p: 0 },
              }}
            />
          ) : (
            value
          )}
        </Bubble>
      </BubbleWrapper>

      <RulerContainer ref={containerRef}>
        <Pointer />
        <RulerContent
          drag="x"
          dragConstraints={{
            left: containerWidth / 2 - rulerWidth,
            right: containerWidth / 2,
          }}
          dragElastic={0.1}
          style={{ x, width: rulerWidth }}
          onDragStart={handleDragStart}
          onDrag={handleDrag}
          onDragEnd={handleDragEnd}
        >
          {ticks}
        </RulerContent>
      </RulerContainer>
    </RootStyle>
  );
}
