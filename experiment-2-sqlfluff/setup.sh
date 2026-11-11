#!/bin/bash
# Setup for blueprint experiment 2 (sqlfluff, PR #8580).
#
#   bash setup.sh        -> first setup: extract, arm-a-1, arm-b-1, scoring env
#   bash setup.sh 2      -> another pair: arm-a-2, arm-b-2 (same for 3, 4, 5)
#   TASK_LANG=tr bash setup.sh   -> use the original Turkish task texts and skill
#
# Folders:
#   ~/Desktop/blueprint-runs/sq/   copies the sessions work in
#   ~/Desktop/contracts/sqlfluff/  hidden tests, oracle, scoring (hidden from sessions)
set -euo pipefail

KIT="$(cd "$(dirname "$0")" && pwd)"
RUNS="$HOME/Desktop/blueprint-runs/sq"
SECRET="$HOME/Desktop/contracts/sqlfluff"
BASE=c01adec1d964db8f12a3df9f679dfaca093ac584
PR=cc44abfb2225bb7f5142a50a3d874e5bccda067f
PY=3.12
PAIR="${1:-1}"
# English translations by default; TASK_LANG=tr uses the Turkish texts the runs used.
if [ "${TASK_LANG:-en}" = "tr" ]; then
  TASKS="$KIT/../original-tr/experiment-2-sqlfluff"
  SKILL="$KIT/../original-tr/extract-skill"
else
  TASKS="$KIT"
  SKILL="$KIT/../extract-skill"
fi

say() { printf '\n==> %s\n' "$1"; }

# --- uv -----------------------------------------------------------------
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  say "installing uv (it builds the Python environments)"
  # The installer fails if it cannot write to ~/.config, but uv is still installed.
  curl -LsSf https://astral.sh/uv/install.sh | sh || true
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "Could not install uv."
  exit 1
fi
UV="$(command -v uv)"
mkdir -p "$SECRET"
# Keep uv's cache in the experiment folder (~/.cache may not be writable).
export UV_CACHE_DIR="$SECRET/uv-cache"
export UV_NO_CONFIG=1

# --- source and snapshots ---------------------------------------------------
mkdir -p "$RUNS" "$SECRET"
if [ ! -d "$SECRET/src/.git" ]; then
  say "cloning sqlfluff (once)"
  git clone -q https://github.com/sqlfluff/sqlfluff "$SECRET/src"
fi
git -C "$SECRET/src" cat-file -e "$BASE^{commit}"
git -C "$SECRET/src" cat-file -e "$PR^{commit}"

snapshot() {  # snapshot <commit> <folder>
  if [ ! -d "$2" ]; then
    mkdir -p "$2"
    git -C "$SECRET/src" archive "$1" | tar -x -C "$2"
  fi
}
snapshot "$BASE" "$SECRET/snap/base"
snapshot "$PR" "$SECRET/snap/oracle"

if [ ! -d "$SECRET/hidden" ]; then
  say "preparing hidden tests"
  for f in test/fixtures/rules/std_rule_cases/LT05.yml \
           test/core/config/validate_test.py \
           test/rules/std_LT05_LT09_combo_test.py; do
    mkdir -p "$SECRET/hidden/$(dirname "$f")"
    git -C "$SECRET/src" show "$PR:$f" > "$SECRET/hidden/$f"
  done
fi
cp "$KIT/score.py" "$SECRET/score.py"

# --- permission file ----------------------------------------------------------
settings() {  # settings <target folder> <own name>
  local self="$2" others="" n
  for n in extract arm-a-1 arm-a-2 arm-a-3 arm-a-4 arm-a-5 arm-b-1 arm-b-2 arm-b-3 arm-b-4 arm-b-5; do
    [ "$n" = "$self" ] && continue
    others="$others      \"Read(~/Desktop/blueprint-runs/sq/$n/**)\",
"
  done
  mkdir -p "$1/.claude"
  cat > "$1/.claude/settings.json" <<EOF
{
  "permissions": {
    "deny": [
      "WebFetch",
      "WebSearch",
      "Bash(git clone:*)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(pip:*)",
      "Bash(pip3:*)",
      "Bash(uv:*)",
      "Bash(python3 -m pip:*)",
      "Bash(.venv/bin/python -m pip:*)",
$others      "Read(~/Desktop/contracts/**)",
      "Read(~/.cache/**)"
    ]
  }
}
EOF
}

# --- one session folder -----------------------------------------------------
make_run() {  # make_run <ad>
  local d="$RUNS/$1"
  if [ -e "$d" ]; then
    echo "$d already exists, leaving it alone."
    return
  fi
  say "preparing $1"
  cp -R "$SECRET/snap/base" "$d"
  (
    cd "$d"
    git init -q
    git add -A
    git -c user.name=blueprint -c user.email=blueprint@local commit -qm "base snapshot"
    printf '.venv/\n*.egg-info/\n.claude/\nTASK.md\n' >> .git/info/exclude
    "$UV" venv -q --python "$PY" .venv
    "$UV" pip install -q --python .venv/bin/python -e . pytest pytest-xdist
  )
  settings "$d" "$1"
}

if [ "$PAIR" = "1" ]; then
  make_run extract
  mkdir -p "$RUNS/extract/.claude/skills"
  cp -R "$SKILL" "$RUNS/extract/.claude/skills/extract"

  if [ ! -d "$SECRET/score-venv" ]; then
    say "preparing scoring environment"
    "$UV" venv -q --python "$PY" "$SECRET/score-venv"
    "$UV" pip install -q --python "$SECRET/score-venv/bin/python" \
      -e "$SECRET/snap/base" pytest pytest-xdist
  fi
fi

make_run "arm-a-$PAIR"
make_run "arm-b-$PAIR"
cp "$TASKS/arm-a/TASK.md" "$RUNS/arm-a-$PAIR/TASK.md"
cp "$TASKS/arm-b/TASK.md" "$RUNS/arm-b-$PAIR/TASK.md"

say "Ready."
echo "Session folders: $RUNS"
ls "$RUNS"
