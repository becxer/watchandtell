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

## 실행
```bash
python app.py
```

## POST 응답 처리 규칙
- JSON이면 `text`, `result`, `message`, `content`, `response` 키를 우선 탐색
- 없으면 JSON 전체를 문자열화
- 텍스트 응답이면 본문 그대로 사용

## 주의
- Windows에서 동작을 목표로 작성됨
- 자동 클릭/입력은 포커스된 앱에 입력되므로 좌표 설정 시 주의
- 필요시 pyautogui fail-safe를 원하는 방식으로 조정
