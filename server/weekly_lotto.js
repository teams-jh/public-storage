const fs = require("fs");
const path = require("path");
const axios = require("axios");

const getLottoNumber = async (drwNo) => {
  try {
    const response = await axios.get(
      `https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo=${drwNo}`
    );

    if (response.status !== 200) return undefined;

    console.log(response.data);
    return response.data;
  } catch (error) {
    console.error(`Error fetching round ${drwNo}:`, error.message);
    return undefined;
  }
};

const getLottoRound = (date) => {
  const baseDate = new Date('2002-12-07T00:00:00');
  const targetDate = new Date(date);
  
  // Reset time to ensure day calculation is accurate
  targetDate.setHours(0, 0, 0, 0);
  baseDate.setHours(0, 0, 0, 0);

  const diffTime = targetDate - baseDate;
  const diffDays = diffTime / (1000 * 60 * 60 * 24);
  
  if (diffDays < 0) return 0;
  
  const round = Math.ceil(diffDays / 7) + 1;
  return round;
};

const updateLottoJson = async (targetDateStr) => {
  const filePath = path.join(__dirname, "../json/lottoNumber.json");

  try {
    const data = fs.readFileSync(filePath, "utf-8");
    const lottoJson = JSON.parse(data);
    const lastEntry = lottoJson[lottoJson.length - 1];
    const lastDrwNo = lastEntry ? lastEntry.drwNo : 0;
    
    const targetDate = targetDateStr ? new Date(targetDateStr) : new Date();
    const targetRound = getLottoRound(targetDate);

    console.log(`Last Round: ${lastDrwNo}, Target Round: ${targetRound} (Target Date: ${targetDateStr || 'Today'})`);

    if (targetRound <= lastDrwNo) {
      console.log("Already up to date.");
      return;
    }

    for (let i = lastDrwNo + 1; i <= targetRound; i++) {
      console.log(`Fetching round ${i}...`);
      const lottoData = await getLottoNumber(i);
      
      if (lottoData && lottoData.returnValue === 'success') {
        lottoJson.push(lottoData);
      } else {
        console.log(`Failed to fetch round ${i} or data not available yet.`);
        // If we fail to fetch, we might want to stop to avoid gaps, or continue?
        // Usually if one fails, subsequent might fail too if it's future.
        // But if it's a network error, we might want to retry.
        // For now, break is safer to avoid gaps.
        break; 
      }
    }

    fs.writeFileSync(filePath, JSON.stringify(lottoJson, null, 4));
    console.log("Update complete.");
  } catch (error) {
    console.error("Error updating lotto json:", error);
  }
};

// Execute if run directly
if (require.main === module) {
    // Check for command line argument or use default (undefined -> Today)
    const argDate = process.argv[2];
    updateLottoJson(argDate);
}