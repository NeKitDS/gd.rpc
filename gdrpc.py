__title__ = "gdrpc"
__author__ = "NeKitDS"
__copyright__ = "Copyright 2020 NeKitDS"
__license__ = "MIT"
__version__ = "0.2.7"

import time

import gd
import pypresence


def get_timestamp() -> int:
    return int(time.time())


CLIENT_ID = 704721375050334300
GD_PROCESS = "GeometryDash.exe"
LOOP = gd.utils.acquire_loop()
MESSAGES = {
    gd.memory.Scene.MAIN: "Idle",
    gd.memory.Scene.SELECT: "Selecting level",
    gd.memory.Scene.EDITOR_OR_LEVEL: "Watching level info",
    gd.memory.Scene.SEARCH: "Searching levels",
    gd.memory.Scene.LEADERBOARD: "Browsing leaderboards",
    gd.memory.Scene.ONLINE: "Online",
    gd.memory.Scene.OFFICIAL_LEVELS: "Selecting official level",
}
START = get_timestamp()


client = gd.Client(loop=LOOP)
memory = gd.memory.Memory(GD_PROCESS)
presence = pypresence.AioPresence(str(CLIENT_ID), loop=LOOP)


def get_image(
    difficulty: gd.typing.Union[gd.DemonDifficulty, gd.LevelDifficulty],
    is_featured: bool = False,
    is_epic: bool = False,
) -> str:
    parts = difficulty.name.lower().split("_")

    if is_epic:
        parts.append("epic")

    elif is_featured:
        parts.append("featured")

    return "-".join(parts)


@gd.tasks.loop(seconds=1, loop=LOOP)
async def main_loop() -> None:
    global START

    try:
        memory.reload()

    except RuntimeError:
        START = get_timestamp()
        await presence.clear()
        return

    name = memory.get_user_name()

    if not name:
        name = "Player"

    scene = memory.get_scene()
    level_type = memory.get_level_type()

    if level_type is gd.api.LevelType.NULL:

        if memory.is_in_editor():

            editor_object_count = memory.get_object_count()
            editor_level_name = memory.get_editor_level_name()

            details = "Editing level"
            state = f"{editor_level_name} ({editor_object_count} objects)"

        else:
            details = MESSAGES.get(scene)
            state = None

        small_image = None
        small_text = None

    else:

        current_percent = memory.get_percent()
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

        if level_type == gd.api.LevelType.OFFICIAL:
            level = gd.Level.official(level_id, get_data=False, client=client)

            level_difficulty = level.difficulty
            level_creator = level.creator.name
            is_featured = level.is_featured()
            is_epic = level.is_epic()

            typeof = "official"

        elif level_type == gd.api.LevelType.EDITOR:
            typeof = "editor"

        else:
            typeof = "online"

        details = f"{level_name} ({typeof}) <{gamemode.name.lower()}>"
        state = (
            f"by {level_creator} ({mode} "
            f"{current_percent}%, best {best_normal}%/{best_practice}%)"
        )
        small_image = get_image(level_difficulty, is_featured, is_epic)
        small_text = f"{level_stars}* {level_difficulty.title} (ID: {level_id})"

    await presence.update(
        pid=memory.process_id,
        state=state,
        details=details,
        start=START,
        large_image="gd",
        large_text=name,
        small_image=small_image,
        small_text=small_text,
    )


async def connect() -> None:
    await presence.connect()


def run() -> None:

    print(f"Running gd.rpc v.{__version__}... Press [Ctrl + C] to stop.")

    LOOP.run_until_complete(connect())

    main_loop.start()

    try:
        LOOP.run_forever()

    except KeyboardInterrupt:
        gd.utils.cancel_all_tasks(LOOP)
        presence.close()


if __name__ == "__main__":
    run()
