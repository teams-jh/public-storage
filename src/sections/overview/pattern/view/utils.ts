export const getConsecutiveColors = (diffSet?: Set<number>): string[] | undefined => {
  if (!diffSet || diffSet.size === 0) return undefined;

  // if (diffSet.size > 2) return ['#ffffff']; // Removed: Support multi-colors

  const getDiffColor = (d: number) => {
    switch (d) {
      case 0:
        return '#00BCD4'; // Cyan for repeat
      case 1:
        return '#F50057';
      case 2:
        return '#89ff29ff';
      case 3:
        return '#ffe603ff';
      case 4:
        return '#ff1fffff';
      case 5:
        return '#26b12dff';
      default:
        return '#000000';
    }
  };

  const diffs = Array.from(diffSet).sort();
  return diffs.map((d) => getDiffColor(d));
};
