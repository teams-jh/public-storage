
const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'json', 'compactLottoNumber.json');
const rawData = fs.readFileSync(filePath, 'utf8');
const rawList = JSON.parse(rawData);

// Map to include drwNo based on 1-indexed position and sort descending by drwNo
const allData = rawList.map((item, index) => ({
    ...item,
    drwNo: index + 1,
}));
const data = allData.sort((a, b) => b.drwNo - a.drwNo);

const stats = {}; // drwNo -> num -> Set<diff>

function addStat(drwNo, num, diff) {
    if (!stats[drwNo]) stats[drwNo] = {};
    if (!stats[drwNo][num]) stats[drwNo][num] = new Set();
    stats[drwNo][num].add(diff);
}

// Logic from overview-lotto-number-view.tsx
for (let i = 0; i < data.length - 2; i++) {
    const r1 = data[i];     // Newer
    const r2 = data[i + 1];
    const r3 = data[i + 2];   // Older

    const nums1 = r1.No;
    const nums2 = r2.No;
    const nums3 = r3.No;

    for (const n1 of nums1) {
        for (const n2 of nums2) {
            const diff = n1 - n2;
            const absDiff = Math.abs(diff);

            if (diff === 0 || absDiff > 5) continue; // Logic updated to 5 in recent step

            const n3 = n2 - diff;
            if (nums3.includes(n3)) {
                addStat(r1.drwNo, n1, absDiff);
                addStat(r2.drwNo, n2, absDiff);
                addStat(r3.drwNo, n3, absDiff);
            }
        }
    }
}

// Check for size > 2
let foundCount = 0;
for (const drwNo in stats) {
    for (const num in stats[drwNo]) {
        const set = stats[drwNo][num];
        if (set.size > 2) {
            console.log(`Found Size > 2 at Round ${drwNo}, Number ${num}: Diffs [${Array.from(set).join(', ')}]`);
            foundCount++;
        }
    }
}

if (foundCount === 0) {
    console.log("No instances of diffSet.size > 2 found.");
} else {
    console.log(`Total instances found: ${foundCount}`);
}
