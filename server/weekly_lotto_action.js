const fs = require("fs");
const path = require("path");
const axios = require("axios");
const fetch = require("node-fetch");
const { parseLottoLog } = require("./lotto_html_parser");

const { Octokit } = require("@octokit/core");

// === 수정된 부분: Organization 및 Repository 설정 ===
const owner = "team-jh";
const repo = "public-storage";
const committerName = "bloodstrawberry";
const userEmail = "vvv3334@hanmail.net";
const token = process.env.GH_TOKEN;
// ====================================================

const getSHA = async (octokit, path) => {
  const response = await octokit.request(
    `GET /repos/${owner}/${repo}/contents/${path}`
  );

  return response.data.sha;
};

const githubWrite = async (path, contents, commitMessage) => {
  const octokit = new Octokit({
    auth: token,
    request: {
      fetch: fetch,
    },
  });

  const fileSHA = await getSHA(octokit, path);

  const response = await octokit.request(
    `PUT /repos/${owner}/${repo}/contents/${path}`,
    {
      sha: fileSHA,
      message: commitMessage,
      committer: {
        name: committerName,
        email: userEmail,
      },

      // btoa : 바이너리 데이터를 base64로 인코딩
      // unescape(encodeURIComponent(())) <- 한글 처리
      content: btoa(unescape(encodeURIComponent(`${contents}`))),
    }
  );

  console.log("githubWrite", path, response.status);
  return response.status;
};

const getLottoNumber = async (drwNo) => {
  try {
    const response = await axios.get(
      `https://www.dhlottery.co.kr/smarPage`
      // `https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo=${drwNo}`
    );

    if (response.status !== 200) return undefined;

    return response.data;
  } catch (error) {
    console.error(`Error fetching round ${drwNo}:`, error.message);
    return undefined;
  }
};

const saveLog = async (drwNo) => {
    try {
    const response = await axios.get(
      `https://www.dhlottery.co.kr/smarPage`,
      { responseType: 'text' }
    );

    if (response.status !== 200) return undefined;

    const githubFilePath = "server/lotto_log.txt";
    await githubWrite(githubFilePath, response.data, `Update lotto_log.txt`); 

    return response.data;
  } catch (error) {
    console.error(`Error fetching round ${drwNo}:`, error.message);
    return undefined;
  }
}

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

function transformLottoItem(item) {
  return {
    drwNoDate: item.drwNoDate,
    No: [
      item.drwtNo1,
      item.drwtNo2,
      item.drwtNo3,
      item.drwtNo4,
      item.drwtNo5,
      item.drwtNo6
    ],
    bnusNo: item.bnusNo
  };
}

const updateLottoJson = async (targetDateStr) => {
  const filePath = path.join(__dirname, "../json/lottoNumber.json");

  console.log("filePath :", filePath);

  try {
    const data = fs.readFileSync(filePath, "utf-8");
    const lottoJson = JSON.parse(data);
    const lastEntry = lottoJson[lottoJson.length - 1];
    const lastDrwNo = lastEntry ? lastEntry.drwNo : 0;
    let isNewRoundAdded = false;
    
    const targetDate = targetDateStr ? new Date(targetDateStr) : new Date();
    const targetRound = getLottoRound(targetDate);

    console.log(`Last Round: ${lastDrwNo}, Target Round: ${targetRound} (Target Date: ${targetDateStr || 'Today'})`);

    console.log("saveLog start");
    const htmlContent = await saveLog(lastDrwNo);
    console.log("saveLog end");

    if (htmlContent) {      
        const parsedData = parseLottoLog(htmlContent);
        console.log({ parsedData });
        // drwNo1이 0이 아닌 경우에만 처리
        if (parsedData && parsedData.returnValue === 'success' && parsedData.drwtNo1 !== 0) {
             if (parsedData.drwNo > lastDrwNo) {
                 console.log(`New round ${parsedData.drwNo} found from HTML Parser. Appending.`);
                 lottoJson.push(parsedData);
                 isNewRoundAdded = true;
             } else {
                 const existingIndex = lottoJson.findIndex(item => item.drwNo === parsedData.drwNo);
                 if (existingIndex !== -1) {
                    lottoJson[existingIndex] = parsedData;
                    console.log(`Updated round ${parsedData.drwNo} from HTML Parser`);
                 }
             }
        }
    }

    // fs.writeFileSync(filePath, JSON.stringify(lottoJson, null, 4));

    const updatedJson = JSON.stringify(lottoJson, null, 2);
    const compactLottoJson = lottoJson.map(transformLottoItem);
    const updatedCompactJson = JSON.stringify(compactLottoJson, null, 2);
    
    const today = new Date();
    const formatted = today.toISOString().split("T")[0];

    const githubFilePath = "json/lottoNumber.json";
    const githubCompactFilePath = "json/compactLottoNumber.json";

    console.log("githubFilePath :", githubFilePath);
    const status = await githubWrite(githubFilePath, updatedJson, `${formatted} Update lottoNumber.json`); 
    
    console.log("githubCompactFilePath :", githubCompactFilePath);
    const compactStatus = await githubWrite(githubCompactFilePath, updatedCompactJson, `${formatted} Update compactLottoNumber.json`);

    if (((status === 200 || status === 201) || (compactStatus === 200 || compactStatus === 201)) && isNewRoundAdded) {
        if (process.env.GITHUB_OUTPUT) {
            fs.appendFileSync(process.env.GITHUB_OUTPUT, "status=success\n");
        }
    } 

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