import os
import sys
import json
import glob


def _find_today_files(remember_dir):
    return sorted(p for p in glob.glob(os.path.join(remember_dir, 'today-*.md'))
                  if os.path.getsize(p) > 0)


def _describe_dir(remember_dir, project_label):
    def exists_nonempty(path):
        return os.path.isfile(path) and os.path.getsize(path) > 0

    archive = os.path.join(remember_dir, 'archive.md')
    recent = os.path.join(remember_dir, 'recent.md')
    return {
        "project": project_label,
        "remember_dir": remember_dir,
        "archive_path": archive if exists_nonempty(archive) else None,
        "recent_path": recent if exists_nonempty(recent) else None,
        "today_paths": _find_today_files(remember_dir),
    }


def _has_content(entry):
    return bool(entry["archive_path"] or entry["recent_path"] or entry["today_paths"])


def resolve_remember_dirs(cwd=None):
    """Return a list of dicts describing every remember directory that has readable content.

    Checks:
      1. Legacy mode: <cwd>/.remember/  (project-local)
      2. External mode: ~/.remember/*/  (all external-mode projects)

    Each dict has keys: project, remember_dir, archive_path, recent_path, today_paths.
    archive_path / recent_path are None when the file doesn't exist or is empty.
    today_paths is a sorted list (may be empty).
    """
    results = []
    seen = set()

    def _add(remember_dir, label):
        real = os.path.realpath(remember_dir)
        if real in seen or not os.path.isdir(remember_dir):
            return
        seen.add(real)
        entry = _describe_dir(remember_dir, label)
        if _has_content(entry):
            results.append(entry)

    # 1. Legacy mode — current project
    project_root = os.path.realpath(cwd or os.getcwd())
    _add(os.path.join(project_root, '.remember'), project_root)

    # 2. External mode — ~/.remember/*/
    external_root = os.path.join(os.path.expanduser('~'), '.remember')
    if os.path.isdir(external_root):
        for name in sorted(os.listdir(external_root)):
            candidate = os.path.join(external_root, name)
            if os.path.isdir(candidate):
                _add(candidate, name)

    return results


if __name__ == '__main__':
    dirs = resolve_remember_dirs()
    if not dirs:
        sys.stderr.write("[memory-bank] graduate: no remember directories with content found.\n")
        sys.exit(0)
    print(json.dumps(dirs, indent=2))
