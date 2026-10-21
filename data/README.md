# 데이터 계약 (v0 초안)

비공개 엔진(value-trader)이 매일 이 폴더로 내보내는 공개용 JSON의 형식이다.
에이전트는 이 파일들만 숫자 출처로 쓴다 (CLAUDE.md 절대 규칙 2).
1단계(백오피스)에서 엔진 쪽 export를 만들면서 확정한다. 필드를 바꾸면 이 문서도 같은 PR에서 고친다.

## 위치
```
data/daily/YYYY-MM-DD/      날짜 = 미국 거래일 (뉴욕 기준)
  meta.json
  market.json
  positions.json
  trades.json
  pnl.json
  risk.json
  flags.json
data/backtests/<slug>/      백테스트 결과 (운영자가 넣음)
```

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

## meta.json
```json
{
  "date": "2026-10-21",
  "generated_at": "2026-10-22T06:30:00+09:00",
  "engine_version": "value-trader@abc1234",
  "markets": ["US"],
  "data_asof": { "US": "2026-10-21" },
  "stale": false,
  "notes": []
}
```
`stale`: `data_asof`가 미국 시장의 직전 거래일보다 오래되면 true다. 미국 휴장일은 거래일로 세지 않는다.

## market.json
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

## positions.json
```json
{
  "as_of": "2026-10-21T16:00:00-04:00",
  "rows": [
    {
      "symbol": "QQQ", "name": "Invesco QQQ Trust", "sleeve": "core", "currency": "USD",
      "weight_pct": 32.4, "target_weight_pct": 32.0, "drift_pctp": 0.4,
      "ret_since_entry_pct": 5.4, "manual": false
    }
  ],
  "cash_weight_pct": 67.6
}
```
`manual`: 운영자가 직접 관리하는 보유 종목이면 true. 자동 운용 대상과 구분하는 값이다.

## trades.json
```json
{
  "rows": [
    { "symbol": "QQQ", "side": "BUY", "weight_chg_pctp": 2.1, "reason_code": "rebalance_band", "plan_id": "P-20261021-01" }
  ]
}
```
`reason_code` 사전: `rebalance_band`, `scheduled_contribution`, `manual`, `exit`, `adopt`. 새 코드를 쓰면 여기에 추가한다.

## pnl.json
```json
{
  "day":             { "total_pct": -0.84, "local_pct": -0.70, "fx_pct": -0.14, "benchmark": { "symbol": "QQQ", "ret_pct": -0.60 }, "excess_pctp": -0.24 },
  "mtd":             { "total_pct": 1.20,  "local_pct": 1.05,  "fx_pct": 0.15,  "benchmark": { "symbol": "QQQ", "ret_pct": 1.50 },  "excess_pctp": -0.30 },
  "ytd":             { "total_pct": null },
  "since_inception": { "total_pct": null },
  "contrib": [
    { "symbol": "SOXL", "contrib_bp": -45 },
    { "symbol": "QQQ",  "contrib_bp": -20 }
  ],
  "residual_bp": 2
}
```
`residual_bp`: 기여도 합과 `day.total_pct`의 차이(현금, 비용, 반올림). 에이전트가 직접 맞추지 않는다.

## risk.json
```json
{
  "limits": [
    { "id": "single_name_max", "metric": "단일종목 비중", "value_pct": 18.2, "limit_pct": 20.0, "usage_pct": 91.0, "status": "주의" }
  ],
  "concentration": { "top1_pct": 32.4, "top5_pct": 60.1, "hhi_x": 0.14 },
  "drawdown": { "current_pct": -4.2, "max_pct": -12.5 },
  "vol": { "realized_20d_pct": 18.3 },
  "beta": { "vs": "SPX", "beta_x": 1.12 },
  "var": { "method": "historical", "conf_pct": 95, "horizon_days": 1, "var_pct": -2.1 },
  "leveraged": [
    { "symbol": "SOXL", "leverage_x": 3, "weight_pct": 4.0, "vol_drag_20d_pct": -1.8 }
  ],
  "prev": null
}
```
- `status` 값: `정상`, `주의`, `위반`
- `prev`: 전일 같은 구조의 값. 첫날에는 `null`이다.

## flags.json
```json
{
  "reconciliation": { "status": "OK", "detail": "" },
  "data_issues": [
    { "code": "price_missing", "detail": "1종목 종가 누락, 전일가 사용" }
  ]
}
```
- `reconciliation.status`: `OK` 또는 `MISMATCH`. 브로커 잔고와 원장의 대사 결과다.
- `MISMATCH`인 날 손익 글은 숫자가 확정치가 아니라고 밝혀야 한다 (compliance 검사 항목 9).

## 위 예시 숫자
이 문서의 숫자는 형식 예시일 뿐 실제 값이 아니다. 에이전트는 이 문서의 숫자를 인용하지 않는다.
