__title__ = "gdrpc"
__author__ = "NeKitDS"
__copyright__ = "Copyright 2020 NeKitDS"
__license__ = "MIT"
__version__ = "0.3.2"

from pathlib import Path
import time
from typing import Any, Optional, Union

import gd  # type: ignore  # no stubs or types
import pypresence  # type: ignore  # no stubs or types
import toml  # type: ignore  # no stubs or types

# default config to use if we can not find config file
DEFAULT_TOML = """
[rpc]
refresh_rate = 1
client_id = 704721375050334300

[rpc.editor]
details = "Editing level"
state = "{level_name} ({object_count} objects)"

[rpc.level]
details = "{level_name} ({level_type}) <{gamemode}>"
state = "by {level_creator} ({mode} {percent}%, best {best_normal}%/{best_practice}%)"
small_text = "{level_stars}* {level_difficulty} (ID: {level_id})"

[rpc.scene]
main = "Idle"
select = "Selecting level"
editor_or_level = "Watching level info"
search = "Searching levels"
leaderboard = "Browsing leaderboards"
online = "Online"
official_levels = "Selecting official level"
official_level = "Playing official level"
""".lstrip()

ROOT = Path(__file__).parent.resolve()
PATH = ROOT / "gdrpc.toml"  # path to config


if not PATH.exists():  # if not exists -> create write default config
    with open(PATH, "w") as file:
        file.write(DEFAULT_TOML)


def get_timestamp() -> int:
    """Return the time in seconds since the epoch as integer."""
    return int(time.time())


class NamedDict(dict):
    def __getattr__(self, name: str) -> Any:
        """Same as self[name]."""
        return self[name]


def load_config() -> NamedDict:
    """Load TOML config for RPC and return it."""
    config = toml.load(PATH, NamedDict)
    return config.rpc  # type: ignore


rpc = load_config()
start = get_timestamp()

memory = gd.memory.get_memory(load=False)

presence = pypresence.AioPresence(str(rpc.client_id))


def get_image(
    difficulty: Union[gd.DemonDifficulty, gd.LevelDifficulty],
    is_featured: bool = False,
    is_epic: bool = False,
) -> str:
    """Generate name of an image based on difficulty and parameters."""
    parts = difficulty.name.lower().split("_")

    if is_epic:
        parts.append("epic")

    elif is_featured:
        parts.append("featured")

    return "-".join(parts)


@gd.tasks.loop(seconds=rpc.refresh_rate, loop=presence.loop)
async def main_loop() -> None:
    # declare variables as global since we edit them
    global rpc
    global start

    try:
        memory.reload()  # attempt to reload memory

    except RuntimeError:  # on fail
        start = get_timestamp()  # restart time
        await presence.clear()  # clear presence state

        return

    try:
        rpc = load_config()  # try to load config
    except toml.TomlDecodeError:
        pass  # do nothing on fail

    # annotations for mypy
    details: Optional[str]
    state: Optional[str]

    user_name = memory.get_user_name()  # get user name

    if not user_name:  # set default if not found
        user_name = "Player"

    scene = memory.get_scene()
    level_type = memory.get_level_type()

    if level_type is gd.api.LevelType.NULL:  # if not playing any levels

        if memory.is_in_editor():

            object_count = memory.get_object_count()
            level_name = memory.get_editor_level_name()

            format_map = dict(
                object_count=object_count,
                level_name=level_name,
                user_name=user_name,
            )

            details = rpc.editor.details.format_map(format_map)
            state = rpc.editor.state.format_map(format_map)

        else:

            details = rpc.scene.get(scene.name.lower())
            state = None

        small_image = None
        small_text = None

    else:  # if playing some level

        percent = memory.get_percent()
        attempt = memory.get_attempt()
        best_normal = memory.get_normal_percent()
        best_practice = memory.get_practice_percent()

        mode = "practice" if memory.is_practice_mode() else "normal"

        gamemode = memory.get_gamemode()

        level_id = memory.get_level_id()
        level_name = memory.get_level_name()
        level_creator = memory.get_level_creator()
        level_difficulty = memory.get_level_difficulty()
        level_stars = memory.get_level_stars()

        is_featured = memory.is_level_featured()
        is_epic = memory.is_level_epic()

        if level_type is gd.api.LevelType.OFFICIAL:
            level = gd.Level.official(level_id, get_data=False)

            level_difficulty = level.difficulty
            level_creator = level.creator.name
            is_featured = level.is_featured()
            is_epic = level.is_epic()

            level_type = "official"

        elif level_type is gd.api.LevelType.EDITOR:
            level_type = "editor"

        else:
            level_type = "online"

        format_map = dict(
            user_name=user_name,
            percent=percent,
            best_normal=best_normal,
            best_practice=best_practice,
            attempt=attempt,
            mode=mode,
            gamemode=gamemode.title,
            level_id=level_id,
            level_name=level_name,
            level_creator=level_creator,
            level_difficulty=level_difficulty.title,
            level_stars=level_stars,
            level_type=level_type,
        )

        details = rpc.level.details.format_map(format_map)
        state = rpc.level.state.format_map(format_map)

        small_image = get_image(level_difficulty, is_featured, is_epic)
        small_text = rpc.level.small_text.format_map(format_map)

    await presence.update(
        pid=memory.process_id,
        state=state,
        details=details,
        start=start,
        large_image="gd",
        large_text=user_name,
        small_image=small_image,
        small_text=small_text,
    )


def run() -> None:

    print(
        f"Running gd.rpc v.{__version__}...",
        f"Root directory: {ROOT}",
        "Press [Ctrl + C] to stop.",
        sep="\n",
    )

    presence.loop.run_until_complete(presence.connect())

    main_loop.start()

    try:
        presence.loop.run_forever()

    except KeyboardInterrupt:
        gd.utils.cancel_all_tasks(presence.loop)
        presence.close()


if __name__ == "__main__":
    run()
