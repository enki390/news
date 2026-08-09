---
trigger: always_on
---

# NewPaper 프로젝트 개발 규칙

## 1. 프론트엔드 (Frontend) 작성 지침
- **Vanilla Web Stack**: 외부 프레임워크 없이 `index.html`, `index.css`, `app.js` 구성을 유지합니다.
- **디자인 시스템**: `index.css`에 정의된 CSS 변수(Color palette, spacing, font)를 활용하여 일관된 디자인을 유지합니다.
- **예외 처리**: `app.js`에서 데이터 로딩 실패 시 사용자에게 친권적이고 깔끔한 에러 UI를 노출합니다.

## 2. 뉴스 수집 및 AI 요약 (Collector & AI) 지침
- **네트워크 안정성**: RSS 수집 시 타임아웃 처리 및 웹 스크래핑 예외 처리를 철저히 진행합니다.
- **AI 요약 Fallback**: Gemini API 오류 발생 시 전체 프로세스가 중단되지 않도록 원본 기사의 본문 요약/Snippet을 대체 텍스트로 사용하는 방어 로직을 유지합니다.
- **데이터 보존**: `RETENTION_DAYS` (기본 30일) 보관 주기를 준수하여 오래된 뉴스를 적절히 아카이빙합니다.

## 3. GitHub MCP & 에이전트 개발 협업 수칙
- 코드 작성 후 반드시 문법 오류 검증 및 작동 테스트를 거칩니다.
- 커밋 시 의미 있는 개별 단위로 커밋 메시지를 작성합니다.
