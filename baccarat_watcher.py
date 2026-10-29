#!/usr/bin/env python3
"""
바카라 로드맵 화면 워처 (읽기 전용)

화면의 로드맵 영역을 계속 감시해서 뱅커/플레이어/타이 결과를 판독하고,
로컬 HTTP 서버로 내보냅니다. baccarat-bot.html 이 그 값을 받아
패턴 분석·베팅 지시·정산·학습을 이어서 처리합니다.

이 프로그램은 화면을 읽기만 합니다. 마우스·키보드를 조작하거나
베팅을 대신 누르는 기능은 없습니다.

필요한 것:  pip install mss numpy
실행:       python3 baccarat_watcher.py
            python3 baccarat_watcher.py --rows 6 --cols 20 --port 8787
            python3 baccarat_watcher.py --select      (영역 다시 지정)
            python3 baccarat_watcher.py --selftest    (화면 없이 판독기 점검)
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

try:
    import numpy as np
except ImportError:
    sys.exit("numpy 가 필요합니다:  pip install numpy")

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.expanduser("~"), ".baccarat_watcher.json")

# 공유 상태 (워처 스레드가 쓰고, HTTP 핸들러가 읽는다)
STATE = {"results": "", "count": 0, "updated": 0, "reads": 0, "error": None}
LOCK = threading.Lock()


# --------------------------------------------------------------------------
# 판독
# --------------------------------------------------------------------------
def classify_cell(cell):
    """셀 한 칸의 중앙부를 보고 B(뱅커·빨강) / P(플레이어·파랑) / T(타이·초록) / None"""
    h, w = cell.shape[:2]
    if h < 3 or w < 3:
        return None
    y0, y1 = int(h * 0.22), int(h * 0.78)
    x0, x1 = int(w * 0.22), int(w * 0.78)
    core = cell[y0:y1, x0:x1].astype(np.int16)
    if core.size == 0:
        return None

    r, g, b = core[:, :, 0], core[:, :, 1], core[:, :, 2]
    mx = core.max(axis=2)
    mn = core.min(axis=2)
    live = (mx >= 55) & ((mx - mn) >= 42)          # 어둡거나 무채색이면 빈 칸/격자선

    n_b = int((live & (r == mx) & (r - g > 35) & (r - b > 35)).sum())
    n_p = int((live & (b == mx) & (b - r > 30) & (b - g > 15)).sum())
    n_t = int((live & (g == mx) & (g - r > 28) & (g - b > 18)).sum())

    total = core.shape[0] * core.shape[1]
    best = max(n_b, n_p, n_t)
    if best < total * 0.10:
        return None
    return "T" if best == n_t else ("B" if best == n_b else "P")


def read_grid(img, rows, cols):
    """영역 이미지를 격자로 잘라 열 우선(위→아래)으로 결과 시퀀스를 만든다"""
    h, w = img.shape[:2]
    ch, cw = h / rows, w / cols
    out = []
    for c in range(cols):
        seen = False
        for r in range(rows):
            cell = img[int(r * ch):int((r + 1) * ch), int(c * cw):int((c + 1) * cw)]
            v = classify_cell(cell)
            if v:
                out.append(v)
                seen = True
            elif seen:
                break          # 열 중간 공백 = 그 열의 끝
        if not seen:
            break              # 빈 열 = 로드맵의 끝
    return "".join(out)


# --------------------------------------------------------------------------
# 영역 지정 (tkinter 오버레이 — 끌어서 사각형)
# --------------------------------------------------------------------------
def select_region():
    import tkinter as tk

    root = tk.Tk()
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    try:
        root.attributes("-fullscreen", True)
    except tk.TclError:
        root.geometry("%dx%d+0+0" % (root.winfo_screenwidth(), root.winfo_screenheight()))
    root.configure(bg="black")
    root.title("로드맵 영역을 끌어서 지정하세요 (ESC 취소)")

    cv = tk.Canvas(root, cursor="cross", bg="black", highlightthickness=0)
    cv.pack(fill="both", expand=True)
    cv.create_text(root.winfo_screenwidth() // 2, 40, fill="#45e08a",
                   font=("", 18), text="로드맵 영역을 마우스로 끌어서 지정하세요  ·  ESC 취소")

    box = {}
    rect = {"id": None}

    def down(e):
        box["x0"], box["y0"] = e.x_root, e.y_root
        if rect["id"]:
            cv.delete(rect["id"])
        rect["id"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#45e08a", width=2)
        box["cx"], box["cy"] = e.x, e.y

    def move(e):
        if rect["id"]:
            cv.coords(rect["id"], box["cx"], box["cy"], e.x, e.y)

    def up(e):
        box["x1"], box["y1"] = e.x_root, e.y_root
        root.quit()

    cv.bind("<ButtonPress-1>", down)
    cv.bind("<B1-Motion>", move)
    cv.bind("<ButtonRelease-1>", up)
    root.bind("<Escape>", lambda e: (box.clear(), root.quit()))
    root.mainloop()
    root.destroy()

    if "x1" not in box:
        return None
    left, top = min(box["x0"], box["x1"]), min(box["y0"], box["y1"])
    width, height = abs(box["x1"] - box["x0"]), abs(box["y1"] - box["y0"])
    if width < 20 or height < 20:
        return None
    return {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}


def load_region():
    try:
        with open(CONFIG) as f:
            r = json.load(f).get("region")
        if r and r.get("width", 0) > 0:
            return r
    except Exception:
        pass
    return None


def save_region(region):
    try:
        with open(CONFIG, "w") as f:
            json.dump({"region": region}, f)
    except Exception as e:
        print("설정 저장 실패:", e)


# --------------------------------------------------------------------------
# 감시 루프
# --------------------------------------------------------------------------
def watch(region, rows, cols, interval, monitor):
    try:
        import mss
    except ImportError:
        sys.exit("mss 가 필요합니다:  pip install mss")

    last_read, stable = None, 0
    print(f"감시 시작 — 영역 {region['width']}x{region['height']} @"
          f"({region['left']},{region['top']}) · 격자 {cols}열 {rows}행 · {interval}초 주기")
    print("종료하려면 Ctrl+C\n")

    with mss.mss() as sct:
        while True:
            try:
                shot = sct.grab({**region, "mon": monitor})
                img = np.array(shot)[:, :, :3][:, :, ::-1]      # BGRA → RGB
                seq = read_grid(img, rows, cols)

                # 같은 판독이 두 번 연속일 때만 확정 (프레임 노이즈 방지)
                if seq == last_read:
                    stable += 1
                else:
                    last_read, stable = seq, 1

                if stable == 2 and seq:
                    with LOCK:
                        prev = STATE["results"]
                        STATE["reads"] += 1
                        if seq != prev:
                            STATE["results"] = seq
                            STATE["count"] = len(seq)
                            STATE["updated"] = time.time()
                            STATE["error"] = None
                            if seq.startswith(prev) and prev:
                                added = seq[len(prev):]
                                print(f"[{time.strftime('%H:%M:%S')}] 새 결과 {added}  (총 {len(seq)}판)")
                            else:
                                print(f"[{time.strftime('%H:%M:%S')}] 판독 {len(seq)}판: {seq[-24:]}")
            except Exception as e:
                with LOCK:
                    STATE["error"] = str(e)
                print("판독 오류:", e)
            time.sleep(interval)


# --------------------------------------------------------------------------
# HTTP 서버 — 봇 페이지가 여기서 결과를 가져간다
# --------------------------------------------------------------------------
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def do_GET(self):
        if self.path.split("?")[0] == "/state":
            with LOCK:
                body = json.dumps(STATE).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/":
            self.path = "/baccarat-bot.html"
        super().do_GET()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *a):
        pass          # 접속 로그는 감시 출력만 가리므로 끈다


# --------------------------------------------------------------------------
def selftest():
    """화면 없이 판독기만 점검 — 합성 로드맵을 만들어 되읽는다"""
    rows, cols, size = 6, 8, 24
    seq = "BBPPPBTPBBBPPBPB"
    img = np.full((rows * size, cols * size, 3), 255, np.uint8)
    colors = {"B": (211, 47, 47), "P": (21, 101, 192), "T": (46, 125, 50)}
    r = c = 0
    for v in seq:
        cy, cx = r * size + size // 2, c * size + size // 2
        yy, xx = np.ogrid[:rows * size, :cols * size]
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= (size // 2 - 3) ** 2
        img[mask] = colors[v]
        r += 1
        if r == rows:
            r, c = 0, c + 1
    got = read_grid(img, rows, cols)
    ok = got == seq
    print(f"합성 로드맵 {len(seq)}판 → 판독 '{got}'")
    print("판독기 점검:", "통과" if ok else f"실패 (기대 '{seq}')")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="바카라 로드맵 화면 워처 (읽기 전용)")
    ap.add_argument("--rows", type=int, default=6, help="격자 행 수 (기본 6)")
    ap.add_argument("--cols", type=int, default=20, help="격자 열 수 (기본 20)")
    ap.add_argument("--interval", type=float, default=1.0, help="판독 주기(초)")
    ap.add_argument("--port", type=int, default=8787, help="HTTP 포트 (기본 8787)")
    ap.add_argument("--monitor", type=int, default=1, help="모니터 번호 (기본 1)")
    ap.add_argument("--select", action="store_true", help="영역을 다시 지정")
    ap.add_argument("--selftest", action="store_true", help="화면 없이 판독기 점검")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    region = None if args.select else load_region()
    if not region:
        print("로드맵 영역을 지정하세요 (화면이 어두워지면 끌어서 선택)")
        region = select_region()
        if not region:
            sys.exit("영역이 지정되지 않았습니다.")
        save_region(region)
        print("영역 저장됨:", CONFIG)

    threading.Thread(target=watch,
                     args=(region, args.rows, args.cols, args.interval, args.monitor),
                     daemon=True).start()

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"봇 페이지:  http://localhost:{args.port}/")
    print(f"상태 API :  http://localhost:{args.port}/state\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
