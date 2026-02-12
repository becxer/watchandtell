# PR Merge Conflict 해결 가이드

GitHub에서 `This branch has conflicts that must be resolved`가 뜰 때, 아래 순서로 해결할 수 있습니다.

## 1) 최신 대상 브랜치 가져오기
```bash
git fetch origin
```

## 2) 작업 브랜치에서 대상 브랜치로 rebase
대상이 `main`이면:
```bash
git checkout work
git rebase origin/main
```

## 3) 충돌 파일 확인
```bash
git status
```

## 4) 충돌 마커(`<<<<<<<`, `=======`, `>>>>>>>`) 정리
파일을 열어 원하는 내용으로 합친 뒤 저장합니다.

## 5) 해결 완료 처리
```bash
git add README.md app.py requirements.txt
```

## 6) rebase 계속 진행
```bash
git rebase --continue
```

충돌이 여러 번 나면 3~6을 반복합니다.

## 7) 원격 브랜치 갱신
rebase 후에는 force-with-lease로 push:
```bash
git push --force-with-lease origin work
```

---

## merge 방식으로 해결하고 싶을 때(대안)
```bash
git checkout work
git merge origin/main
# 충돌 해결 후
git add README.md app.py requirements.txt
git commit
git push origin work
```

---

## 팁
- 충돌 마커가 남아 있는지 빠르게 확인:
```bash
rg -n "^(<<<<<<<|=======|>>>>>>>)" README.md app.py requirements.txt
```
- VS Code를 쓰면 `Resolve in Merge Editor`로 시각적으로 정리하기 쉽습니다.
