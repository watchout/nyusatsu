#!/bin/bash
# Pre-Code Gate hook for Claude Code (PreToolUse)
# Reads .framework/gates.json and blocks source code edits when gates have not passed.
# Also requires an active task from \`framework run\` before allowing edits.
# Exit 2 = deny (Claude Code convention), Exit 0 = allow

input=$(cat)
tool=$(echo "$input" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{console.log(JSON.parse(d).tool_name||'')}catch{console.log('')}})")

project_dir="${CLAUDE_PROJECT_DIR:-.}"

# Extract file path based on tool type
file_path=""
if [ "$tool" = "Edit" ] || [ "$tool" = "Write" ]; then
  file_path=$(echo "$input" | node -e "let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{try{console.log(JSON.parse(d).tool_input.file_path||'')}catch{console.log('')}})")
fi

# No file path = not a file edit, allow
if [ -z "$file_path" ]; then
  exit 0
fi

# Make path relative to project dir
rel_path="${file_path#$project_dir/}"

# Check if path is a protected source code path
case "$rel_path" in
  src/*|app/*|server/*|lib/*|components/*|pages/*|composables/*|utils/*|stores/*|plugins/*)
    ;;
  *)
    exit 0
    ;;
esac

# ─── Skill Warning (soft layer) ───
# Check if a skill has been activated recently (within 6 hours).
# If not, print a warning to stderr. Does NOT block (exit 0 continues).
skill_file="$project_dir/.framework/active-skill.json"
skill_active=false
if [ -f "$skill_file" ]; then
  skill_active=$(node -e "
    const fs = require('fs');
    try {
      const d = JSON.parse(fs.readFileSync('$skill_file', 'utf8'));
      const age = Date.now() - new Date(d.activatedAt).getTime();
      console.log(age < 6 * 3600 * 1000 ? 'true' : 'false');
    } catch { console.log('false'); }
  ")
fi

if [ "$skill_active" != "true" ]; then
  echo "" >&2
  echo "[Skill Warning] No skill activated for this session." >&2
  echo "  Consider using a skill before editing source code:" >&2
  echo "  /implement — for implementation tasks" >&2
  echo "  /design    — for design tasks" >&2
  echo "  /review    — for code review" >&2
  echo "" >&2
fi

# ─── Pre-Code Gate (hard layer) ───
# Check .framework/gates.json
gates_file="$project_dir/.framework/gates.json"
if [ ! -f "$gates_file" ]; then
  echo "[Pre-Code Gate] .framework/gates.json not found. Run 'framework gate check'." >&2
  exit 2
fi

result=$(node -e "
  const fs = require('fs');
  try {
    const g = JSON.parse(fs.readFileSync('$gates_file', 'utf8'));
    const a = g.gateA && g.gateA.status || 'pending';
    const b = g.gateB && g.gateB.status || 'pending';
    const c = g.gateC && g.gateC.status || 'pending';
    if (a === 'passed' && b === 'passed' && c === 'passed') {
      console.log('PASSED');
    } else {
      console.log(a + ',' + b + ',' + c);
    }
  } catch(e) { console.log('error'); }
")

if [ "$result" != "PASSED" ]; then
  IFS=',' read -r gate_a gate_b gate_c <<< "$result"

  echo "" >&2
  echo "=====================================" >&2
  echo "  PRE-CODE GATE: EDIT BLOCKED" >&2
  echo "=====================================" >&2
  echo "  Gate A (Environment): ${gate_a:-error}" >&2
  echo "  Gate B (Planning):    ${gate_b:-error}" >&2
  echo "  Gate C (SSOT):        ${gate_c:-error}" >&2
  echo "" >&2
  echo "  Run: framework gate check" >&2
  echo "=====================================" >&2
  exit 2
fi

# ─── Active Task Check (hard layer) ───
# Requires a task started via \`framework run\` before allowing source edits.
# Skip: FRAMEWORK_SKIP_TASK_CHECK=1, profile lp/hp

if [ "${FRAMEWORK_SKIP_TASK_CHECK:-}" = "1" ]; then
  exit 0
fi

# Single node call: check profile + run-state
task_check=$(node -e "
  const fs = require('fs');
  try {
    const pf = '$project_dir/.framework/project.json';
    if (fs.existsSync(pf)) {
      const p = JSON.parse(fs.readFileSync(pf, 'utf8'));
      const pt = p.profileType || p.type || '';
      if (pt === 'lp' || pt === 'hp') { console.log('SKIP'); process.exit(0); }
    }
    const rf = '$project_dir/.framework/run-state.json';
    if (!fs.existsSync(rf)) { console.log('NO_STATE'); process.exit(0); }
    const s = JSON.parse(fs.readFileSync(rf, 'utf8'));
    if (s.currentTaskId) { console.log('ACTIVE:' + s.currentTaskId); }
    else {
      const t = (s.tasks || []).find(t => t.status === 'in_progress');
      console.log(t ? 'ACTIVE:' + t.taskId : 'NO_TASK');
    }
  } catch { console.log('ERROR'); }
")

case "$task_check" in
  SKIP|ACTIVE:*)
    exit 0
    ;;
  *)
    echo "" >&2
    echo "=====================================" >&2
    echo "  ACTIVE TASK REQUIRED" >&2
    echo "=====================================" >&2
    echo "  Gates passed, but no task is in progress." >&2
    echo "  Start a task first:" >&2
    echo "    framework run <taskId>" >&2
    echo "" >&2
    echo "  Emergency bypass:" >&2
    echo "    FRAMEWORK_SKIP_TASK_CHECK=1" >&2
    echo "=====================================" >&2
    exit 2
    ;;
esac
