'use client';

import type { ThemeType } from 'src/api/lottolibrary';

import React, { useMemo, useState, useEffect, useCallback } from 'react';

import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import Tabs from '@mui/material/Tabs';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import { varAlpha } from 'minimal-shared/utils';

import { DashboardContent } from 'src/layouts/dashboard';
import { THEME_NAMES, getAllLottoNumbers } from 'src/api/lottolibrary';
import { OverviewMarkingView } from 'src/sections/overview/marking/view/overview-marking-view';
import { AnalyticsRollover } from 'src/sections/overview/analytics/analytics-rollover';

import { getItem, setItem, getLocalSync } from 'src/utils/local-storage';

import { Iconify } from 'src/components/iconify';

import { DataRow } from './components/data-row';
import { PredictRow } from './components/predict-row';
import { useLottoPattern } from './hooks/use-lotto-pattern';
import { useLottoMissing } from './hooks/use-lotto-missing';

// ----------------------------------------------------------------------

export function OverviewPatternView() {
  const [currentTab, setCurrentTab] = useState<'number' | 'marking' | 'rollover'>('number');
  const [data, setData] = useState<any[]>([]);

  const handleToggleTab = useCallback(() => {
    setCurrentTab((prev) =>
      prev === 'number' ? 'marking' : prev === 'marking' ? 'rollover' : 'number'
    );
  }, []);

  useEffect(() => {
    const onToggleEvent = () => {
      handleToggleTab();
    };
    window.addEventListener('toggle-pattern-tab', onToggleEvent);
    return () => {
      window.removeEventListener('toggle-pattern-tab', onToggleEvent);
    };
  }, [handleToggleTab]);
  const [visibleCount, setVisibleCount] = useState(50);
  const [showBonus, setShowBonus] = useState(false);
  const [isReversed, setIsReversed] = useState(false);

  // ⭐ 숫자 보기 토글 (ON → 숫자 전체 보임)
  const [showNumbers, setShowNumbers] = useState(true);

  // ⭐ 테마 선택
  const [theme, setTheme] = useState<ThemeType>('default');
  const [selectedNumbers, setSelectedNumbers] = useState<number[]>([]);
  const [excludedNumbers, setExcludedNumbers] = useState<number[]>([]);
  const [showMissing, setShowMissing] = useState(true);
  const [cellMinWidth, setCellMinWidth] = useState<number>(() => {
    const syncVal = getLocalSync('lotto_cell_min_width');
    if (syncVal) {
      const parsed = parseInt(syncVal, 10);
      if (!Number.isNaN(parsed) && parsed >= 10 && parsed <= 32) {
        return parsed;
      }
    }
    return 16;
  });

  useEffect(() => {
    getItem('lotto_cell_min_width').then((val) => {
      if (val) {
        const parsed = parseInt(val, 10);
        if (!Number.isNaN(parsed) && parsed >= 10 && parsed <= 32) {
          setCellMinWidth(parsed);
        }
      }
    });
  }, []);

  const handleZoomIn = useCallback(() => {
    setCellMinWidth((prev) => {
      const next = Math.min(32, prev + 2);
      setItem('lotto_cell_min_width', String(next));
      return next;
    });
  }, []);

  const handleZoomOut = useCallback(() => {
    setCellMinWidth((prev) => {
      const next = Math.max(10, prev - 2);
      setItem('lotto_cell_min_width', String(next));
      return next;
    });
  }, []);

  // ⭐ 연속 보기 토글 (0=OFF, 99=ALL, 1-5=Diff)
  const [consecutiveOption, setConsecutiveOption] = useState<number>(0);

  // ⭐ 점프 보기 토글 (0=OFF, Interval 2,3,4,5)
  const [jumpInterval, setJumpInterval] = useState<number>(0);

  // Pattern Highlights
  const [patternHighlights, setPatternHighlights] = useState<Record<number, Set<number>>>({});

  const { historyStats, predictCandidates, jumpHistoryStats, jumpPredictCandidates } =
    useLottoPattern(data, consecutiveOption, jumpInterval, showBonus);
  const missingStats = useLottoMissing(data, showBonus);

  const mergedPredictCandidates = useMemo(() => {
    const merged: Record<number, Set<number>> = {};

    if (consecutiveOption !== 0) {
      Object.entries(predictCandidates).forEach(([k, v]) => {
        merged[Number(k)] = new Set(v);
      });
    }

    if (jumpInterval > 0) {
      Object.entries(jumpPredictCandidates).forEach(([k, v]) => {
        const n = Number(k);
        if (!merged[n]) merged[n] = new Set();
        v.forEach((d) => merged[n].add(d));
      });
    }
    return merged;
  }, [predictCandidates, jumpPredictCandidates, consecutiveOption, jumpInterval]);

  const traceStats = useMemo(() => {
    const stats: Record<number, Record<number, Set<number>>> = {};
    if (selectedNumbers.length === 0 || !data || data.length < 2) return stats;

    const latestRound = data[0];
    const getRoundNumbers = (r: any) => (showBonus ? [...r.numbers, r.bonus] : r.numbers);
    const latestRoundNums = getRoundNumbers(latestRound);

    selectedNumbers.forEach((candidate) => {
      const diffs = mergedPredictCandidates[candidate];
      if (!diffs) return;

      diffs.forEach((absDiff) => {
        // 1. Check Interval 1 (Consecutive)
        if (consecutiveOption !== 0) {
          if (consecutiveOption !== 99 && consecutiveOption !== absDiff) {
            // Skip
          } else {
            [candidate - absDiff, candidate + absDiff].forEach((n1) => {
              if (!latestRoundNums.includes(n1)) return;
              const signedDiff = candidate - n1;
              if (Math.abs(signedDiff) !== absDiff) return;

              // Trace back and collect matches
              const traceMatches: { drwNo: number; num: number }[] = [];
              let currentNum = n1;
              let currentIdx = 0; // Starts at latest round

              while (currentIdx < data.length) {
                const r = data[currentIdx];
                if (getRoundNumbers(r).includes(currentNum)) {
                  traceMatches.push({ drwNo: r.drwNo, num: currentNum });
                  currentNum -= signedDiff;
                  currentIdx++;
                } else {
                  break;
                }
              }

              // Only commit if we have at least 2 history items (Candidate + 2 history = 3 total)
              if (traceMatches.length >= 2) {
                traceMatches.forEach((match) => {
                  if (!stats[match.drwNo]) stats[match.drwNo] = {};
                  if (!stats[match.drwNo][match.num]) stats[match.drwNo][match.num] = new Set();
                  stats[match.drwNo][match.num].add(absDiff);
                });
              }
            });
          }
        }

        // 2. Check Interval Jump (if active)
        if (jumpInterval > 0) {
          // Check previous point at specific Jump Interval
          const prevIdx = jumpInterval - 1;
          if (prevIdx < data.length) {
            const rPrev = data[prevIdx];
            [candidate - absDiff, candidate + absDiff].forEach((nPrev) => {
              if (getRoundNumbers(rPrev).includes(nPrev)) {
                const signedDiff = candidate - nPrev;
                if (Math.abs(signedDiff) !== absDiff) return;

                // Trace back
                const traceMatches: { drwNo: number; num: number }[] = [];
                let currentNum = nPrev;
                const currentIdx = prevIdx;

                // Collect first match
                traceMatches.push({ drwNo: rPrev.drwNo, num: currentNum });

                // Continue tracing
                let nextIdx = currentIdx + jumpInterval;
                let nextNum = currentNum - signedDiff;

                while (nextIdx < data.length) {
                  const rNext = data[nextIdx];
                  if (getRoundNumbers(rNext).includes(nextNum)) {
                    traceMatches.push({ drwNo: rNext.drwNo, num: nextNum });
                    currentNum = nextNum;
                    nextIdx += jumpInterval;
                    nextNum -= signedDiff;
                  } else {
                    break;
                  }
                }

                // Check length.
                if (traceMatches.length >= 2) {
                  traceMatches.forEach((match) => {
                    if (!stats[match.drwNo]) stats[match.drwNo] = {};
                    if (!stats[match.drwNo][match.num]) stats[match.drwNo][match.num] = new Set();
                    stats[match.drwNo][match.num].add(absDiff);
                  });
                }
              }
            });
          }
        }
      });
    });
    return stats;
  }, [selectedNumbers, mergedPredictCandidates, data, consecutiveOption, jumpInterval]);

  const latestPatternNodes = useMemo(() => {
    const nodes: Record<number, Set<number>> = {};
    const interval = consecutiveOption > 0 ? 1 : jumpInterval > 0 ? jumpInterval : 0;
    if (interval === 0 || !data || data.length < 3) return nodes;

    const getRoundNumbers = (r: any) => (showBonus ? [...r.numbers, r.bonus] : r.numbers);

    // 연속: 1~5 차이, 점프: 0~5 차이
    const allowedDiffs =
      consecutiveOption > 0
        ? consecutiveOption === 99
          ? [1, 2, 3, 4, 5]
          : [consecutiveOption]
        : [0, 1, 2, 3, 4, 5];

    const visited = new Set<string>();

    for (const absDiff of allowedDiffs) {
      const signs = absDiff === 0 ? [0] : [1, -1];
      for (const sign of signs) {
        const signedDiff = sign * absDiff;

        for (let i = 0; i < data.length; i++) {
          const nums = getRoundNumbers(data[i]);
          for (const val of nums) {
            const key = `${i}-${val}-${signedDiff}`;
            if (visited.has(key)) continue;

            let canExtendForward = false;
            const prevIdx = i - interval;
            if (prevIdx >= 0) {
              const prevVal = val - signedDiff;
              if (
                prevVal >= 1 &&
                prevVal <= 45 &&
                getRoundNumbers(data[prevIdx]).includes(prevVal)
              ) {
                canExtendForward = true;
              }
            }

            if (canExtendForward) continue;

            const chain: { idx: number; val: number }[] = [{ idx: i, val }];
            let currentIdx = i;
            let currentVal = val;

            while (true) {
              const nextIdx = currentIdx + interval;
              if (nextIdx >= data.length) break;

              const nextVal = currentVal + signedDiff;
              if (nextVal < 1 || nextVal > 45) break;

              if (getRoundNumbers(data[nextIdx]).includes(nextVal)) {
                chain.push({ idx: nextIdx, val: nextVal });
                currentIdx = nextIdx;
                currentVal = nextVal;
              } else {
                break;
              }
            }

            if (chain.length >= 3) {
              chain.forEach((node) => {
                visited.add(`${node.idx}-${node.val}-${signedDiff}`);
              });
              const head = chain[0];
              const headDrwNo = data[head.idx].drwNo;
              if (!nodes[headDrwNo]) {
                nodes[headDrwNo] = new Set();
              }
              nodes[headDrwNo].add(head.val);
            }
          }
        }
      }
    }

    return nodes;
  }, [data, consecutiveOption, jumpInterval, showBonus]);

  useEffect(() => {
    const allData = getAllLottoNumbers();
    const sortedDesc = [...allData].sort((a, b) => b.drwNo - a.drwNo);
    setData(sortedDesc);
    setVisibleCount(50);
  }, []);

  // Clear highlights when mode changes
  useEffect(() => {
    setPatternHighlights({});
  }, [consecutiveOption, jumpInterval]);

  const displayed = useMemo(() => {
    const slice = data.slice(0, visibleCount);
    return isReversed ? [...slice].reverse() : slice;
  }, [data, visibleCount, isReversed]);

  const handleNumberClick = useCallback(
    (num: number) => {
      if (selectedNumbers.includes(num)) {
        setSelectedNumbers((prev) => prev.filter((n) => n !== num));
        setExcludedNumbers((prev) => [...prev.filter((n) => n !== num), num].sort((a, b) => a - b));
      } else if (excludedNumbers.includes(num)) {
        setExcludedNumbers((prev) => prev.filter((n) => n !== num));
      } else {
        if (selectedNumbers.length < 6) {
          setSelectedNumbers((prev) => [...prev, num].sort((a, b) => a - b));
        }
      }
    },
    [selectedNumbers, excludedNumbers]
  );

  const handleNumberRightClick = useCallback(
    (num: number) => {
      if (excludedNumbers.includes(num)) {
        setExcludedNumbers((prev) => prev.filter((n) => n !== num));
      } else {
        setSelectedNumbers((prev) => prev.filter((n) => n !== num));
        setExcludedNumbers((prev) => [...prev, num].sort((a, b) => a - b));
      }
    },
    [excludedNumbers]
  );

  const handlePatternClick = useCallback(
    (drwNo: number, num: number) => {
      const isConsecutive = consecutiveOption > 0;
      const isJump = jumpInterval > 0;

      const activeStats = isConsecutive ? historyStats : jumpHistoryStats;
      const cellStats = activeStats[drwNo]?.[num];

      // If the clicked number is already highlighted, toggle it off
      if (patternHighlights[drwNo]?.has(num)) {
        setPatternHighlights({});
        return;
      }

      if (!cellStats || cellStats.size === 0) {
        // If clicking a non-pattern number? Maybe clear?
        // User said: "Different border number -> change to related".
        // If simply clicking empty space, maybe clear or ignore.
        // Let's clear if no pattern found at this spot, just to be clean.
        setPatternHighlights({});
        return;
      }

      const activeDiffs: number[] = [];
      cellStats.forEach((d) => {
        if (isConsecutive) {
          if (consecutiveOption === 99 || consecutiveOption === d) activeDiffs.push(d);
        } else if (isJump) {
          activeDiffs.push(d);
        }
      });

      if (activeDiffs.length === 0) {
        setPatternHighlights({});
        return;
      }

      const result: Record<number, Set<number>> = {};
      const addToResult = (r: number, n: number) => {
        if (!result[r]) result[r] = new Set();
        result[r].add(n);
      };

      addToResult(drwNo, num);
      const interval = isJump ? jumpInterval : 1;

      activeDiffs.forEach((diff) => {
        const visited = new Set<string>();
        visited.add(`${drwNo}-${num}`);

        const check = (r: number, n: number) => {
          // Check both directions (Up/Down)
          [1, -1].forEach((dir) => {
            const nextR = r + dir * interval;
            // Verify nextR exists in stats (optimization)
            // Note: activeStats keys are strings in JS, but we use numbers here.
            if (!activeStats[nextR]) return;

            [n - diff, n + diff].forEach((nextN) => {
              if (activeStats[nextR][nextN]?.has(diff)) {
                const key = `${nextR}-${nextN}`;
                if (!visited.has(key)) {
                  visited.add(key);
                  addToResult(nextR, nextN);
                  check(nextR, nextN);
                }
              }
            });
          });
        };
        check(drwNo, num);
      });

      setPatternHighlights(result);
    },
    [consecutiveOption, jumpInterval, historyStats, jumpHistoryStats, patternHighlights]
  );

  const getNextOption = (current: number) => {
    if (current === 0) return 99; // Off -> All
    if (current === 99) return 1; // All -> 1
    if (current < 5) return current + 1; // 1->2->3->4->5
    return 0; // 5 -> Off
  };

  const getOptionLabel = (opt: number, label: string) => {
    if (opt === 0) return `${label} (OFF)`;
    if (opt === 99) return `${label} (ON)`;
    return `${label} (${opt}칸)`;
  };

  return (
    <DashboardContent maxWidth="xl" sx={{ px: { xs: 0.5, sm: 2 } }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 1,
          mb: 1.5,
          px: { xs: 0.5, sm: 0 },
        }}
      >
        <Tabs
          value={currentTab}
          onChange={(e, val) => val && setCurrentTab(val)}
          sx={{
            bgcolor: (theme) => varAlpha(theme.palette.grey['500Channel'], 0.08),
            p: 0.5,
            borderRadius: 1.5,
            '& .MuiTab-root': {
              minHeight: 32,
              py: 0.5,
              px: 1.5,
              fontSize: '0.85rem',
              fontWeight: 600,
              borderRadius: 1,
              color: 'text.secondary',
              transition: (theme) => theme.transitions.create(['all'], { duration: 150 }),
              '&.Mui-selected': {
                color: 'text.primary',
                bgcolor: 'background.paper',
                boxShadow: (theme) => theme.customShadows.z1,
              },
            },
            '& .MuiTabs-indicator': {
              display: 'none',
            },
          }}
        >
          <Tab
            value="number"
            label="번호패턴"
            icon={<Iconify icon="solar:sort-by-alphabet-bold" width={16} />}
            iconPosition="start"
            disableRipple
          />
          <Tab
            value="marking"
            label="마킹패턴"
            icon={<Iconify icon="solar:pen-bold" width={16} />}
            iconPosition="start"
            disableRipple
          />
          <Tab
            value="rollover"
            label="이월패턴"
            icon={<Iconify icon="solar:repeat-bold" width={16} />}
            iconPosition="start"
            disableRipple
          />
        </Tabs>

        {currentTab === 'number' && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              flexWrap: 'wrap',
              justify: { xs: 'center', sm: 'flex-end' },
            }}
          >
            {/* 테마 선택 버튼 그룹 */}
            <ToggleButtonGroup
              size="small"
              value={theme}
              exclusive
              onChange={(e, newTheme) => newTheme && setTheme(newTheme)}
              aria-label="theme selection"
            >
              {(Object.keys(THEME_NAMES) as ThemeType[]).map((themeKey) => (
                <Tooltip key={themeKey} title={THEME_NAMES[themeKey]}>
                  <ToggleButton
                    value={themeKey}
                    aria-label={THEME_NAMES[themeKey]}
                    sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                  >
                    <Iconify
                      icon={themeKey === 'default' ? 'mdi:format-color-fill' : 'mdi:palette'}
                      width={24}
                      sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                    />
                  </ToggleButton>
                </Tooltip>
              ))}
            </ToggleButtonGroup>

            <ToggleButtonGroup
              size="small"
              value={[
                showNumbers && 'showNumbers',
                showBonus && 'showBonus',
                isReversed && 'isReversed',
                showMissing && 'showMissing',
              ].filter(Boolean)}
              onChange={(event, newValues) => {
                setShowNumbers(newValues.includes('showNumbers'));
                setShowBonus(newValues.includes('showBonus'));
                setIsReversed(newValues.includes('isReversed'));
                setShowMissing(newValues.includes('showMissing'));
              }}
              aria-label="view settings"
            >
              <Tooltip title="숫자 보기">
                <ToggleButton
                  value="showNumbers"
                  aria-label="show numbers"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:numeric"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>

              <Tooltip title="보너스 번호">
                <ToggleButton
                  value="showBonus"
                  aria-label="show bonus"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:star-circle-outline"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>

              <Tooltip title="역순">
                <ToggleButton
                  value="isReversed"
                  aria-label="reverse order"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify icon="mdi:sort" width={24} sx={{ width: { xs: 13, sm: 15, md: 16 } }} />
                </ToggleButton>
              </Tooltip>

              <Tooltip title="미출현">
                <ToggleButton
                  value="showMissing"
                  aria-label="show missing"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:gradient"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>
            </ToggleButtonGroup>

            {/* Pattern Button Group */}
            <ToggleButtonGroup
              size="small"
              exclusive
              value={consecutiveOption > 0 ? 'consecutive' : jumpInterval > 0 ? 'jump' : null}
              onChange={(event, newPattern) => {
                // Empty OnChange (using custom onClick)
              }}
              aria-label="pattern settings"
            >
              <Tooltip title={getOptionLabel(consecutiveOption, '연속')}>
                <ToggleButton
                  value="consecutive"
                  aria-label="show consecutive"
                  selected={consecutiveOption > 0}
                  onClick={() => {
                    const next = getNextOption(consecutiveOption);
                    setConsecutiveOption(next);
                    if (next > 0) setJumpInterval(0);
                  }}
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  {consecutiveOption > 0 ? (
                    <Box
                      component="span"
                      sx={{
                        fontWeight: 'bold',
                        fontSize: { xs: 8, sm: 11, md: 12 },
                        lineHeight: 1,
                      }}
                    >
                      {consecutiveOption === 99 ? 'On' : consecutiveOption}
                    </Box>
                  ) : (
                    <Iconify
                      icon="mdi:link-variant"
                      width={24}
                      sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                    />
                  )}
                </ToggleButton>
              </Tooltip>

              <Tooltip title={jumpInterval === 0 ? '점프 (OFF)' : `점프 (${jumpInterval}회차)`}>
                <ToggleButton
                  value="jump"
                  aria-label="jump pattern"
                  selected={jumpInterval > 0}
                  onClick={() => {
                    const next = jumpInterval === 0 ? 2 : jumpInterval === 5 ? 0 : jumpInterval + 1;
                    setJumpInterval(next);
                    if (next > 0) setConsecutiveOption(0);
                  }}
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  {jumpInterval > 0 ? (
                    <Box
                      component="span"
                      sx={{
                        fontWeight: 'bold',
                        fontSize: { xs: 8, sm: 11, md: 12 },
                        lineHeight: 1,
                      }}
                    >
                      {jumpInterval}
                    </Box>
                  ) : (
                    <Iconify
                      icon="mdi:stairs"
                      width={24}
                      sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                    />
                  )}
                </ToggleButton>
              </Tooltip>
            </ToggleButtonGroup>

            {/* Zoom Controls */}
            <ToggleButtonGroup size="small" aria-label="zoom settings">
              <Tooltip title="화면 축소">
                <ToggleButton
                  value="zoomOut"
                  onClick={handleZoomOut}
                  disabled={cellMinWidth <= 10}
                  aria-label="zoom out"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:magnify-minus-outline"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>

              <Tooltip title="화면 확대">
                <ToggleButton
                  value="zoomIn"
                  onClick={handleZoomIn}
                  disabled={cellMinWidth >= 32}
                  aria-label="zoom in"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:magnify-plus-outline"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>
            </ToggleButtonGroup>
          </Box>
        )}

        {currentTab === 'rollover' && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              flexWrap: 'wrap',
              justify: { xs: 'center', sm: 'flex-end' },
            }}
          >
            <ToggleButtonGroup
              size="small"
              value={showBonus ? ['showBonus'] : []}
              onChange={(event, newValues) => {
                setShowBonus(newValues.includes('showBonus'));
              }}
              aria-label="bonus settings"
            >
              <Tooltip title="보너스 번호">
                <ToggleButton
                  value="showBonus"
                  aria-label="show bonus"
                  sx={{ width: { xs: 20, sm: 22, md: 24 }, height: { xs: 20, sm: 22, md: 24 } }}
                >
                  <Iconify
                    icon="mdi:star-circle-outline"
                    width={24}
                    sx={{ width: { xs: 13, sm: 15, md: 16 } }}
                  />
                </ToggleButton>
              </Tooltip>
            </ToggleButtonGroup>
          </Box>
        )}
      </Box>

      {currentTab === 'number' ? (
        <Box sx={{ width: '100%' }}>
          {isReversed && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
              <Button
                variant="soft"
                color="inherit"
                onClick={() => setVisibleCount((prev) => Math.min(prev + 50, data.length))}
                disabled={visibleCount >= data.length}
                sx={{ minWidth: 40 }}
              >
                ↑
              </Button>
            </Box>
          )}

          <Box sx={{ overflowX: 'auto', width: '100%' }}>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                minWidth: `${Math.max(850, 45 * cellMinWidth + 140)}px`,
              }}
            >
              {!isReversed && (
                <PredictRow
                  selectedNumbers={selectedNumbers}
                  excludedNumbers={excludedNumbers}
                  handleNumberClick={handleNumberClick}
                  handleNumberRightClick={handleNumberRightClick}
                  showNumbers={showNumbers}
                  theme={theme}
                  showConsecutive={consecutiveOption > 0 || jumpInterval > 0}
                  consecutiveCandidates={mergedPredictCandidates}
                  cellMinWidth={cellMinWidth}
                />
              )}

              {displayed.map((round) => {
                const roundHistory = historyStats[round.drwNo];
                const roundJump = jumpHistoryStats[round.drwNo];
                const roundTrace = traceStats[round.drwNo];

                // Merge consecutive and jump stats
                const mergedStats: Record<number, Set<number>> = {};

                if (consecutiveOption !== 0 && roundHistory) {
                  Object.entries(roundHistory).forEach(([k, v]) => {
                    mergedStats[Number(k)] = new Set(v);
                  });
                }

                if (jumpInterval > 0 && roundJump) {
                  Object.entries(roundJump).forEach(([k, v]) => {
                    const n = Number(k);
                    if (!mergedStats[n]) mergedStats[n] = new Set();
                    v.forEach((d) => mergedStats[n].add(d));
                  });
                }

                if (roundTrace) {
                  Object.entries(roundTrace).forEach(([numStr, set]) => {
                    const num = Number(numStr);
                    if (mergedStats[num]) {
                      mergedStats[num] = new Set([...mergedStats[num], ...set]);
                    } else {
                      mergedStats[num] = set;
                    }
                  });
                }

                return (
                  <DataRow
                    key={round.drwNo}
                    round={round}
                    showBonus={showBonus}
                    showNumbers={showNumbers}
                    theme={theme}
                    showMissing={showMissing}
                    missingStreakMap={missingStats[round.drwNo]}
                    showConsecutive={consecutiveOption > 0 || jumpInterval > 0}
                    consecutiveMap={mergedStats}
                    onPatternClick={handlePatternClick}
                    highlightedMap={patternHighlights[round.drwNo]}
                    latestPatternMap={latestPatternNodes[round.drwNo]}
                    cellMinWidth={cellMinWidth}
                  />
                );
              })}

              {isReversed && (
                <PredictRow
                  selectedNumbers={selectedNumbers}
                  excludedNumbers={excludedNumbers}
                  handleNumberClick={handleNumberClick}
                  handleNumberRightClick={handleNumberRightClick}
                  showNumbers={showNumbers}
                  theme={theme}
                  showConsecutive={consecutiveOption > 0 || jumpInterval > 0}
                  consecutiveCandidates={mergedPredictCandidates}
                  cellMinWidth={cellMinWidth}
                />
              )}
            </div>
          </Box>

          {!isReversed && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3, mb: 1 }}>
              <Button
                variant="soft"
                color="inherit"
                onClick={() => setVisibleCount((prev) => Math.min(prev + 50, data.length))}
                disabled={visibleCount >= data.length}
                sx={{ minWidth: 40 }}
              >
                ↓
              </Button>
            </Box>
          )}
        </Box>
      ) : currentTab === 'marking' ? (
        <OverviewMarkingView disableDashboardContent />
      ) : (
        <AnalyticsRollover rounds={data} includeBonus={showBonus} />
      )}
    </DashboardContent>
  );
}
