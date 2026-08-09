---
trigger: always_on
---

# NewPaper 프로젝트 개발 규칙

## 1. 프론트엔드 (Frontend) 작성 지침
- **Vanilla Web Stack**: 외부 프레임워크 없이 `index.html`, `index.css`, `app.js` 구성을 유지합니다.
- **카테고리 구성**: `경제` 및 `글로벌` 2개 대표 필터 카테고리 유지.
- **뉴스 모달 구성**:
  1. AI 종합 요약 (`overview`)
  2. [랜덤 선택] 언론사 기사 본문 전체 (`featured_article`)
  3. 언론사별 보도 시작(`start_point`) & 강조점(`emphasis_point`) 비교
  4. 언론사별 기사 원본 링크

## 2. 뉴스 수집 및 AI 요약 (Collector & AI) 지침
- **네이버 뉴스 API**: `https://openapi.naver.com/v1/search/news.json`을 사용하여 `경제`, `글로벌` 뉴스를 수집합니다.
- **API 인증**: `NAVER_CLIENT_ID` 및 `NAVER_CLIENT_SECRET` 사용 (미설정 시 Fallback 수집기 작동).
- **데이터 보존**: `RETENTION_DAYS` (기본 30일) 보관 주기를 준수하여 오래된 뉴스를 자동 정리합니다.

## 3. GitHub MCP & 에이전트 개발 협업 수칙
- 코드 작성 후 반드시 `python scripts/collector.py` 실행 및 문법 오류 검증을 수행합니다.
- 커밋 시 의미 있는 개별 단위로 커밋 메시지를 작성합니다.
