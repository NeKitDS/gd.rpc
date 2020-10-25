__title__ = "rpc"
__author__ = "nekitdev"
__copyright__ = "Copyright 2020 nekitdev"
__license__ = "MIT"
__version__ = "1.0.0rc0"

from pathlib import Path
import time
from typing import Optional, Union

from gd.json import NamedDict
import gd
import pypresence  # type: ignore  # no stubs or types
import toml  # type: ignore  # no stubs or types

# default config to use if we can not find config file
DEFAULT_TOML = """
[rpc]
process_name = "default"
refresh_rate = 1
client_id = 704721375050334300

[rpc.editor]
details = "Editing level"
state = "{level_name} ({object_count} objects)"

[rpc.level]
details = "{level_name} ({level_type}) <{gamemode}> [attempt {attempt}]"
state = "by {level_creator} ({mode} {percent}%, best {best_normal}%/{best_practice}%)"
small_text = "{level_stars}* {level_difficulty} (ID: {level_id})"
percent_precision = 1

[rpc.scene]
main = "Idle"
select = "Selecting level"
editor_or_level = "Watching level info"
search = "Searching levels"
leaderboard = "Browsing leaderboards"
online = "Online"
official_levels = "Selecting official level"
official_level = "Playing official level"

[rpc.difficulty]
na = "N/A"
auto = "Auto"
easy = "Easy"
normal = "Normal"
hard = "Hard"
harder = "Harder"
insane = "Insane"
demon = "Demon"
easy_demon = "Easy Demon"
medium_demon = "Medium Demon"
hard_demon = "Hard Demon"
insane_demon = "Insane Demon"
extreme_demon = "Extreme Demon"

[rpc.gamemode]
cube = "Cube"
ship = "Ship"
ball = "Ball"
ufo = "UFO"
wave = "Wave"
robot = "Robot"
spider = "Spider"

[rpc.level_type]
null = "null"
official = "official"
editor = "editor"
saved = "saved"
online = "online"

[rpc.mode]
normal = "normal"
practice = "practice"
""".lstrip()

GD = "gd"  # do not change

ROOT = Path(__file__).parent.resolve()
PATH = ROOT / "rpc_config.toml"  # path to config


if not PATH.exists():  # if not exists -> create write default config
    with open(PATH, "w") as file:
        file.write(DEFAULT_TOML)


def get_timestamp() -> int:
    """Return the time in seconds since the epoch as integer."""
    return int(time.time())


def is_soft_dunder(string: str) -> bool:
    return string.startswith("__") and string.endswith("__")


def load_config() -> NamedDict:
    """Load TOML config for RPC and return it."""
    config = toml.load(PATH, NamedDict)
    return config.rpc  # type: ignore


rpc = load_config()

if rpc.process_name == "default":
    memory_state = gd.memory.get_state(load=False)

else:
    memory_state = gd.memory.get_state(rpc.process_name, load=False)

start = get_timestamp()

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
        memory_state.reload()  # attempt to reload memory

    except LookupError:  # can not find
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

    account_manager = memory_state.get_account_manager()

    user_name = account_manager.get_user_name()  # get user name

    if not user_name:  # set default if not found
        user_name = "Player"

    game_manager = memory_state.get_game_manager()

    editor_layer = game_manager.get_editor_layer()
    play_layer = game_manager.get_play_layer()

    player = play_layer.get_player()
    level = play_layer.get_level_settings().get_level()

    if level.is_null():  # if not playing any levels
        if editor_layer.is_null():
            scene = game_manager.get_scene()

            details = rpc.scene.get(scene.name.lower())
            state = None

        else:
            editor_level = editor_layer.get_level_settings().get_level()

            format_map = dict(
                object_count=editor_layer.get_object_count(),
                level_name=editor_level.get_name(),
                user_name=user_name,
            )

            details = rpc.editor.details.format_map(format_map)
            state = rpc.editor.state.format_map(format_map)

        small_image = None
        small_text = None

    else:  # if playing some level

        percent = round(play_layer.get_percent(), rpc.level.percent_precision)
        attempt = play_layer.get_attempt()
        best_normal = level.get_normal_percent()
        best_practice = level.get_practice_percent()

        mode = rpc.mode.practice if play_layer.is_practice_mode() else rpc.mode.normal

        gamemode = player.get_gamemode()

        level_id = level.get_id()
        level_name = level.get_name()
        level_creator = level.get_creator_name()
        level_difficulty = level.get_difficulty()
        level_stars = level.get_stars()
        level_type = level.get_level_type()

        is_featured = level.is_featured()
        is_epic = level.is_epic()

        if level_type is gd.LevelType.OFFICIAL:
            gd_level = gd.Level.official(level_id, get_data=False)

            level_difficulty = gd_level.difficulty
            level_creator = gd_level.creator.name
            is_featured = gd_level.is_featured()
            is_epic = gd_level.is_epic()

        elif level_type is gd.LevelType.EDITOR:
            level_difficulty = gd.LevelDifficulty.NA  # type: ignore

        format_map = dict(
            user_name=user_name,
            percent=percent,
            best_normal=best_normal,
            best_practice=best_practice,
            attempt=attempt,
            mode=mode,
            gamemode=rpc.gamemode.get(gamemode.name.lower()),
            level_type=rpc.level_type.get(level_type.name.lower()),
            level_id=level_id,
            level_name=level_name,
            level_creator=level_creator,
            level_difficulty=rpc.difficulty.get(level_difficulty.name.lower()),
            level_stars=level_stars,
        )

        details = rpc.level.details.format_map(format_map)
        state = rpc.level.state.format_map(format_map)

        small_image = get_image(level_difficulty, is_featured, is_epic)
        small_text = rpc.level.small_text.format_map(format_map)

    await presence.update(
        pid=memory_state.process_id,
        state=state,
        details=details,
        start=start,
        large_image=GD,
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
