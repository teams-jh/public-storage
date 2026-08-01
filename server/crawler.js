const axios = require('axios');
const fs = require('fs');
const path = require('path');

// 대상 웹 페이지 변수 관련 설정
// 기본값으로 동행복권 사이트 설정
const targetUrl = 'https://www.dhlottery.co.kr/smarPage';
const logFilePath = path.join(__dirname, 'crawler.html');

async function crawlAndLog() {
  console.log(`Crawling target: ${targetUrl}`);

  try {
    // 웹 페이지 요청 (User-Agent 헤더 추가로 차단 방지)
    const response = await axios.get(targetUrl, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      },
    });

    console.log(response.data);

    // response.data를 crawler.html에 저장
    fs.writeFileSync(logFilePath, response.data);

    console.log('Successfully crawled and logged to crawler.html');
  } catch (error) {
    const errorMessage = error.message;
    fs.writeFileSync(logFilePath, `Error: ${errorMessage}`);

    console.error(`Failed to crawl: ${errorMessage}`);
  }
}



// 실행
crawlAndLog();
