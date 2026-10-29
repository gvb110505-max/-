# 로컬 워처 (baccarat_watcher.py)

화면의 바카라 로드맵을 계속 읽어서 `baccarat-bot.html` 에 보내주는 프로그램입니다.
브라우저 화면 공유가 막힌 환경에서도 동작하고, 창을 바꿔도 계속 읽습니다.

**이 프로그램은 화면을 읽기만 합니다.** 마우스·키보드를 조작하거나 베팅을 대신
누르는 기능은 들어 있지 않습니다. 베팅 버튼은 직접 누르셔야 합니다.

## 설치

파이썬 3.8 이상이 필요합니다.

```bash
pip install mss numpy
```

| 운영체제 | 비고 |
|---|---|
| Windows | 추가 설정 없음 |
| macOS | 처음 실행하면 **시스템 설정 → 개인정보 보호 및 보안 → 화면 기록** 에서 터미널(또는 iTerm)을 허용해야 합니다. 허용 후 터미널을 완전히 종료했다 다시 켜세요 |
| Linux | X11에서 동작합니다. Wayland면 `QT_QPA_PLATFORM=xcb` 등 X11 세션으로 로그인하세요 |

## 실행

```bash
python3 baccarat_watcher.py
```

1. 화면이 어두워지면 **로드맵 영역을 마우스로 끌어서** 지정합니다 (ESC 취소)
2. 지정한 영역은 `~/.baccarat_watcher.json` 에 저장되어 다음부터 자동으로 쓰입니다
3. 브라우저에서 **http://localhost:8787/** 를 엽니다 — 워처가 봇 페이지를 직접 서빙합니다
4. 봇 페이지에서 **🖥 로컬 워처 연결** 을 누릅니다

이제 새 결과가 나올 때마다 판독 → 패턴 분석 → 베팅 지시 → 정산 → 학습이 자동으로 돕니다.

## 옵션

```bash
python3 baccarat_watcher.py --rows 6 --cols 20    # 격자 크기 (기본 6행 20열)
python3 baccarat_watcher.py --interval 0.5        # 판독 주기(초)
python3 baccarat_watcher.py --port 9000           # HTTP 포트
python3 baccarat_watcher.py --monitor 2           # 두 번째 모니터
python3 baccarat_watcher.py --select              # 영역 다시 지정
python3 baccarat_watcher.py --selftest            # 화면 없이 판독기만 점검
```

## 판독이 잘 안 될 때

- **결과가 안 잡힘** → `--cols` 를 화면의 실제 열 수에 맞추세요. 영역을 격자에 딱 맞게 다시 지정(`--select`)하면 정확도가 크게 올라갑니다
- **엉뚱한 색으로 잡힘** → 사이트 테마가 많이 다른 경우입니다. `classify_cell()` 의 임계값(`r - g > 35` 등)을 조정하세요
- **판이 밀림** → 판독 주기를 줄이고(`--interval 0.5`), 로드맵이 가려지지 않게 두세요

## 봇 페이지만 따로 쓰려면

워처 없이도 `baccarat-bot.html` 은 혼자 동작합니다. 화면 공유, 사진 판독,
직접 입력(B/P/T 버튼) 중 편한 방법을 쓰시면 됩니다.
