# 데이터 계약 (v1)

비공개 엔진(value-trader)이 매일 이 폴더로 내보내는 공개용 JSON의 형식이다.
에이전트는 이 파일들만 숫자 출처로 쓴다 (CLAUDE.md 절대 규칙 2).
필드를 바꾸면 이 문서도 같은 PR에서 고친다. v1은 2026-10-23~27 실제 export와 대조해 맞췄다.

## 위치
```
data/daily/YYYY-MM-DD/      날짜 = 미국 거래일 (뉴욕 기준)
  meta.json                 export됨
  positions.json            export됨
  trades.json               export됨
  pnl.json                  export됨
  flags.json                export됨
  market.json               아직 export되지 않음 (형식은 예정안)
  risk.json                 아직 export되지 않음 (형식은 예정안)
data/backtests/<slug>/      백테스트 결과 (운영자가 넣음)
```
`market.json`이 없는 날은 시황 글(market)을 쓰지 않는다(규칙 7). `risk.json`이 없는 날은 리스크 숫자를 쓰지 않는다.

## 공개 기준일 (CLAUDE.md 절대 규칙 9)
- 공개 전 데이터는 이 레포에 커밋하지 않는다. CI(`checks/data_guard.py`)가 PR에서 막는다.
- 공개 전 판정: `meta.json`에 `public_inception`이 없거나 `null`이거나, `notes`에 `pre_public`이 있거나, `date`가 `public_inception`보다 앞선다.
- 공개 전 기간의 글에는 수익률·손익·비중을 쓰지 않는다(`checks/content_lint.py`, compliance 검사 항목 10). 구축기는 운용 숫자 없이 쓸 수 있다.

## 공통 규칙
- 단위는 키 접미사로 표시한다.
  - `_pct`: 퍼센트 (1.23 = 1.23%)
  - `_pctp`: 퍼센트포인트
  - `_bp`: bp
  - `_x`: 배수
  - `_lvl`: 지수·환율·금리 등의 수준값
  - `_days`: 일수
- 금액·수량 필드는 넣지 않는다. 엔진이 내보내기 전에 제거한다.
- 값을 만들 수 없으면 `null`로 둔다. 짧은 기간으로 대신 계산하지 않는다.
- 시각은 ISO 8601 + 오프셋으로 쓴다 (`2026-10-21T16:05:00+09:00`).
- 배열 순서가 곧 리포트 표시 순서다.
- **가상 장부(vt shadow)는 공개 JSON에 넣지 않는다.** 가상 장부의 포지션·체결·손익은 어느 파일에도 들어가지 않고, `positions.sleeve`에도 shadow 값은 없다.

## meta.json
```json
{
  "date": "2026-11-02",
  "generated_at": "2026-11-03T06:30:00+09:00",
  "engine_version": "value-trader@abc1234",
  "markets": ["US"],
  "data_asof": { "US": "2026-11-02" },
  "stale": false,
  "public_inception": "2026-11-02",
  "notes": ["inception:2026-10-23"]
}
```
- `stale`: `data_asof`가 미국 시장의 직전 거래일보다 오래되면 true다. 미국 휴장일은 거래일로 세지 않는다.
- `public_inception`: 공개 기준일(`YYYY-MM-DD`). 이 날짜부터의 데이터만 공개한다. 정해지지 않았으면 `null`이다.
  초기 export(2026-10-23)에는 이 필드가 없다. 필드가 없으면 공개 전으로 본다.
- `notes`: 문자열 배열. 알려진 값:
  - `pre_public`: 공개 전 데이터. 커밋하지 않는다.
  - `inception:YYYY-MM-DD`: 운용 측정 시작일. `pnl.since_inception`의 기준일이다. 공개 기준일(`public_inception`)과 다르다.
  - `baseline:<방식>`: 손익 기준점을 잡은 방식. 실제 값은 `baseline:openings`(측정 시작일)이고, 그날 `pnl`의 수익률은 모두 `null`이다.
  - 그 밖의 문자열은 사람용 메모다. 에이전트는 숫자 출처로 쓰지 않는다.

## positions.json
```json
{
  "as_of": "2026-11-02T16:00:00-05:00",
  "rows": [
    {
      "symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "sleeve": "core", "currency": "USD",
      "weight_pct": 60.0, "target_weight_pct": 62.0, "drift_pctp": -2.0,
      "ret_since_entry_pct": 1.2, "manual": false
    },
    {
      "symbol": "ABC", "name": "Example Corp", "sleeve": "discovery", "currency": "USD",
      "weight_pct": 3.0, "target_weight_pct": 3.0, "drift_pctp": 0.0,
      "ret_since_entry_pct": -0.5, "manual": false
    },
    {
      "symbol": "XYZ", "name": "Example Holdings", "sleeve": "manual", "currency": "USD",
      "weight_pct": 5.0, "target_weight_pct": null, "drift_pctp": null,
      "ret_since_entry_pct": -10.0, "manual": true
    }
  ],
  "cash_weight_pct": 32.0
}
```
- `sleeve` 값 (엔진 설정 기준):
  - `core`: `targets`의 종목. 목표 비중으로 자동 운용하는 핵심 슬리브.
  - `discovery`: `discovery_sleeve`의 종목. 투자위원회 승인을 거쳐 편입하는 개별 종목 슬리브.
  - `manual`: `manual_symbols`의 종목. 운영자가 직접 관리하는 보유. 엔진이 목표 비중을 두지 않아 `target_weight_pct`·`drift_pctp`가 `null`이다.
  - `other`: `targets`·`discovery_sleeve`·`manual_symbols` 어디에도 없는 보유.
- 슬리브 소속은 이 `sleeve` 값으로 판단한다. `trades.reason_code`로 판단하지 않는다.
- `manual`: 운영자가 직접 관리하는 보유면 true. `sleeve: "manual"`과 같이 쓴다.
- `weight_pct`가 0인 행이 있을 수 있다(목표 비중은 있으나 아직 보유하지 않은 종목). 이때 `ret_since_entry_pct`는 `null`이다.

## trades.json
```json
{
  "rows": [
    { "symbol": "SPY", "side": "BUY", "weight_chg_pctp": 2.1, "reason_code": "core_rebalance", "plan_id": "P-20261102-01" }
  ]
}
```
- 체결이 없는 날은 `"rows": []`다.
- `reason_code`는 종목 분류가 아니라 **주문 출처** 기준이다. 슬리브 소속 여부는 `reason_code`가 아니라 `positions.json`의 `sleeve`로 판단한다.
  - 시스템 원장(orders)에 없는 주문: 항상 `manual_external`이다. 매매 차단 중에는 앱에서 낸 매매가 전부 여기에 들어간다(슬리브 종목 매수 포함).
  - 시스템 주문일 때만 종목에 따라 나뉜다.
    - `core_rebalance`: `targets` 종목
    - `sleeve_buy`: `discovery_sleeve` 종목
    - `manual`: 그 외 종목
- 새 코드를 쓰면 여기에 추가한다.

## pnl.json
```json
{
  "day":             { "total_pct": -0.84, "local_pct": -0.84, "fx_pct": 0.0, "benchmark": { "symbol": "SPY", "ret_pct": -0.60 }, "excess_pctp": -0.24 },
  "mtd":             { "total_pct": null },
  "ytd":             { "total_pct": null },
  "since_inception": { "total_pct": 1.20, "local_pct": 1.20, "fx_pct": 0.0, "benchmark": { "symbol": "SPY", "ret_pct": 1.50 }, "excess_pctp": -0.30 },
  "contrib": [
    { "symbol": "ABC", "contrib_bp": -45 },
    { "symbol": "SPY", "contrib_bp": -20 }
  ],
  "residual_bp": 1
}
```
- 기간: `day`, `mtd`, `ytd`, `since_inception`. 값을 만들 수 있으면 `total_pct`, `local_pct`, `fx_pct`, `benchmark`, `excess_pctp`를 모두 넣고, 없으면 `{ "total_pct": null }`만 둔다(예: 기간 시작일이 측정 시작일보다 앞선 `mtd`·`ytd`).
- 벤치마크는 `SPY`다.
- `since_inception`의 기준일은 `meta.notes`의 `inception:`이다.
- `contrib`: 종목별 기여도. 측정 시작일처럼 손익이 없는 날은 `[]`다.
- `residual_bp`: 기여도 합과 `day.total_pct`의 차이(현금, 비용, 반올림). 손익이 없는 날은 `null`이다. 에이전트가 직접 맞추지 않는다.

## risk.json (예정안, 아직 export되지 않음)
```json
{
  "limits": [
    { "id": "single_name_max", "metric": "단일종목 비중", "value_pct": 18.2, "limit_pct": 20.0, "usage_pct": 91.0, "status": "주의" }
  ],
  "concentration": { "top1_pct": 32.4, "top5_pct": 60.1, "hhi_x": 0.14 },
  "drawdown": { "current_pct": -4.2, "max_pct": -12.5 },
  "vol": { "realized_20d_pct": 18.3 },
  "beta": { "vs": "SPY", "beta_x": 1.12 },
  "var": { "method": "historical", "conf_pct": 95, "horizon_days": 1, "var_pct": -2.1 },
  "leveraged": [
    { "symbol": "XYZ", "leverage_x": 3, "weight_pct": 4.0, "vol_drag_20d_pct": -1.8 }
  ],
  "prev": null
}
```
- `status` 값: `정상`, `주의`, `위반`
- `prev`: 전일 같은 구조의 값. 첫날에는 `null`이다.

## market.json (예정안, 아직 export되지 않음)
```json
{
  "indices": [
    { "symbol": "SPX", "name": "S&P 500", "close_lvl": 5800.1, "chg_pct": 0.42, "from_high_pct": -3.1, "above_ma200": true }
  ],
  "rates": [
    { "name": "US10Y", "yield_pct": 4.12, "chg_bp": -3 }
  ],
  "fx": [
    { "pair": "USDKRW", "rate_lvl": 1385.2, "chg_pct": 0.15 }
  ],
  "commodities": [
    { "name": "WTI", "price_lvl": 71.3, "chg_pct": -1.2 }
  ],
  "sectors": [
    { "name": "반도체", "chg_pct": 1.8 }
  ]
}
```

## flags.json
```json
{
  "reconciliation": { "status": "OK", "detail": "" },
  "data_issues": [
    { "code": "corporate_action", "detail": "XYZ: share count ratio_x=0.25, cost preserved" }
  ]
}
```
- `reconciliation.status`: `OK` 또는 `MISMATCH`. 브로커 잔고와 원장의 대사 결과다.
- `MISMATCH`인 날 손익 글은 숫자가 확정치가 아니라고 밝혀야 한다 (compliance 검사 항목 9).
- `data_issues[].code` 값:
  - `price_missing`: 종가 누락. `detail`에 대체 방법(예: 전일가 사용)을 적는다.
  - `corporate_action`: 분할·병합 같은 기업 행위. `detail`에 비율(`ratio_x`)과 원가 처리를 적는다. 수량은 넣지 않는다.
- 문제가 없는 날은 `"data_issues": []`다.

## 위 예시 숫자
이 문서의 숫자와 종목(ABC, XYZ 등)은 형식 예시일 뿐 실제 값이 아니다. 에이전트는 이 문서의 숫자를 인용하지 않는다.
