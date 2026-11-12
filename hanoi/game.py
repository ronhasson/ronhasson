"""Update the profile's shared Tower of Hanoi board from an issue title."""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
README = HERE.parent / "README.md"
STATE = HERE / "state.json"
BOARD = HERE / "board.svg"
PEGS = "ABC"
DISC_COUNT = 4
START = [0] * DISC_COUNT
GOAL = [2] * DISC_COUNT
START_MARKER = "<!-- hanoi:start -->"
END_MARKER = "<!-- hanoi:end -->"
TITLE = re.compile(r"\[Hanoi\] (0|[1-9][0-9]{0,11}) ([ABC]-[ABC]|reset)")
REPOSITORY = "https://github.com/ronhasson/ronhasson"


def stacks(positions):
    return [
        [disc for disc in range(DISC_COUNT, 0, -1) if positions[disc - 1] == peg]
        for peg in range(len(PEGS))
    ]


def legal_moves(positions):
    if positions == GOAL:
        return {"reset": START}

    board = stacks(positions)
    moves = {}
    for origin, source in enumerate(board):
        if not source:
            continue
        disc = source[-1]
        for target, destination in enumerate(board):
            if target == origin or (destination and destination[-1] < disc):
                continue
            updated = positions.copy()
            updated[disc - 1] = target
            moves[f"{PEGS[origin]}-{PEGS[target]}"] = updated
    return moves


def render_board(positions):
    board = stacks(positions)
    palette = {
        1: (72, "#ffde86", "#d9a951"),
        2: (100, "#ffa991", "#d67468"),
        3: (128, "#a3ded0", "#62aa9e"),
        4: (156, "#a6b9ff", "#748cdb"),
    }
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="612" height="224" viewBox="0 0 612 224" role="img" aria-labelledby="title">
  <title id="title">Tower of Hanoi</title>
  <defs>
    <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#7e8989" opacity=".22"/>
    </pattern>
    <clipPath id="frame"><rect width="612" height="224" rx="20"/></clipPath>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="612" height="224" fill="#202b30"/>
    <rect width="612" height="224" fill="url(#dots)"/>
    <rect x="1" y="1" width="610" height="222" rx="19" fill="none" stroke="#415357" stroke-width="2"/>
    <path d="M32 169h548" stroke="#111b20" stroke-width="16" stroke-linecap="round"/>
    <path d="M32 165h548" stroke="#9d7260" stroke-width="12" stroke-linecap="round"/>
    <path d="M32 162h548" stroke="#d5a483" stroke-width="4" stroke-linecap="round"/>''']

    for peg, (center, discs) in enumerate(zip((118, 306, 494), board)):
        parts.append(
            f'    <path d="M{center} 67v91" stroke="#b0846b" stroke-width="11" stroke-linecap="round"/>'
        )
        parts.append(
            f'    <path d="M{center - 2} 69v89" stroke="#e3b396" stroke-width="3" stroke-linecap="round"/>'
        )
        for level, disc in enumerate(discs):
            width, fill, shade = palette[disc]
            x, y = center - width // 2, 140 - level * 22
            parts.append(
                f'    <rect x="{x}" y="{y + 3}" width="{width}" height="20" rx="7" fill="#152127"/>\n'
                f'    <rect x="{x}" y="{y}" width="{width}" height="19" rx="7" fill="{shade}"/>\n'
                f'    <rect x="{x}" y="{y}" width="{width}" height="15" rx="7" fill="{fill}"/>\n'
                f'    <path d="M{x + 9} {y + 4}h{width - 18}" stroke="#fff8ec" opacity=".45" stroke-width="2" stroke-linecap="round"/>'
            )
        if peg == 2:
            parts.append(
                f'    <rect x="{center - 16}" y="185" width="32" height="26" rx="8" fill="#40564f"/>'
            )
        parts.append(
            f'    <text x="{center}" y="204" text-anchor="middle" fill="#f9ebd9" '
            f'font-family="monospace" font-size="17" font-weight="bold">{PEGS[peg]}</text>'
        )

    if positions == GOAL:
        parts.append('''    <g fill="#ffde86">
      <path d="M494 28l3 8 8 3-8 3-3 8-3-8-8-3 8-3z"/>
      <path d="M443 45l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/>
      <path d="M545 45l2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/>
    </g>''')
    parts.extend(("  </g>", "</svg>", ""))
    return "\n".join(parts)


def render_readme(state):
    positions, revision = state["positions"], state["revision"]
    description = ", ".join(
        f"peg {name}: {', '.join(map(str, discs)) if discs else 'empty'}"
        for name, discs in zip(PEGS, stacks(positions))
    )
    links = []
    for command in legal_moves(positions):
        label = "play again" if command == "reset" else command.replace("-", " → ")
        query = urlencode({
            "title": f"[Hanoi] {revision} {command}",
            "body": "Submit this issue to play. The game will close it after processing your turn.",
        })
        links.append(f"[{label}]({REPOSITORY}/issues/new?{query})")

    prompt = (
        "**we did it!** ✨"
        if positions == GOAL
        else "move the stack to **C**, one disc at a time. smaller discs go on top."
    )
    return "\n".join((
        '<details>',
        '<summary>🧩 open the toolbox</summary>',
        '',
        '#### tower of hanoi',
        '',
        f'![Tower of Hanoi, bottom to top — {description}](hanoi/board.svg?v={revision})',
        '',
        prompt,
        '',
        " · ".join(links),
        '',
        'pick a link, submit the prefilled issue, then refresh to see the shared board.',
        '',
        '</details>',
    ))


def save(state):
    readme = README.read_text(encoding="utf-8")
    before, start, remainder = readme.partition(START_MARKER)
    _, end, after = remainder.partition(END_MARKER)
    if not (start and end):
        raise ValueError("The README must contain both Hanoi markers.")

    README.write_text(
        f"{before}{start}\n{render_readme(state)}\n{end}{after}", encoding="utf-8"
    )
    BOARD.write_text(render_board(state["positions"]), encoding="utf-8")
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def handle_issue(state, issue):
    number = issue["number"]
    if number == state["last_issue"]:
        return "your turn is on the board. thanks for playing! 🧩"

    match = TITLE.fullmatch(issue["title"])
    if not match:
        return "pick a move from the profile and use its prefilled issue title."

    revision, command = match.groups()
    if int(revision) != state["revision"]:
        return "someone played first! refresh the profile and pick a move from the current board."

    positions = legal_moves(state["positions"]).get(command)
    if positions is None:
        return "that move is unavailable. refresh the profile and pick one of the listed moves."

    save({"positions": positions, "revision": state["revision"] + 1, "last_issue": number})
    if command == "reset":
        return "the board is ready for another round. 🧩"
    if positions == GOAL:
        return "you moved the final disc. we did it! ✨"
    return "your turn is on the board. thanks for playing! 🧩"


def main():
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if sys.argv[1:] == ["--render"]:
        save(state)
        return
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as event:
        print(handle_issue(state, json.load(event)["issue"]))


if __name__ == "__main__":
    main()
