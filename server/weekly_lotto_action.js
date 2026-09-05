const fs = require("fs");
const path = require("path");
const axios = require("axios");
const fetch = require("node-fetch");
const { parseLottoLog } = require("./lotto_html_parser");

let Octokit;
try {
  Octokit = require("@octokit/rest").Octokit;
} catch (e) {
  Octokit = require("@octokit/core").Octokit;
}

// === 수정된 부분: Organization 및 Repository 설정 ===
const [envOwner, envRepo] = (process.env.GITHUB_REPOSITORY || "teams-jh/public-storage").split("/");
const owner = envOwner;
const repo = envRepo;
const committerName = "bloodstrawberry";
const userEmail = "vvv3334@hanmail.net";
const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || process.env.MY_TOKEN;
// ====================================================

async function getSHA(octokit, path) {
  try {
    const response = await octokit.request(
      `GET /repos/${owner}/${repo}/contents/${path}`
    );
    return response.data.sha;
  } catch (error) {
    if (error.status === 404) {
      return undefined;
    }
    throw error;
  }
}

async function getRemoteOrLocalJson(octokit, repoPath, localPath) {
  let remoteData = null;
  let sha = undefined;

  if (octokit && token) {
    try {
      const response = await octokit.request(
        `GET /repos/${owner}/${repo}/contents/${repoPath}`
      );
      if (response.data && response.data.content) {
        const decoded = Buffer.from(response.data.content, "base64").toString("utf-8");
        remoteData = JSON.parse(decoded);
        sha = response.data.sha;
        console.log(`Successfully fetched ${repoPath} from GitHub (SHA: ${sha})`);
      }
    } catch (error) {
      console.warn(`Could not fetch ${repoPath} from GitHub, falling back to local file:`, error.message);
    }
  }

  if (Array.isArray(remoteData) && remoteData.length > 0) {
    return { data: remoteData, sha };
  }

  if (fs.existsSync(localPath)) {
    try {
      const fileContent = fs.readFileSync(localPath, "utf-8");
      return { data: JSON.parse(fileContent), sha };
    } catch (e) {
      console.error(`Error reading local ${localPath}:`, e.message);
    }
  }

  return { data: [], sha };
}

const githubWrite = async (path, contents, commitMessage, existingSha) => {
  if (!token) {
    console.error("GitHub token is not defined. Please check GH_TOKEN or GITHUB_TOKEN environment variable.");
    return undefined;
  }

  const octokit = new Octokit({
    auth: token,
    request: {
      fetch: fetch,
    },
  });

  const fileSHA = existingSha || (await getSHA(octokit, path));

  const payload = {
    message: commitMessage,
    committer: {
      name: committerName,
      email: userEmail,
    },
    // Node.js 표준 Base64 인코딩 (한글 및 유니코드 처리 지원)
    content: Buffer.from(`${contents}`, "utf-8").toString("base64"),
  };

  if (fileSHA) {
    payload.sha = fileSHA;
  }

  const response = await octokit.request(
    `PUT /repos/${owner}/${repo}/contents/${path}`,
    payload
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
  const compactFilePath = path.join(__dirname, "../json/compactLottoNumber.json");
  const githubFilePath = "json/lottoNumber.json";
  const githubCompactFilePath = "json/compactLottoNumber.json";

  console.log("filePath :", filePath);

  let octokit = null;
  if (token) {
    octokit = new Octokit({
      auth: token,
      request: {
        fetch: fetch,
      },
    });
  }

  try {
    // 1. GitHub 원격 저장소 최신 파일 우선 조회 (로컬 파일 불일치로 인한 덮어쓰기 방지)
    const { data: lottoJson, sha: lottoSha } = await getRemoteOrLocalJson(octokit, githubFilePath, filePath);
    let { data: compactLottoJson, sha: compactSha } = await getRemoteOrLocalJson(octokit, githubCompactFilePath, compactFilePath);

    const lastEntry = lottoJson[lottoJson.length - 1];
    const lastDrwNo = lastEntry ? lastEntry.drwNo : 0;
    let isNewRoundAdded = false;

    if (!Array.isArray(compactLottoJson) || compactLottoJson.length === 0) {
      compactLottoJson = lottoJson.map(transformLottoItem);
    }
    
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
             const compactItem = transformLottoItem(parsedData);

             // 1. lottoJson 처리: 기존 회차면 정보 업데이트, 새 회차면 append
             const existingLottoIndex = lottoJson.findIndex(item => item.drwNo === parsedData.drwNo);
             if (existingLottoIndex !== -1) {
                 lottoJson[existingLottoIndex] = parsedData;
                 console.log(`Updated round ${parsedData.drwNo} in lottoJson`);
             } else {
                 console.log(`New round ${parsedData.drwNo} found. Appending to lottoJson.`);
                 lottoJson.push(parsedData);
                 lottoJson.sort((a, b) => a.drwNo - b.drwNo);
                 isNewRoundAdded = true;
             }

             // 2. compactLottoJson 처리: 날짜(drwNoDate) 기준 중복 체크
             // 동일 날짜가 이미 있으면 업데이트, 없는 날짜면 항상 끝에 추가(push)
             const existingCompactIndex = compactLottoJson.findIndex(item => item.drwNoDate === compactItem.drwNoDate);
             if (existingCompactIndex !== -1) {
                 compactLottoJson[existingCompactIndex] = compactItem;
                 console.log(`Updated date ${compactItem.drwNoDate} in compactLottoJson`);
             } else {
                 console.log(`New date ${compactItem.drwNoDate} found. Appending to compactLottoJson.`);
                 compactLottoJson.push(compactItem);
             }

             // 날짜 기준 오름차순 정렬 보장
             compactLottoJson.sort((a, b) => new Date(a.drwNoDate) - new Date(b.drwNoDate));
        }
    }

    const updatedJson = JSON.stringify(lottoJson, null, 2);
    const updatedCompactJson = JSON.stringify(compactLottoJson, null, 2);

    // 로컬 파일 쓰기
    fs.writeFileSync(filePath, updatedJson, "utf-8");
    fs.writeFileSync(compactFilePath, updatedCompactJson, "utf-8");
    
    const today = new Date();
    const formatted = today.toISOString().split("T")[0];

    console.log("githubFilePath :", githubFilePath);
    const status = await githubWrite(githubFilePath, updatedJson, `${formatted} Update lottoNumber.json`, lottoSha); 
    
    console.log("githubCompactFilePath :", githubCompactFilePath);
    const compactStatus = await githubWrite(githubCompactFilePath, updatedCompactJson, `${formatted} Update compactLottoNumber.json`, compactSha);

    if (((status === 200 || status === 201) || (compactStatus === 200 || compactStatus === 201)) && isNewRoundAdded) {
        if (process.env.GITHUB_OUTPUT) {
            fs.appendFileSync(process.env.GITHUB_OUTPUT, "status=success\n");
        }
    } 

    console.log("Update complete.");
  } catch (error) {
    console.error("Error updating lotto json:", error);
    process.exitCode = 1;
  }
};

// Execute if run directly
if (require.main === module) {
    // Check for command line argument or use default (undefined -> Today)
    const argDate = process.argv[2];
    updateLottoJson(argDate);
}