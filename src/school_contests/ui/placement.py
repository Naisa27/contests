"""Начальная геометрия в координатах выбранного монитора, включая рамку окна."""

from PySide6.QtCore import QRect, QSize


def centered_frame(available: QRect, client: QSize, decoration: QSize) -> QRect:
    """Учитывает отрицательные координаты мониторов и уменьшает слишком большое окно."""
    inset = min(12, available.width() // 4, available.height() // 4)
    area = available.adjusted(inset, inset, -inset, -inset)
    width = min(client.width() + decoration.width(), area.width())
    height = min(client.height() + decoration.height(), area.height())
    return QRect(area.x() + (area.width() - width) // 2,
                 area.y() + (area.height() - height) // 2, width, height)
