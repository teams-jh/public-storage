import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { updateLottoNumbers } from "./update_lotto.ts";

function createApiResponse(round: number, date: string): Response {
  return Response.json({
    data: {
      list: [{
        ltEpsd: round,
        ltRflYmd: date,
        tm1WnNo: 7,
        tm2WnNo: 13,
        tm3WnNo: 16,
        tm4WnNo: 23,
        tm5WnNo: 24,
        tm6WnNo: 43,
        bnsWnNo: 9,
        rnk1WnNope: 18,
        rnk1WnAmt: 1_628_391_980,
        rnk1SumWnAmt: 29_311_055_640,
        wholEpsdSumNtslAmt: 121_918_085_000,
      }],
    },
  });
}

function createFixture(): { directory: string; fullPath: string; compactPath: string } {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "lotto-update-"));
  const fullPath = path.join(directory, "lottoNumber.json");
  const compactPath = path.join(directory, "compactLottoNumber.json");
  const fullItem = {
    totSellamnt: 1,
    returnValue: "success",
    drwNoDate: "2026-09-05",
    firstWinamnt: 1,
    drwtNo6: 44,
    drwtNo4: 20,
    firstPrzwnerCo: 1,
    drwtNo5: 31,
    bnusNo: 27,
    firstAccumamnt: 1,
    drwNo: 1240,
    drwtNo2: 13,
    drwtNo3: 19,
    drwtNo1: 11,
  };
  const compactItem = {
    drwNoDate: "2026-09-05",
    No: [11, 13, 19, 20, 31, 44],
    bnusNo: 27,
  };

  fs.writeFileSync(fullPath, JSON.stringify([fullItem]), "utf8");
  fs.writeFileSync(compactPath, JSON.stringify([compactItem]), "utf8");
  return { directory, fullPath, compactPath };
}

test("새 회차를 전체 파일과 간소화 파일에 한 번만 추가해요", async (context) => {
  const fixture = createFixture();
  context.after(() => fs.rmSync(fixture.directory, { recursive: true, force: true }));

  const result = await updateLottoNumbers({
    ...fixture,
    fetchImpl: async () => createApiResponse(1241, "20260912"),
  });
  const fullItems = JSON.parse(fs.readFileSync(fixture.fullPath, "utf8"));
  const compactItems = JSON.parse(fs.readFileSync(fixture.compactPath, "utf8"));

  assert.deepEqual(result.addedRounds, [1241]);
  assert.equal(fullItems.at(-1).drwNo, 1241);
  assert.deepEqual(compactItems.at(-1), {
    drwNoDate: "2026-09-12",
    No: [7, 13, 16, 23, 24, 43],
    bnusNo: 9,
  });

  const secondResult = await updateLottoNumbers({
    ...fixture,
    fetchImpl: async () => createApiResponse(1241, "20260912"),
  });
  const secondCompactItems = JSON.parse(fs.readFileSync(fixture.compactPath, "utf8"));

  assert.equal(secondResult.changed, false);
  assert.equal(secondCompactItems.length, compactItems.length);
});

test("드라이런에서는 갱신 가능 여부만 확인하고 파일을 바꾸지 않아요", async (context) => {
  const fixture = createFixture();
  context.after(() => fs.rmSync(fixture.directory, { recursive: true, force: true }));
  const before = fs.readFileSync(fixture.compactPath, "utf8");

  const result = await updateLottoNumbers({
    ...fixture,
    dryRun: true,
    fetchImpl: async () => createApiResponse(1241, "20260912"),
  });

  assert.equal(result.changed, true);
  assert.equal(fs.readFileSync(fixture.compactPath, "utf8"), before);
});
