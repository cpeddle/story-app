"""Clean duplicate/stale entries from prompt-log.md."""
from pathlib import Path

log_path = Path(r"c:\projects\personal\story-app\assets\prompt-log.md")
lines = log_path.read_text(encoding="utf-8").splitlines(keepends=True)
print(f"Total lines: {len(lines)}")

# Find the sections to remove:
# - "## Phase 2 — N-7 Throne Room Regeneration — [TO BE COMPLETED]"
# - "## Phase 2 — N-7 Corridor Regeneration — [TO BE COMPLETED]"
# - Two duplicate "## Phase 2 — N-5 Recraft v3 Evaluation — 2026-04-16" blocks
# Keep: the final "## Phase 2 — N-7 Scene Regeneration — 2026-04-16" block onwards

# Strategy: find line numbers of all '## Phase 2' headings
section_starts = []
for i, line in enumerate(lines):
    stripped = line.rstrip()
    if stripped.startswith("## Phase 2"):
        section_starts.append((i, stripped))
        print(f"  Line {i+1}: {stripped}")

# The sections we want to remove are all between the KEEP sections:
# Keep: N-4 (index 0), N-5 clean (index 1), N-7 Scene Regen (last)
# Remove: N-7 Throne TO-DO, N-7 Corridor TO-DO, N-5 dup1, N-5 dup2
keep_sections = {"N-4 Composite", "N-5 Recraft v3 Evaluation — 2026-04-16", "N-7 Scene Regeneration"}

to_remove_start = None
to_remove_end = None
n5_count = 0
for i, (line_no, heading) in enumerate(section_starts):
    if "N-7 Throne Room" in heading or "N-7 Corridor" in heading:
        if to_remove_start is None:
            to_remove_start = line_no
    elif "N-5 Recraft" in heading:
        n5_count += 1
        if n5_count > 1:  # second and third N-5 are duplicates
            if to_remove_start is None:
                to_remove_start = line_no
    elif "N-7 Scene Regeneration" in heading:
        # Everything up to the line before this is what we remove
        to_remove_end = line_no
        break

print(f"\nRemoving lines {to_remove_start+1} to {to_remove_end+1} (exclusive)")

if to_remove_start is not None and to_remove_end is not None:
    # Keep: before to_remove_start, then from to_remove_end onward
    new_lines = lines[:to_remove_start] + lines[to_remove_end:]
    log_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"Done. New total lines: {len(new_lines)}")
else:
    print("ERROR: Could not find boundaries. No changes made.")
    print(f"to_remove_start={to_remove_start}, to_remove_end={to_remove_end}")
