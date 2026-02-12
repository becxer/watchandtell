import json
import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from tkinter import BOTH, LEFT, Button, Entry, Frame, Label, StringVar, Tk, Toplevel, messagebox

import pyautogui
import requests
from PIL import ImageGrab


pyautogui.FAILSAFE = False
TEMP_IMAGE_PATH = "temp.jpg"


@dataclass
class AppState:
    region: tuple[int, int, int, int] | None = None
    click_point: tuple[int, int] | None = None


class RegionSelector:
    def __init__(self, root: Tk, on_select, on_cancel):
        self.root = root
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.start_x = 0
        self.start_y = 0
        self.rect_id = None

        self.overlay = Toplevel(root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.2)
        self.overlay.configure(bg="black")
        self.overlay.overrideredirect(True)

        from tkinter import Canvas

        self.canvas = Canvas(self.overlay, bg="black", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.overlay.bind("<Escape>", lambda _e: self.cancel())

    def _start(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=3,
        )

    def _drag(self, event):
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))

        if right - left < 5 or bottom - top < 5:
            messagebox.showwarning("영역 선택", "영역이 너무 작습니다. 다시 선택해주세요.")
            return

        self.destroy()
        self.on_select((left, top, right, bottom))

    def cancel(self):
        self.destroy()
        self.on_cancel()

    def destroy(self):
        if self.overlay.winfo_exists():
            self.overlay.destroy()


class PointSelector:
    def __init__(self, root: Tk, on_select, on_cancel):
        self.root = root
        self.on_select = on_select
        self.on_cancel = on_cancel

        self.overlay = Toplevel(root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.01)
        self.overlay.configure(bg="white")
        self.overlay.overrideredirect(True)

        self.overlay.bind("<Button-1>", self._click)
        self.overlay.bind("<Escape>", lambda _e: self.cancel())

    def _click(self, event):
        x = self.overlay.winfo_pointerx()
        y = self.overlay.winfo_pointery()
        self.destroy()
        self.on_select((x, y))

    def cancel(self):
        self.destroy()
        self.on_cancel()

    def destroy(self):
        if self.overlay.winfo_exists():
            self.overlay.destroy()




class RegionOutline:
    def __init__(self, root: Tk):
        self.root = root
        self.overlay: Toplevel | None = None

    def show(self, region: tuple[int, int, int, int]):
        self.hide()

        left, top, right, bottom = region
        width = max(1, right - left)
        height = max(1, bottom - top)

        overlay = Toplevel(self.root)
        overlay.attributes("-topmost", True)
        overlay.overrideredirect(True)

        transparent_key = "#00ff00"
        overlay.configure(bg=transparent_key)
        try:
            overlay.wm_attributes("-transparentcolor", transparent_key)
        except Exception:
            pass

        overlay.geometry(f"{width}x{height}+{left}+{top}")

        from tkinter import Canvas

        canvas = Canvas(
            overlay,
            bg=transparent_key,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(fill=BOTH, expand=True)
        canvas.create_rectangle(1, 1, width - 2, height - 2, outline="red", width=3)

        self.overlay = overlay

    def hide(self):
        if self.overlay and self.overlay.winfo_exists():
            self.overlay.destroy()
        self.overlay = None

class WatchAndTellApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Watch & Tell")
        self.root.geometry("860x450")
        self.root.resizable(False, False)

        self.state = AppState()
        self.region_outline = RegionOutline(root)
        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.status_queue: Queue[str] = Queue()

        self.url_var = StringVar()
        self.prompt_var = StringVar()
        self.interval_var = StringVar(value="5")
        self.region_var = StringVar(value="미선택")
        self.click_var = StringVar(value="미선택")
        self.status_var = StringVar(value="대기 중")
        self.last_response_var = StringVar(value="(없음)")
        self.output_test_var = StringVar(value="테스트 입력")

        self._build_ui()
        self.root.after(100, self._drain_status_queue)

    def _build_ui(self):
        container = Frame(self.root, padx=16, pady=16)
        container.pack(fill=BOTH, expand=True)

        row1 = Frame(container)
        row1.pack(fill=BOTH, pady=6)
        Label(row1, text="감시 영역:", width=16, anchor="w").pack(side=LEFT)
        Button(row1, text="영역 선택", command=self.select_region, width=14).pack(side=LEFT)
        Button(row1, text="선택 취소", command=self.clear_region, width=14).pack(side=LEFT, padx=8)
        Label(row1, textvariable=self.region_var, anchor="w").pack(side=LEFT, padx=8)

        row2 = Frame(container)
        row2.pack(fill=BOTH, pady=6)
        Label(row2, text="POST URL:", width=16, anchor="w").pack(side=LEFT)
        Entry(row2, textvariable=self.url_var).pack(side=LEFT, fill=BOTH, expand=True)

        row3 = Frame(container)
        row3.pack(fill=BOTH, pady=6)
        Label(row3, text="프롬프트:", width=16, anchor="w").pack(side=LEFT)
        Entry(row3, textvariable=self.prompt_var).pack(side=LEFT, fill=BOTH, expand=True)

        row4 = Frame(container)
        row4.pack(fill=BOTH, pady=6)
        Label(row4, text="출력 클릭 좌표:", width=16, anchor="w").pack(side=LEFT)
        Button(row4, text="좌표 선택", command=self.select_click_point, width=14).pack(side=LEFT)
        Button(row4, text="선택 취소", command=self.clear_click_point, width=14).pack(side=LEFT, padx=8)
        Label(row4, textvariable=self.click_var, anchor="w").pack(side=LEFT, padx=8)

        row5 = Frame(container)
        row5.pack(fill=BOTH, pady=6)
        Label(row5, text="Interval(초):", width=16, anchor="w").pack(side=LEFT)
        Entry(row5, textvariable=self.interval_var, width=10).pack(side=LEFT)
        Button(row5, text="Run", command=self.start, width=12).pack(side=LEFT, padx=8)
        Button(row5, text="Stop", command=self.stop, width=12).pack(side=LEFT)

        row6 = Frame(container)
        row6.pack(fill=BOTH, pady=6)
        Label(row6, text="단건 테스트:", width=16, anchor="w").pack(side=LEFT)
        Button(row6, text="캡처 테스트", command=self.test_capture, width=12).pack(side=LEFT)
        Button(row6, text="POST 테스트", command=self.test_post, width=12).pack(side=LEFT, padx=8)
        Button(row6, text="출력 테스트", command=self.test_output, width=12).pack(side=LEFT)

        row7 = Frame(container)
        row7.pack(fill=BOTH, pady=6)
        Label(row7, text="출력 테스트 문구:", width=16, anchor="w").pack(side=LEFT)
        Entry(row7, textvariable=self.output_test_var).pack(side=LEFT, fill=BOTH, expand=True)

        row8 = Frame(container)
        row8.pack(fill=BOTH, pady=6)
        Label(row8, text="마지막 응답:", width=16, anchor="w").pack(side=LEFT)
        Label(row8, textvariable=self.last_response_var, anchor="w", fg="#444").pack(side=LEFT, fill=BOTH, expand=True)

        row9 = Frame(container)
        row9.pack(fill=BOTH, pady=12)
        Label(row9, text="상태:", width=16, anchor="w").pack(side=LEFT)
        Label(row9, textvariable=self.status_var, anchor="w", fg="#0b6").pack(side=LEFT)

    def select_region(self):
        self.status_var.set("드래그로 영역을 선택하세요. ESC: 취소")
        RegionSelector(self.root, self._set_region, lambda: self.status_var.set("영역 선택 취소됨"))

    def _set_region(self, region):
        self.state.region = region
        self.region_outline.show(region)
        self.region_var.set(f"{region}")
        self.status_var.set("감시 영역 설정됨 (빨간 테두리 유지)")

    def clear_region(self):
        self.state.region = None
        self.region_outline.hide()
        self.region_var.set("미선택")
        self.status_var.set("감시 영역 선택 취소됨")

    def select_click_point(self):
        self.status_var.set("출력 좌표를 클릭하세요. ESC: 취소")
        PointSelector(self.root, self._set_click, lambda: self.status_var.set("좌표 선택 취소됨"))

    def _set_click(self, point):
        self.state.click_point = point
        self.click_var.set(f"{point}")
        self.status_var.set("출력 좌표 설정됨")

    def clear_click_point(self):
        self.state.click_point = None
        self.click_var.set("미선택")
        self.status_var.set("출력 좌표 선택 취소됨")

    def _validate_region(self) -> bool:
        if not self.state.region:
            messagebox.showerror("오류", "감시 영역을 먼저 선택하세요.")
            return False
        return True

    def _validate_click_point(self) -> bool:
        if not self.state.click_point:
            messagebox.showerror("오류", "출력 클릭 좌표를 먼저 선택하세요.")
            return False
        return True

    def _validate_url(self) -> bool:
        if not self.url_var.get().strip():
            messagebox.showerror("오류", "POST URL을 입력하세요.")
            return False
        return True

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("실행 중", "이미 실행 중입니다.")
            return

        if not self._validate_region() or not self._validate_click_point() or not self._validate_url():
            return

        try:
            interval = float(self.interval_var.get().strip())
            if interval <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("오류", "Interval은 0보다 큰 숫자여야 합니다.")
            return

        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, args=(interval,), daemon=True)
        self.worker_thread.start()
        self.status_var.set("실행 시작")

    def stop(self):
        self.stop_event.set()
        self.status_var.set("중지 요청됨")

    def test_capture(self):
        if not self._validate_region():
            return
        self._capture_region_to_file(TEMP_IMAGE_PATH)
        self.status_var.set(f"캡처 테스트 성공: {TEMP_IMAGE_PATH}")

    def test_post(self):
        if not self._validate_region() or not self._validate_url():
            return
        self._capture_region_to_file(TEMP_IMAGE_PATH)
        response_text = self._post_image_and_prompt(TEMP_IMAGE_PATH).strip()
        self.last_response_var.set(response_text if response_text else "(빈 응답)")
        self.status_var.set("POST 테스트 성공")

    def test_output(self):
        if not self._validate_click_point():
            return

        text = self.output_test_var.get().strip()
        if not text:
            candidate = self.last_response_var.get().strip()
            if candidate and candidate != "(없음)":
                text = candidate

        if not text:
            messagebox.showerror("오류", "출력 테스트 문구 또는 마지막 응답이 필요합니다.")
            return

        confirmed = messagebox.askyesno(
            "출력 테스트",
            "3초 후 선택된 좌표를 클릭하고 입력합니다.\n원하면 지금 대상 창으로 포커스를 옮겨주세요.",
        )
        if not confirmed:
            self.status_var.set("출력 테스트 취소됨")
            return

        self.status_var.set("출력 테스트 3초 대기...")
        self.root.update_idletasks()
        time.sleep(3)
        self._click_and_type(text)
        self.status_var.set("출력 테스트 성공")

    def _drain_status_queue(self):
        try:
            while True:
                msg = self.status_queue.get_nowait()
                self.status_var.set(msg)
        except Empty:
            pass
        self.root.after(100, self._drain_status_queue)

    def _capture_region_to_file(self, image_path: str):
        image = ImageGrab.grab(bbox=self.state.region)
        image.save(image_path, "JPEG")

    def _post_image_and_prompt(self, image_path: str) -> str:
        url = self.url_var.get().strip()
        prompt = self.prompt_var.get()

        with open(image_path, "rb") as f:
            files = {"image": ("temp.jpg", f, "image/jpeg")}
            data = {"prompt": prompt}
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()

        ctype = response.headers.get("content-type", "")
        if "application/json" in ctype:
            payload = response.json()
            if isinstance(payload, dict):
                for key in ("text", "result", "message", "content", "response"):
                    if key in payload:
                        return str(payload[key])
            return json.dumps(payload, ensure_ascii=False)

        return response.text

    def _click_and_type(self, text: str):
        click_point = self.state.click_point
        if not click_point:
            raise ValueError("출력 클릭 좌표가 없습니다.")
        pyautogui.click(click_point[0], click_point[1])
        time.sleep(0.2)
        if text:
            pyautogui.write(text, interval=0.01)
        pyautogui.press("enter")

    def _worker_loop(self, interval: float):
        while not self.stop_event.is_set():
            try:
                region = self.state.region
                click_point = self.state.click_point
                if not region or not click_point:
                    self.status_queue.put("영역/좌표가 없어 중지합니다")
                    return

                self._capture_region_to_file(TEMP_IMAGE_PATH)
                self.status_queue.put("캡처 완료 -> 요청 전송 중")

                text = self._post_image_and_prompt(TEMP_IMAGE_PATH).strip()
                self.last_response_var.set(text if text else "(빈 응답)")
                self.status_queue.put("응답 수신 -> 입력 중")

                self._click_and_type(text)
                self.status_queue.put(f"완료, {interval}초 대기")
            except Exception as exc:
                self.status_queue.put(f"오류: {exc}")

            finished = self.stop_event.wait(interval)
            if finished:
                break

        self.status_queue.put("중지됨")


def main():
    root = Tk()
    app = WatchAndTellApp(root)

    def on_close():
        app.stop()
        app.region_outline.hide()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
