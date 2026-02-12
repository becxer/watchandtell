# Watch & Tell (Windows Python GUI)

요구사항을 반영한 단일(Flat) GUI 자동화 툴입니다.

## 기능
- 감시 영역 선택: `영역 선택` 버튼으로 드래그해 사각형 지정 (ESC 취소, 선택 취소 버튼 제공)
- URL + 프롬프트 입력
- 출력 클릭 좌표 선택: `좌표 선택` 버튼으로 클릭 위치 저장 (ESC 취소, 선택 취소 버튼 제공)
- Interval + Run/Stop
  - Run 중에는 지정 영역을 interval마다 캡처하여 `temp.jpg` 저장
  - `image=temp.jpg`, `prompt=<입력값>` 형태로 POST 요청
  - 응답 문자열을 지정 좌표 클릭 후 자동 입력
  - Stop 누를 때까지 반복

## 설치
```bash
pip install -r requirements.txt
```

### Windows에서 `액세스가 거부되었습니다`가 뜰 때
관리자 권한이 없는 PowerShell/CMD에서 전역 설치를 시도하면 자주 발생합니다. 아래 순서대로 진행해 주세요.

1) 먼저 pip 자체를 최신화
```bash
python -m pip install --upgrade pip
```

2) 현재 사용자 계정에만 설치 (`--user`)
```bash
python -m pip install --user -r requirements.txt
```

3) 그래도 안 되면 가상환경(권장)
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

4) 회사 PC 정책으로 막힌 경우
- PowerShell/CMD를 "관리자 권한으로 실행" 후 다시 시도
- 백신/보안 프로그램이 `python.exe`/`pip.exe` 쓰기를 막는지 확인

참고: `pip` 대신 항상 `python -m pip`를 사용하면 PATH 충돌을 줄일 수 있습니다.

## 실행
```bash
python app.py
```

## 단건 테스트(권장)
Run 전에 아래 3가지를 각각 버튼으로 점검할 수 있습니다.

1. **캡처 테스트**
   - 감시 영역을 먼저 선택한 뒤 `캡처 테스트`를 누르면 `temp.jpg`가 저장됩니다.

2. **POST 테스트**
   - 감시 영역 + URL + 프롬프트를 설정한 뒤 `POST 테스트`를 누르면
     캡처 후 바로 POST를 1회 보냅니다.
   - 성공하면 `마지막 응답` 라벨에 서버 응답 문자열이 표시됩니다.

3. **출력 테스트**
   - 출력 클릭 좌표를 설정한 뒤 `출력 테스트`를 누르면
     3초 대기 후 선택 좌표를 클릭하고 테스트 문구를 입력합니다.
   - `출력 테스트 문구`가 비어 있으면 `마지막 응답` 내용을 사용합니다.

> 이 단건 테스트로 **캡처 / POST / 클릭+타이핑**이 각각 정상인지 먼저 확인한 뒤 Run을 시작하세요.

## POST 응답 처리 규칙
- JSON이면 `text`, `result`, `message`, `content`, `response` 키를 우선 탐색
- 없으면 JSON 전체를 문자열화
- 텍스트 응답이면 본문 그대로 사용

## 주의
- Windows에서 동작을 목표로 작성됨
- 자동 클릭/입력은 포커스된 앱에 입력되므로 좌표 설정 시 주의
- 필요시 pyautogui fail-safe를 원하는 방식으로 조정
