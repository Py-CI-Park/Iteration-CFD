# Studio API와 OpenCodex 연결 검토

## 직접 호출과 코드 변경 여부

| 경로 | 이번 검증 | 코드 변경 판단 |
|---|---|---|
| Studio HTTP API | 브라우저와 같은 루프백 Studio에 `GET /api/health`, `POST /api/datasets/open`, `GET /api/datasets/:id`로 실제 격자 조회. | 로컬 조회·읽기에 코드 수정 불필요. AI 모델이나 API 키도 필요 없다. 이 경로는 GPU 해석 실행과 별개다. |
| Studio → Anthropic 호환 로컬 endpoint | 현 Studio의 실제 Anthropic 어댑터를 격리된 127.0.0.1 응답 서버로 연결. `POST /v1/messages?beta=true`와 SSE 도구 요청 파싱을 검증. 도구 자체는 실행하지 않았다. | SDK가 `ANTHROPIC_BASE_URL`을 읽으므로 프로토콜이 호환되면 환경 설정만으로 가능. |
| Studio → 실제 OpenCodex | 설치된 `ocx --version`은 2.97.0. 확인 시 기본 포트 10100은 듣고 있지 않았다. 게이트웨이 설정·계정·키는 수정하지 않았고 실모델 요청은 보내지 않았다. | 게이트웨이의 Anthropic 호환 endpoint가 Studio의 요청·응답을 처리하는 경우에만 무수정 연결 가능. 실제 연결은 미검증. |
| Studio UI에 OpenCodex를 별도 공급자로 등록 | 현 설정은 `anthropic`·`zai`·`mock` 경로. 일반 공급자/URL 등록 UI나 Responses 전용 경로는 확인되지 않았다. | 별도 공급자·URL·인증을 UI에서 관리하려면 서버 설정과 UI 확장 필요. Responses 전용 endpoint를 사용하려면 별도 어댑터가 필요. |

[OpenCodex 공식 문서](https://github.com/lidge-jun/opencodex#connect-your-tool)는 Anthropic 호환 기본 URL을 `http://localhost:10100`로 안내한다. **OpenAI 호환 URL의 `/v1`을 Anthropic 기본 URL에 붙이지 않는다.** Studio의 SDK가 이미 `/v1/messages`를 붙이는 것을 이번 시험에서 관찰했다.

### 설정만으로 확인할 때

별도 Studio 서버 프로세스에 아래 값을 설정한다. 여기서 인증값은 예시 문자열이 아니라 해당 로컬 게이트웨이가 요구하는 자격 증명을 비밀 저장소로 주입한다. 기존 데모 서버·Codex 자체의 전역 환경은 바꾸지 않는다.

```text
CFD_LLM=anthropic
ANTHROPIC_BASE_URL=http://127.0.0.1:10100
CFD_MODEL=<게이트웨이가 라우팅하는 모델 ID>
ANTHROPIC_API_KEY 또는 ANTHROPIC_AUTH_TOKEN=<게이트웨이 인증 계약에 맞춰 주입>
```

실제 Studio 어댑터는 베타 헤더, adaptive thinking, fallbacks, cache_control, tool calls와 SSE를 사용한다. 따라서 **헬스 응답만으로 호환을 선언하지 않는다.** 합성 문장, 제한된 도구 이름, tool input JSON, 결과 회신과 오류 동작을 검증한 뒤 작업용으로 사용한다. 거부가 나오면 게이트웨이의 요청 변환 옵션을 먼저 확인하고, 필요할 때만 호환 모드를 추가한다. `CFD_LLM_BASE_URL`은 현재 z.ai 설정 경로에서 읽는 값이다.

재현: `gui/node_modules/.bin/tsx.cmd research/a321-quality/probe_anthropic_base.mjs`. [로컬 시험 기록](evidence/anthropic-loopback-20261107.json)에는 합성 자격 증명 사용 여부만 남겼다. 실제 자격 증명·항공기 데이터·외부 제공자 요청은 기록하거나 전송하지 않았다.

## 진단 데이터를 Studio에 표시할 때

현재 `gui/server/src/formats/vtu.ts`는 appended raw polyhedron VTU를 대상으로 한다. 이번 ASCII triangle VTU는 읽지 못해 기존 polyMesh로 fallback했고 요청한 진단 필드는 없었다. 따라서 데이터 조회 API가 작동하는 것과 임의의 데이터 형식을 화면에 그릴 수 있다는 것은 별개다. 삼각 표면 진단을 그대로 표시하려면 지원 형식 변환이나 reader 확장이 필요하다. 실패한 색상 화면은 합격 증거에서 제외했다.

실제 AI에 업무 도구를 허용하기 전에는 기존 approval 경로와 호출 범위도 확인해야 한다. 환경 URL을 바꿨다는 사실만으로 보고서의 GPU HOLD가 서버 실행 경로에서 강제된다고 가정하지 않는다. 이번에는 기존 Studio를 mock으로 유지했고, 읽기 API와 격리 fixture만 사용했다.
