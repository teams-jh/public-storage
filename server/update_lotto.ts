import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  COMPACT_LOTTO_NUMBER_JSON_PATH,
  LOTTO_NUMBER_JSON_PATH,
  LOTTO_REQUEST_MAX_RETRIES,
  LOTTO_REQUEST_RETRY_DELAY_MS,
  LOTTO_REQUEST_TIMEOUT_MS,
  LOTTO_REQUEST_USER_AGENT,
  LOTTO_RESULT_API_URL,
} from "../src/constants/global_constants.ts";

type CompactLottoItem = { drwNoDate: string; No: number[]; bnusNo: number };

type LottoItem = {
  totSellamnt: number;
  returnValue: "success";
  drwNoDate: string;
  firstWinamnt: number;
  drwtNo6: number;
  drwtNo4: number;
  firstPrzwnerCo: number;
  drwtNo5: number;
  bnusNo: number;
  firstAccumamnt: number;
  drwNo: number;
  drwtNo2: number;
  drwtNo3: number;
  drwtNo1: number;
};

type ApiLottoItem = {
  ltEpsd: number;
  ltRflYmd: string;
  tm1WnNo: number;
  tm2WnNo: number;
  tm3WnNo: number;
  tm4WnNo: number;
  tm5WnNo: number;
  tm6WnNo: number;
  bnsWnNo: number;
  rnk1WnNope: number;
  rnk1WnAmt: number;
  rnk1SumWnAmt: number;
  wholEpsdSumNtslAmt: number;
};

type ApiResponse = { data?: { list?: ApiLottoItem[] } };
type UpdateOptions = { compactPath: string; fullPath: string; dryRun?: boolean; fetchImpl?: typeof fetch };
type UpdateResult = { addedRounds: number[]; changed: boolean };

function readJsonArray<T>(filePath: string): T[] {
  const parsed: unknown = JSON.parse(fs.readFileSync(filePath, "utf8"));

  if (!Array.isArray(parsed)) {
    throw new Error(`${filePath} 파일의 최상위 값이 배열이 아니에요.`);
  }

  return parsed as T[];
}

function formatDrawDate(value: string): string {
  if (!/^\d{8}$/.test(value)) {
    throw new Error(`추첨일 형식이 올바르지 않아요: ${value}`);
  }

  return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`;
}

function isValidBall(value: number): boolean {
  return Number.isInteger(value) && value >= 1 && value <= 45;
}

function validateApiItem(item: ApiLottoItem): void {
  const numbers = [item.tm1WnNo, item.tm2WnNo, item.tm3WnNo, item.tm4WnNo, item.tm5WnNo, item.tm6WnNo];

  if (!Number.isInteger(item.ltEpsd) || item.ltEpsd < 1) {
    throw new Error(`회차 번호가 올바르지 않아요: ${item.ltEpsd}`);
  }

  if (numbers.some((number) => !isValidBall(number)) || new Set(numbers).size !== numbers.length) {
    throw new Error(`${item.ltEpsd}회 당첨 번호가 올바르지 않아요.`);
  }

  if (!isValidBall(item.bnsWnNo) || numbers.includes(item.bnsWnNo)) {
    throw new Error(`${item.ltEpsd}회 보너스 번호가 올바르지 않아요.`);
  }

  formatDrawDate(item.ltRflYmd);
}

function toCompactItem(item: ApiLottoItem | LottoItem): CompactLottoItem {
  if ("ltEpsd" in item) {
    return {
      drwNoDate: formatDrawDate(item.ltRflYmd),
      No: [item.tm1WnNo, item.tm2WnNo, item.tm3WnNo, item.tm4WnNo, item.tm5WnNo, item.tm6WnNo],
      bnusNo: item.bnsWnNo,
    };
  }

  return {
    drwNoDate: item.drwNoDate,
    No: [item.drwtNo1, item.drwtNo2, item.drwtNo3, item.drwtNo4, item.drwtNo5, item.drwtNo6],
    bnusNo: item.bnusNo,
  };
}

function toFullItem(item: ApiLottoItem): LottoItem {
  return {
    totSellamnt: item.wholEpsdSumNtslAmt,
    returnValue: "success",
    drwNoDate: formatDrawDate(item.ltRflYmd),
    firstWinamnt: item.rnk1WnAmt,
    drwtNo6: item.tm6WnNo,
    drwtNo4: item.tm4WnNo,
    firstPrzwnerCo: item.rnk1WnNope,
    drwtNo5: item.tm5WnNo,
    bnusNo: item.bnsWnNo,
    firstAccumamnt: item.rnk1SumWnAmt,
    drwNo: item.ltEpsd,
    drwtNo2: item.tm2WnNo,
    drwtNo3: item.tm3WnNo,
    drwtNo1: item.tm1WnNo,
  };
}

function wait(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function fetchNewRounds(lastRound: number, fetchImpl: typeof fetch = fetch): Promise<ApiLottoItem[]> {
  const url = new URL(LOTTO_RESULT_API_URL);
  url.searchParams.set("srchDir", "latest");
  url.searchParams.set("srchCursorLtEpsd", String(lastRound));
  let lastError: unknown;

  for (let attempt = 1; attempt <= LOTTO_REQUEST_MAX_RETRIES; attempt += 1) {
    try {
      const response = await fetchImpl(url, {
        headers: { "User-Agent": LOTTO_REQUEST_USER_AGENT },
        signal: AbortSignal.timeout(LOTTO_REQUEST_TIMEOUT_MS),
      });

      if (!response.ok) {
        throw new Error(`동행복권 API가 HTTP ${response.status}로 응답했어요.`);
      }

      const payload = (await response.json()) as ApiResponse;
      const list = payload.data?.list ?? [];
      list.forEach(validateApiItem);

      return list
        .filter((item) => item.ltEpsd > lastRound)
        .sort((first, second) => first.ltEpsd - second.ltEpsd);
    } catch (error) {
      lastError = error;

      if (attempt < LOTTO_REQUEST_MAX_RETRIES) {
        await wait(LOTTO_REQUEST_RETRY_DELAY_MS * attempt);
      }
    }
  }

  throw new Error("동행복권에서 최신 번호를 가져오지 못했어요.", { cause: lastError });
}

function writeJson(filePath: string, value: unknown): void {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export async function updateLottoNumbers(options: UpdateOptions): Promise<UpdateResult> {
  const fullItems = readJsonArray<LottoItem>(options.fullPath);
  const compactItems = readJsonArray<CompactLottoItem>(options.compactPath);
  const originalCompactLength = compactItems.length;

  if (fullItems.length === 0) {
    throw new Error("전체 로또 데이터가 비어 있어 기준 회차를 찾을 수 없어요.");
  }

  const lastRound = Math.max(...fullItems.map((item) => item.drwNo));
  const compactDates = new Set(compactItems.map((item) => item.drwNoDate));
  const lastCompactDate = compactItems.reduce(
    (latest, item) => (item.drwNoDate > latest ? item.drwNoDate : latest),
    "",
  );

  for (const item of fullItems) {
    if (item.drwNoDate > lastCompactDate && !compactDates.has(item.drwNoDate)) {
      compactItems.push(toCompactItem(item));
      compactDates.add(item.drwNoDate);
    }
  }

  const apiItems = await fetchNewRounds(lastRound, options.fetchImpl);
  const fullRounds = new Set(fullItems.map((item) => item.drwNo));

  for (const item of apiItems) {
    const compactItem = toCompactItem(item);

    if (!fullRounds.has(item.ltEpsd)) {
      fullItems.push(toFullItem(item));
      fullRounds.add(item.ltEpsd);
    }

    if (!compactDates.has(compactItem.drwNoDate)) {
      compactItems.push(compactItem);
      compactDates.add(compactItem.drwNoDate);
    }
  }

  fullItems.sort((first, second) => first.drwNo - second.drwNo);
  compactItems.sort((first, second) => first.drwNoDate.localeCompare(second.drwNoDate));
  const changed = apiItems.length > 0 || compactItems.length !== originalCompactLength;

  if (changed && !options.dryRun) {
    writeJson(options.fullPath, fullItems);
    writeJson(options.compactPath, compactItems);
  }

  return { addedRounds: apiItems.map((item) => item.ltEpsd), changed };
}

async function main(): Promise<void> {
  const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const dryRun = process.argv.includes("--dry-run");
  const result = await updateLottoNumbers({
    fullPath: path.join(repositoryRoot, LOTTO_NUMBER_JSON_PATH),
    compactPath: path.join(repositoryRoot, COMPACT_LOTTO_NUMBER_JSON_PATH),
    dryRun,
  });

  if (!result.changed) {
    console.log("이미 최신 로또 번호가 들어 있어요.");
    return;
  }

  const rounds = result.addedRounds.length > 0 ? result.addedRounds.join(", ") : "기존 전체 데이터";
  console.log(`${rounds} 기준으로 간소화 로또 데이터를 ${dryRun ? "갱신할 수 있어요" : "갱신했어요"}.`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
