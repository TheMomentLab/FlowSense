# Commit Convention

## 형식

```
<type>: <description>
```

한 줄로 작성. 영어 소문자 시작, 마침표 없음, 72자 이내.

## Type

| type | 용도 | 예시 |
|------|------|------|
| `feat` | 새 기능 추가 | `feat: add stock comparison view` |
| `fix` | 버그 수정 | `fix: resolve chatbot SSE connection drop` |
| `docs` | 문서 변경 | `docs: update API reference in README` |
| `refactor` | 기능 변경 없는 코드 개선 | `refactor: extract LLM retry logic to util` |
| `style` | 포맷팅, 세미콜론 등 (동작 변경 없음) | `style: fix indentation in ai_analyzer` |
| `chore` | 빌드, 설정, 의존성 | `chore: upgrade pykrx to 1.3.0` |
| `test` | 테스트 추가/수정 | `test: add unit tests for stock_search` |
| `perf` | 성능 개선 | `perf: cache sector data to reduce API calls` |

## 규칙

1. type은 위 목록만 사용
2. description은 영어로 작성 (코드베이스 일관성)
3. "what"이 아닌 "why" 중심으로 작성
4. 본문이 필요하면 빈 줄 후 추가 (선택)

```
fix: prevent duplicate news cache updates

Background scheduler and manual trigger were racing.
Added a lock to ensure only one update runs at a time.
```

5. Breaking change는 본문에 `BREAKING CHANGE:` 표기

```
refactor: change judge API response structure

BREAKING CHANGE: checklist items now use "passed" instead of "pass"
```

## 하지 말 것

- `fix: 버그 수정` -- 한국어 description 사용 금지
- `Fix: resolve issue` -- 대문자 시작 금지
- `feat: add stock comparison view.` -- 마침표 금지
- `update code` -- type 없이 커밋 금지
- `feat: add A, fix B, refactor C` -- 한 커밋에 여러 type 혼합 금지
