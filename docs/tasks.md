# Tasks

A task is a Markdown file in `<home>/tasks/`. It is the orchestrator's memory of one piece of work, and it is what the watcher reads.

## Shape

```
---
id: T001
title: Short title
status: running
context: <context>
agents: <machine-label>/<agent-name>, <machine-label>/<other-agent>
session_id:
needs_user: false
created: 2026-01-01
updated: 2026-01-01
---

## Goal
## Done when
## Log
- 2026-01-01 10:00 created
```

Copy `templates/task.md`. File names are `T<number>.md`; the watcher reads files matching `T*.md`.

## Rules

- **Write the task before you delegate.** The `done_when` is what the orchestrator checks the output against. Idle is not done.
- **One log, append only.** Add dated lines. Never edit old ones.
- **Statuses:** `new`, `running`, `blocked`, `needs-user`, `orphaned`, `unreachable`, `done`, `dropped`. Closed tasks move to `<home>/done/YYYY-MM/`.
- **Board.** `board.md` is the index: Needs you, Moving, Done since last update.
- **Journal.** `journal.md` has one line per session event.

## What the watcher reads

Only these front matter fields: `id`, `title`, `status`, `agents`, and the single-agent pair `machine` + `agent`.

- It looks at tasks with `status: new` or `status: running`.
- Each owner is `<machine-label>/<agent-name>`. The label is the saved herdr machine label (or this machine's `machine_label` from the config). The name is the live herdr agent name. Labels cannot contain "/".
- A trailing ` # comment` on a field line is ignored.
- A wrong label or name fails silently: no match, no wake line. `orchid_watcher.py --check` lists each owner and says whether the agent was found.

## When the watcher writes a wake

For an agent that owns an open task:

- it stops working (idle, done or blocked) after it was seen working;
- it sits in `unknown` for 30 seconds (it may be showing a dialog);
- it shows `working` but its screen text has not changed for 10 minutes.

The watcher writes one line to `wakes.log` (in the folder of the orchid config, `~/.config/orchid/` by default, the same path on macOS and Linux). It never types into any agent's input box, never waits for the keyboard, and sends no notification. It waits 60 seconds after the computer wakes from sleep. The line names the agent, its state and the task. It never contains agent output; the screen text is hashed to detect a frozen screen and is neither stored nor sent.

The orchestrator arms a Monitor on the file: `tail -n 0 -F <path>/wakes.log`. A Monitor lasts 30 minutes at most, so the orchestrator arms it again when it ends. At session start it also reads the file for wakes it missed. The orchestrator sends a `PushNotification` only when it has a message for the user. Claude Code skips the notification when the user is at the terminal.

No line for agents without an open task or for the orchestrator itself. No agent sees the line unless a Monitor reads the file.

## Many machines, many agents

List every agent in `agents`. Agent names are unique only per machine, which is why the label comes first.
