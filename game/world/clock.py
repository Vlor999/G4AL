"""World clock: the frames elapsed since the game started."""


class WorldClock:
    """Counts the world frames completed since the start of the game: ``advance_world``
    calls ``advance`` at the end of each frame, so during the n-th frame
    ``elapsed_frames`` is n - 1. Only ``advance`` moves it."""

    def __init__(self) -> None:
        self._elapsed_frames = 0

    @property
    def elapsed_frames(self) -> int:
        return self._elapsed_frames

    def advance(self) -> None:
        self._elapsed_frames += 1
