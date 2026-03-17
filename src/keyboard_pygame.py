from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime import Runtime

import pygame
from keyboard import KeyboardBase


class Keyboard(KeyboardBase):

    def __init__(self, runtime: Runtime) -> None:
        KeyboardBase.__init__(self, runtime)

    def run(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if not event.unicode:
                return
            key = ord(event.unicode)
            if event.key == pygame.K_LEFT:
                key = 0x08
            if event.key == pygame.K_RIGHT:
                key = 0x15
            if key:
                self.pressed(chr(key))
