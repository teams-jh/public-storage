import { useState, useCallback } from 'react';

import { getIsMobile } from 'src/utils/is-mobile';

import * as LottoLibrary from 'src/api/lottolibrary';

import { toast } from 'src/components/snackbar';

const LOTTO_NUMBERS = Array.from({ length: 45 }, (_, i) => i + 1);

export function useLottoGenerator() {
  const [includedNumbers, setIncludedNumbers] = useState<number[]>([]);
  const [excludedNumbers, setExcludedNumbers] = useState<number[]>([]);
  const [generatedResults, setGeneratedResults] = useState<number[][]>([]);

  // 포함수 토글
  const handleToggleIncluded = useCallback(
    (num: number) => {
      if (excludedNumbers.includes(num)) return;
      setIncludedNumbers((prev) => {
        if (prev.includes(num)) return prev.filter((n) => n !== num);
        if (prev.length >= 6) return prev;
        return [...prev, num].sort((a, b) => a - b);
      });
    },
    [excludedNumbers]
  );

  // 제외수 토글
  const handleToggleExcluded = useCallback(
    (num: number) => {
      if (includedNumbers.includes(num)) return;
      setExcludedNumbers((prev) => {
        if (prev.includes(num)) return prev.filter((n) => n !== num);
        if (prev.length >= 39) return prev;
        return [...prev, num].sort((a, b) => a - b);
      });
    },
    [includedNumbers]
  );

  // 생성 로직 - 최대 5개 세트 생성 (중복 조합 제외)
  const handleGenerate = useCallback(() => {
    const resultsSet = new Set<string>();
    const needed = 6 - includedNumbers.length;

    if (needed < 0) {
      alert('포함수가 6개를 초과했습니다.');
      return false;
    }

    const availablePool = LOTTO_NUMBERS.filter(
      (n) => !excludedNumbers.includes(n) && !includedNumbers.includes(n)
    );

    if (availablePool.length < needed) {
      alert('선택 가능한 숫자가 부족합니다.');
      return false;
    }

    // 최대 100번 시도하여 유니크한 5개 세트 찾기 (보통 5번이면 충분)
    let attempts = 0;
    while (resultsSet.size < 5 && attempts < 100) {
      const result = [...includedNumbers];
      const pool = [...availablePool];

      for (let i = 0; i < needed; i++) {
        const randomIndex = Math.floor(Math.random() * pool.length);
        result.push(pool[randomIndex]);
        pool.splice(randomIndex, 1);
      }

      const sortedSet = result.sort((a, b) => a - b);
      resultsSet.add(JSON.stringify(sortedSet));
      attempts++;
    }

    setGeneratedResults(Array.from(resultsSet).map((s) => JSON.parse(s)));
    return true;
  }, [includedNumbers, excludedNumbers]);

  const handleReset = useCallback(() => {
    setIncludedNumbers([]);
    setExcludedNumbers([]);
    setGeneratedResults([]);
  }, []);

  const handleAutoSelect = useCallback(
    (type: 'included' | 'excluded') => {
      toast.info(`${type === 'included' ? '포함수' : '제외수'} 3개를 자동으로 선택합니다.`);

      const shuffledPool = [...LOTTO_NUMBERS]
        .filter((n) =>
          type === 'included' ? !excludedNumbers.includes(n) : !includedNumbers.includes(n)
        )
        .sort(() => 0.5 - Math.random());

      const selected = shuffledPool.slice(0, 3).sort((a, b) => a - b);

      if (type === 'included') {
        setIncludedNumbers(selected);
      } else {
        setExcludedNumbers(selected);
      }
    },
    [includedNumbers, excludedNumbers]
  );

  const handleShare = useCallback(async () => {
    const latest = LottoLibrary.getLatestLottoNumber();
    if (!latest || generatedResults.length === 0) return;

    const nextDrwNo = latest.drwNo + 1;
    const nextDate = new Date(latest.drwNoDate);
    nextDate.setDate(nextDate.getDate() + 7);

    const year = nextDate.getFullYear();
    const month = nextDate.getMonth() + 1;
    const day = nextDate.getDate();

    const formattedResults = generatedResults
      .map((result, index) => {
        const label = String.fromCharCode(65 + index);
        const numbers = result
          .sort((a, b) => a - b)
          .map((n) => n.toString().padStart(2, '0'))
          .join(', ');
        return `${label} : ${numbers}`;
      })
      .join('\n');

    const shareText = `[${nextDrwNo}]회 (${year}년 ${month}월 ${day}일 추첨)

${formattedResults}

https://lotto-viewer.vercel.app/`;

    const isMobile = getIsMobile();

    if (isMobile && navigator.share) {
      try {
        await navigator.share({
          title: '추천 로또 번호',
          text: shareText,
        });
        return;
      } catch (error) {
        console.warn('Share cancelled or failed:', error);
      }
    }

    try {
      await navigator.clipboard.writeText(shareText);
      toast.success('추천 로또 번호가 복사되었습니다!');
    } catch (error) {
      console.error('Clipboard copy failed:', error);
      toast.error('복사에 실패했습니다.');
    }
  }, [generatedResults]);

  return {
    includedNumbers,
    excludedNumbers,
    generatedResults,
    setIncludedNumbers,
    setExcludedNumbers,
    handleToggleIncluded,
    handleToggleExcluded,
    handleGenerate,
    handleReset,
    handleAutoSelect,
    handleShare,
  };
}
