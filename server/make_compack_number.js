const fs = require('fs');

/**
 * 단일 로또 데이터를 원하는 형식으로 변환하는 함수
 * @param {Object} item - 원본 로또 데이터 객체
 * @returns {Object} 변환된 로또 데이터 객체
 */
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

/**
 * 전체 JSON 데이터를 읽어 변환 후 새 파일로 저장하는 메인 함수
 * @param {string} inputFilePath - 원본 JSON 파일 경로
 * @param {string} outputFilePath - 저장할 JSON 파일 경로
 */
function convertLottoJsonFile(inputFilePath, outputFilePath) {
  try {
    // 1. 원본 JSON 파일 읽기
    const rawData = fs.readFileSync(inputFilePath, 'utf8');
    const lottoArray = JSON.parse(rawData);

    // 2. 전체 배열을 순회하며 transformLottoItem 함수 적용
    const transformedArray = lottoArray.map(transformLottoItem);

    // 3. 변환된 데이터를 보기 좋게(들여쓰기 2칸) 문자열로 변환하여 파일 저장
    fs.writeFileSync(outputFilePath, JSON.stringify(transformedArray, null, 2), 'utf8');
    console.log(`성공적으로 변환되었습니다! 저장된 파일: ${outputFilePath}`);
    
  } catch (error) {
    console.error("데이터 변환 중 오류가 발생했습니다:", error.message);
  }
}

// ==========================================
// 실행 영역 (Node.js 환경에서 직접 실행 시)
// ==========================================

const path = require('path');

// 실제 파일명에 맞게 아래 경로를 수정하여 사용하세요.
const INPUT_FILE = path.join(__dirname, '../json/lottoNumber.json');   // 원본 JSON 파일명
const OUTPUT_FILE = path.join(__dirname, '../json/compactLottoNumber.json'); // 생성될 JSON 파일명

// 파일이 존재할 경우에만 실행되도록 간단한 체크 (테스트용)
if (fs.existsSync(INPUT_FILE)) {
  convertLottoJsonFile(INPUT_FILE, OUTPUT_FILE);
} else {
  console.log(`알림: ${INPUT_FILE} 파일이 없어 변환을 실행하지 않았습니다.`);
}

// 다른 파일에서 재사용할 수 있도록 export
module.exports = {
  transformLottoItem,
  convertLottoJsonFile
};