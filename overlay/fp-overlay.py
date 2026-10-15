#!/usr/bin/env python3
"""Fingerprint prompt overlay for Hyprland (and other wlroots compositors).

Listens to fprintd signals on the system bus and shows a small animated
card in the middle of the screen whenever something (sudo, a polkit dialog,
...) waits for a fingerprint. It only displays state; authentication is still
done by fprintd and PAM.
"""
import math
import signal

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gio, GLib, Gtk, GtkLayerShell  # noqa: E402

FPRINT_BUS = "net.reactivated.Fprint"
DEVICE_IFACE = "net.reactivated.Fprint.Device"

SIZE = 220
ICON = 108

# state -> (rgb, title, subtitle)
STATES = {
    "waiting": ((0.55, 0.75, 1.00), "Chạm cảm biến vân tay", "để xác thực"),
    "scanning": ((0.55, 0.75, 1.00), "Đang quét…", "giữ yên ngón tay"),
    "success": ((0.35, 0.85, 0.50), "Thành công", ""),
    "fail": ((1.00, 0.42, 0.42), "Không khớp", "thử lại"),
    "retry": ((1.00, 0.78, 0.30), "Chưa nhận rõ", "đặt ngón tay phủ kín cảm biến"),
}

RETRY_RESULTS = {
    "verify-retry-scan", "verify-swipe-too-short", "verify-finger-not-centered",
    "verify-remove-and-retry",
}

CSS = b"""
window { background: transparent; }
.card {
  background: rgba(18, 20, 28, 0.86);
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 18px 18px 20px 18px;
}
.title { color: #f2f4f8; font-size: 15pt; font-weight: 600; }
.subtitle { color: rgba(242, 244, 248, 0.62); font-size: 10.5pt; }
"""

# Ridges of a stylised fingerprint: (radius factor, start angle, end angle) in a
# coordinate system where the icon spans [-1, 1].
RIDGES = [
    (0.16, math.radians(200), math.radians(520)),
    (0.30, math.radians(190), math.radians(470)),
    (0.44, math.radians(185), math.radians(400)),
    (0.58, math.radians(180), math.radians(370)),
    (0.72, math.radians(195), math.radians(345)),
    (0.86, math.radians(205), math.radians(335)),
]


class Overlay(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.state = "waiting"
        self.t0 = GLib.get_monotonic_time()
        self.state_t = self.t0
        self.hide_id = 0
        self.tick_id = 0

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        GtkLayerShell.set_namespace(self, "fp-overlay")
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.get_style_context().add_class("card")
        card.set_size_request(SIZE, -1)
        self.area = Gtk.DrawingArea()
        self.area.set_size_request(SIZE - 36, ICON + 24)
        self.area.connect("draw", self.on_draw)
        self.title = Gtk.Label()
        self.title.get_style_context().add_class("title")
        self.subtitle = Gtk.Label()
        self.subtitle.get_style_context().add_class("subtitle")
        card.pack_start(self.area, False, False, 0)
        card.pack_start(self.title, False, False, 0)
        card.pack_start(self.subtitle, False, False, 0)
        self.add(card)

    # state handling

    def set_state(self, state, hide_after=None):
        self.state = state
        self.state_t = GLib.get_monotonic_time()
        _, title, sub = STATES[state]
        self.title.set_text(title)
        self.subtitle.set_text(sub)
        self.subtitle.set_visible(bool(sub))
        Gtk.Widget.set_opacity(self, 1.0)
        if not self.get_visible():
            self.t0 = self.state_t
            self.show_all()
            self.subtitle.set_visible(bool(sub))
        if not self.tick_id:
            self.tick_id = GLib.timeout_add(16, self.on_tick)
        self.cancel_hide()
        if hide_after is not None:
            self.hide_id = GLib.timeout_add(hide_after, self.fade_out)

    def cancel_hide(self):
        if self.hide_id:
            GLib.source_remove(self.hide_id)
            self.hide_id = 0

    def fade_out(self):
        self.hide_id = 0
        start = GLib.get_monotonic_time()

        def step():
            p = (GLib.get_monotonic_time() - start) / 220000
            if p >= 1:
                self.hide()
                if self.tick_id:
                    GLib.source_remove(self.tick_id)
                    self.tick_id = 0
                return False
            Gtk.Widget.set_opacity(self, 1 - p)
            return True

        GLib.timeout_add(16, step)
        return False

    def on_tick(self):
        self.area.queue_draw()
        return True

    # drawing

    def on_draw(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        now = GLib.get_monotonic_time()
        t = (now - self.t0) / 1e6
        since = (now - self.state_t) / 1e6
        rgb = STATES[self.state][0]

        dx = 0.0
        if self.state == "fail" and since < 0.45:
            dx = math.sin(since * 50) * 9 * (1 - since / 0.45)
        cx, cy = w / 2 + dx, h / 2
        r = ICON / 2

        # glow ring
        pulse = 0.5 + 0.5 * math.sin(t * 3.2) if self.state in ("waiting", "scanning") else 1.0
        ring = r + 8 + (4 * pulse if self.state == "waiting" else 0)
        cr.set_source_rgba(*rgb, 0.10 + 0.12 * pulse)
        cr.arc(cx, cy, ring, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(*rgb, 0.35 + 0.35 * pulse)
        cr.set_line_width(2)
        cr.arc(cx, cy, ring, 0, 2 * math.pi)
        cr.stroke()

        # ridges, with a sweeping "scan" highlight while waiting
        cr.set_line_cap(1)  # round
        cr.set_line_width(4.2)
        scan = (t * 0.9) % 1.6 - 0.3
        for i, (rf, a0, a1) in enumerate(RIDGES):
            level = i / (len(RIDGES) - 1)
            alpha = 0.95
            if self.state == "waiting":
                alpha = 0.45 + 0.5 * max(0.0, 1 - abs(level - scan) * 3)
            elif self.state == "success":
                alpha = 0.35
            cr.set_source_rgba(*rgb, alpha)
            cr.new_sub_path()
            cr.arc(cx, cy + r * 0.08, r * rf, a0, a1)
            cr.stroke()

        if self.state == "success":
            p = min(1.0, since / 0.28)
            cr.set_source_rgba(*rgb, 1)
            cr.set_line_width(9)
            pts = [(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.34),
                   (cx + r * 0.46, cy - r * 0.32)]
            cr.move_to(*pts[0])
            seg = p * 2
            if seg <= 1:
                cr.line_to(pts[0][0] + (pts[1][0] - pts[0][0]) * seg,
                           pts[0][1] + (pts[1][1] - pts[0][1]) * seg)
            else:
                cr.line_to(*pts[1])
                s2 = seg - 1
                cr.line_to(pts[1][0] + (pts[2][0] - pts[1][0]) * s2,
                           pts[1][1] + (pts[2][1] - pts[1][1]) * s2)
            cr.stroke()
        return False


class FprintWatcher:
    def __init__(self, overlay):
        self.overlay = overlay
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.idle_id = 0
        self.bus.signal_subscribe(FPRINT_BUS, DEVICE_IFACE, None, None, None,
                                  Gio.DBusSignalFlags.NONE, self.on_device_signal)
        self.bus.signal_subscribe(FPRINT_BUS, "org.freedesktop.DBus.Properties",
                                  "PropertiesChanged", None, None,
                                  Gio.DBusSignalFlags.NONE, self.on_props)

    def guard(self, ms):
        # Hide if fprintd goes quiet (e.g. PAM timed out and stopped verifying)
        if self.idle_id:
            GLib.source_remove(self.idle_id)
        self.idle_id = GLib.timeout_add(ms, self.on_idle)

    def on_idle(self):
        self.idle_id = 0
        if self.overlay.get_visible() and self.overlay.state not in ("success",):
            self.overlay.fade_out()
        return False

    def on_device_signal(self, _conn, _sender, _path, _iface, name, params):
        if name == "VerifyFingerSelected":
            self.overlay.set_state("waiting")
            self.guard(35000)
        elif name == "VerifyStatus":
            result, done = params.unpack()
            if result == "verify-match":
                self.overlay.set_state("success", hide_after=850)
            elif result == "verify-no-match":
                self.overlay.set_state("fail", hide_after=1400 if done else None)
                if not done:
                    GLib.timeout_add(1100, self.back_to_waiting)
            elif result in RETRY_RESULTS:
                self.overlay.set_state("retry")
                GLib.timeout_add(1300, self.back_to_waiting)
            else:
                self.overlay.fade_out()
            self.guard(35000)

    def back_to_waiting(self):
        if self.overlay.get_visible() and self.overlay.state in ("fail", "retry"):
            self.overlay.set_state("waiting")
        return False

    def on_props(self, _conn, _sender, _path, _iface, _name, params):
        iface, changed, _ = params.unpack()
        if iface != DEVICE_IFACE or not self.overlay.get_visible():
            return
        if changed.get("finger-present") and self.overlay.state == "waiting":
            self.overlay.set_state("scanning")
        if changed.get("finger-needed") is False and self.overlay.state in ("waiting", "scanning"):
            # Verification stopped or a result is about to arrive
            self.guard(2500)


def main():
    overlay = Overlay()
    FprintWatcher(overlay)
    signal.signal(signal.SIGINT, lambda *_: Gtk.main_quit())
    signal.signal(signal.SIGTERM, lambda *_: Gtk.main_quit())
    Gtk.main()


if __name__ == "__main__":
    main()
