"""A menu that refuses to hide underneath a panel.

Qt asks the platform whether popups may cover the whole screen. On KDE/XCB the
answer is yes, so ``QMenu`` fits itself to the *full* screen rectangle instead
of the work area. A tray menu is opened right next to a panel by definition, so
that difference is exactly the panel's thickness: the bottom items end up
behind it. Submenus inherit the placement of their parent, which is where it is
most obvious -- they open to the side and run off the edge of the screen.

Clamping to :meth:`QScreen.availableGeometry` restores what a user expects on
every platform. Where Qt already gets it right (Windows, macOS, and any desktop
that reports a work area to Qt) the clamp finds nothing to do and is a no-op.
"""

from typing import override

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QMenu


def fitted_position(frame: QRect, area: QRect) -> QPoint:
    """Where ``frame`` has to sit to stay inside ``area``.

    Overflow is resolved by pulling the near edge back, so a menu that is
    simply larger than the work area is aligned to the area's top-left corner
    and stays reachable rather than disappearing off the far side.
    """
    x, y = frame.x(), frame.y()
    if frame.right() > area.right():
        x = area.right() - frame.width() + 1
    if x < area.left():
        x = area.left()
    if frame.bottom() > area.bottom():
        y = area.bottom() - frame.height() + 1
    if y < area.top():
        y = area.top()
    return QPoint(x, y)


class TrayMenu(QMenu):
    """A :class:`QMenu` that keeps itself inside the desktop work area."""

    @override
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        frame = self.frameGeometry()
        target = fitted_position(frame, self.screen().availableGeometry())
        if target != frame.topLeft():
            self.move(target)
