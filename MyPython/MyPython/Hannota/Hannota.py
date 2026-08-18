import colorsys
import math
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import pygame
except ImportError:
    pygame = None


MAX_DISKS = 20
FPS = 60


def ask_disk_count():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        while True:
            value = simpledialog.askinteger(
                "汉诺塔动画演示",
                f"请输入原层数（1-{MAX_DISKS}）：",
                parent=root,
                minvalue=1,
                maxvalue=MAX_DISKS,
            )
            if value is None:
                return None
            if 1 <= value <= MAX_DISKS:
                return value
            messagebox.showwarning(
                "输入不正确",
                f"层数必须在 1 到 {MAX_DISKS} 之间。",
                parent=root,
            )
    finally:
        root.destroy()


def hanoi_moves(n, source, auxiliary, target):
    if n == 0:
        return
    yield from hanoi_moves(n - 1, source, target, auxiliary)
    yield source, target
    yield from hanoi_moves(n - 1, auxiliary, source, target)


def make_font(size, bold=False):
    font_names = ("msyhbd.ttc", "simhei.ttf", "msyh.ttc", "simsun.ttc", "arialbd.ttf", "arial.ttf")
    fonts_dir = Path("C:/Windows/Fonts")

    for font_name in font_names:
        if not bold and font_name in {"msyhbd.ttc", "arialbd.ttf"}:
            continue
        font_path = fonts_dir / font_name
        if font_path.exists():
            return pygame.font.Font(str(font_path), size)

    return pygame.font.Font(None, size)


def disk_color(size, total):
    hue = (size * 0.61803398875) % 1.0
    saturation = 0.70 + (size % 3) * 0.07
    value = 0.86 + (size % 2) * 0.08
    red, green, blue = colorsys.hsv_to_rgb(hue, min(saturation, 0.86), value)
    return int(red * 255), int(green * 255), int(blue * 255)


class HanoiAnimation:
    def __init__(self, disk_count):
        self.disk_count = disk_count
        self.total_moves = (1 << disk_count) - 1
        self.completed_moves = 0
        self.pegs = [list(range(disk_count, 0, -1)), [], []]
        self.moves = hanoi_moves(disk_count, 0, 1, 2)
        self.active_move = None
        self.active_elapsed = 0.0
        self.last_moved_disk = None
        self.finished = False

        pygame.init()
        pygame.display.set_caption("汉诺塔动画演示")
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.width, self.height = self.screen.get_size()
        self.configure_layout()
        self.configure_speed()

        self.title_font = make_font(max(24, min(44, self.height // 25)), bold=True)
        self.text_font = make_font(max(18, min(30, self.height // 42)))
        self.small_font = make_font(max(15, min(24, self.height // 55)))

        self.background = (17, 21, 28)
        self.foreground = (236, 242, 248)
        self.muted = (160, 171, 186)
        self.rod_color = (116, 128, 145)
        self.base_color = (68, 78, 93)
        self.progress_back = (45, 54, 68)
        self.progress_fill = (65, 195, 143)

    def configure_layout(self):
        self.bottom_height = max(94, min(150, int(self.height * 0.15)))
        self.top_margin = max(58, int(self.height * 0.07))
        self.side_margin = max(50, int(self.width * 0.08))
        self.tower_bottom = self.height - self.bottom_height - max(34, self.height // 32)

        usable_height = self.tower_bottom - self.top_margin - 34
        self.disk_height = max(4, min(34, usable_height // (self.disk_count + 2)))
        stack_height = self.disk_height * self.disk_count
        self.base_y = min(self.tower_bottom, self.top_margin + stack_height + self.disk_height * 2)
        self.peg_top = self.base_y - stack_height - self.disk_height * 2

        usable_width = self.width - self.side_margin * 2
        spacing = usable_width / 2
        self.peg_x = [
            self.side_margin,
            self.side_margin + spacing,
            self.side_margin + spacing * 2,
        ]
        max_by_spacing = spacing * 0.72
        self.max_disk_width = max(56, min(self.width * 0.26, max_by_spacing))
        self.min_disk_width = max(24, min(self.max_disk_width * 0.28, self.max_disk_width - 12))

    def configure_speed(self):
        if self.total_moves <= 1023:
            self.mode = "smooth"
            self.move_duration = max(0.03, min(0.50, 9.0 / self.total_moves))
            self.moves_per_frame = 1
        else:
            self.mode = "batch"
            target_seconds = min(30.0, max(10.0, self.disk_count * 1.4))
            self.moves_per_frame = max(1, math.ceil(self.total_moves / (target_seconds * FPS)))
            self.move_duration = 0.0

    def disk_width(self, size):
        if self.disk_count == 1:
            return self.max_disk_width * 0.68
        ratio = (size - 1) / (self.disk_count - 1)
        return self.min_disk_width + ratio * (self.max_disk_width - self.min_disk_width)

    def disk_center(self, size, peg_index, level):
        return (
            self.peg_x[peg_index],
            self.base_y - (level + 0.5) * self.disk_height,
        )

    def start_next_move(self):
        try:
            source, target = next(self.moves)
        except StopIteration:
            self.finished = True
            return False

        disk = self.pegs[source].pop()
        start_level = len(self.pegs[source])
        end_level = len(self.pegs[target])
        start = self.disk_center(disk, source, start_level)
        end = self.disk_center(disk, target, end_level)
        lift_y = max(self.peg_top + self.disk_height * 0.8, min(start[1], end[1]) - self.disk_height * 2.2)

        self.active_move = {
            "disk": disk,
            "target": target,
            "start": start,
            "end": end,
            "lift_y": lift_y,
        }
        self.active_elapsed = 0.0
        return True

    def finish_active_move(self):
        disk = self.active_move["disk"]
        target = self.active_move["target"]
        self.pegs[target].append(disk)
        self.last_moved_disk = disk
        self.completed_moves += 1
        self.active_move = None
        if self.completed_moves >= self.total_moves:
            self.finished = True

    def active_disk_position(self):
        move = self.active_move
        if not move:
            return None

        progress = min(1.0, self.active_elapsed / self.move_duration)
        sx, sy = move["start"]
        ex, ey = move["end"]
        lift_y = move["lift_y"]

        if progress < 0.33:
            t = progress / 0.33
            return sx, sy + (lift_y - sy) * t
        if progress < 0.66:
            t = (progress - 0.33) / 0.33
            return sx + (ex - sx) * t, lift_y
        t = (progress - 0.66) / 0.34
        return ex, lift_y + (ey - lift_y) * t

    def apply_batch_moves(self):
        for _ in range(self.moves_per_frame):
            if self.completed_moves >= self.total_moves:
                self.finished = True
                return
            try:
                source, target = next(self.moves)
            except StopIteration:
                self.finished = True
                return
            disk = self.pegs[source].pop()
            self.pegs[target].append(disk)
            self.last_moved_disk = disk
            self.completed_moves += 1

    def update(self, dt):
        if self.finished:
            return

        if self.mode == "batch":
            self.apply_batch_moves()
            return

        if self.active_move is None and not self.start_next_move():
            return

        self.active_elapsed += dt
        if self.active_elapsed >= self.move_duration:
            self.finish_active_move()

    def draw_text_center(self, text, font, y, color):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, y))
        self.screen.blit(surface, rect)

    def draw_disk(self, size, center, highlight=False):
        disk_w = int(self.disk_width(size))
        disk_h = max(4, int(self.disk_height * 0.82))
        x = int(center[0] - disk_w / 2)
        y = int(center[1] - disk_h / 2)
        color = disk_color(size, self.disk_count)
        edge = tuple(max(0, channel - 46) for channel in color)
        radius = max(2, min(10, disk_h // 2))

        if highlight:
            glow = pygame.Rect(x - 4, y - 4, disk_w + 8, disk_h + 8)
            pygame.draw.rect(self.screen, (246, 240, 172), glow, border_radius=radius + 4)

        rect = pygame.Rect(x, y, disk_w, disk_h)
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)
        pygame.draw.rect(self.screen, edge, rect, width=2, border_radius=radius)

    def draw_towers(self):
        base_rect = pygame.Rect(
            int(self.side_margin * 0.55),
            int(self.base_y),
            int(self.width - self.side_margin * 1.1),
            max(8, self.disk_height // 3),
        )
        pygame.draw.rect(self.screen, self.base_color, base_rect, border_radius=4)

        rod_width = max(6, int(self.width * 0.006))
        for index, x in enumerate(self.peg_x):
            rod = pygame.Rect(
                int(x - rod_width / 2),
                int(self.peg_top),
                rod_width,
                int(self.base_y - self.peg_top),
            )
            pygame.draw.rect(self.screen, self.rod_color, rod, border_radius=rod_width // 2)
            label = self.small_font.render(chr(ord("A") + index), True, self.muted)
            self.screen.blit(label, label.get_rect(center=(x, self.base_y + self.disk_height * 1.2)))

        active_disk = self.active_move["disk"] if self.active_move else None
        for peg_index, stack in enumerate(self.pegs):
            for level, disk in enumerate(stack):
                self.draw_disk(
                    disk,
                    self.disk_center(disk, peg_index, level),
                    highlight=(self.mode == "batch" and disk == self.last_moved_disk),
                )

        if active_disk:
            self.draw_disk(active_disk, self.active_disk_position(), highlight=True)

    def draw_progress(self):
        percent = self.completed_moves / self.total_moves if self.total_moves else 1.0
        panel_top = self.height - self.bottom_height
        bar_w = int(min(820, self.width * 0.62))
        bar_h = max(16, min(24, self.height // 45))
        bar_x = int((self.width - bar_w) / 2)
        bar_y = int(panel_top + self.bottom_height * 0.48)

        status = f"完成度 {percent * 100:6.2f}%"
        steps = f"步骤 {self.completed_moves:,} / {self.total_moves:,}"
        if self.finished:
            status = "完成度 100.00%"

        self.draw_text_center(status, self.text_font, int(panel_top + self.bottom_height * 0.25), self.foreground)

        back_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        fill_rect = pygame.Rect(bar_x, bar_y, int(bar_w * percent), bar_h)
        pygame.draw.rect(self.screen, self.progress_back, back_rect, border_radius=bar_h // 2)
        pygame.draw.rect(self.screen, self.progress_fill, fill_rect, border_radius=bar_h // 2)
        pygame.draw.rect(self.screen, (126, 139, 158), back_rect, width=2, border_radius=bar_h // 2)

        self.draw_text_center(steps, self.small_font, int(panel_top + self.bottom_height * 0.75), self.muted)

    def draw(self):
        self.screen.fill(self.background)
        title = f"{self.disk_count} 层汉诺塔动画演示"
        self.draw_text_center(title, self.title_font, max(28, self.top_margin // 2), self.foreground)
        self.draw_towers()
        self.draw_progress()
        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            self.update(dt)
            self.draw()


def main():
    if pygame is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("缺少 pygame", "请先安装 pygame：pip install pygame")
        root.destroy()
        return 1

    disk_count = ask_disk_count()
    if disk_count is None:
        return 0

    app = HanoiAnimation(disk_count)
    try:
        app.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
