import os
import re
import sys
import json

def audit_skill(skill_path):
    report = {
        "naming": {"status": "✅", "finding": "Matches specification."},
        "frontmatter": {"status": "✅", "finding": "Format is valid."},
        "tone": {"status": "✅", "finding": "Imperative and third-person."},
        "paths": {"status": "✅", "finding": "Forward slashes used."},
        "scripts": {"status": "✅", "finding": "Deterministic and non-interactive."},
        "references": {"status": "✅", "finding": "Modular with TOC where needed."},
        "evals": {"status": "✅", "finding": "Evaluation set present."},
        "security": {"status": "✅", "finding": "No obvious secrets found."}
    }

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    content = ""
    if os.path.exists(skill_md_path):
        with open(skill_md_path, 'r') as f:
            content = f.read()

    # 1. Directory & Naming Audit
    dir_name = os.path.basename(os.path.normpath(skill_path))
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', dir_name):
        report["naming"]["status"] = "❌"
        report["naming"]["finding"] = f"Directory name '{dir_name}' is not kebab-case."
    
    # Check for gerund form: ends with -ing (longer than 4 chars to avoid false positives like ping, ring, string)
    # Common non-gerund terms are explicitly exempted to prevent false positives.
    NON_GERUNDS = {
        "string", "spring", "thing", "something", "anything", 
        "nothing", "everything", "during", "bring", "cling", 
        "fling", "sling", "sting", "swing", "wring", "sibling", 
        "pudding", "lightning"
    }
    words = dir_name.split("-")
    has_gerund = any(word.endswith("ing") and len(word) > 4 and word not in NON_GERUNDS for word in words)
    if has_gerund:
        report["naming"]["status"] = "⚠️"
        report["naming"]["finding"] = f"Skill name '{dir_name}' uses a gerund form (ends in '-ing'). Avoid gerunds and prefer simple, descriptive names (e.g. 'code-design' instead of 'designing-code', 'doc-review' instead of 'reviewing-docs')."

    if content:
        # Check frontmatter name
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        if name_match:
            fm_name = name_match.group(1).strip()
            if fm_name != dir_name:
                report["naming"]["status"] = "❌"
                report["naming"]["finding"] = f"Frontmatter name '{fm_name}' does not match directory '{dir_name}'."

        # 2. Frontmatter Description & Category Audit
        fm_findings = []
        fm_status = "✅"
        
        desc_match = re.search(r'^description:\s*["\\]?(.+?)["\\]?$', content, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip()
            if len(description) > 1024:
                fm_status = "❌"
                fm_findings.append("Description exceeds 1024 characters.")
            
            trigger_patterns = ["use this skill when", "use when", "trigger:"]
            if not any(description.lower().startswith(p) for p in trigger_patterns):
                if fm_status != "❌":
                    fm_status = "⚠️"
                fm_findings.append("Description MUST start with 'Use when...' or 'Use this skill when...'.")
            
            # Workflow summarization check (heuristic)
            procedural_keywords = ["then", "finally", "step", "first", "afterwards", "sequentially", "subsequently", "firstly", "secondly", "thirdly", "lastly", "workflow"]
            if any(x in description.lower() for x in procedural_keywords):
                fm_status = "❌"
                fm_findings.append("Description summarizes workflow. Move process details to skill body.")
        else:
            fm_status = "❌"
            fm_findings.append("Missing 'description' in frontmatter.")

        # Category Validation
        VALID_CATEGORIES = {
            "library-reference",
            "product-verification",
            "data-analysis",
            "team-automation",
            "code-scaffolding",
            "code-quality",
            "cicd-deployment",
            "runbook",
            "infra-ops"
        }
        category_match = re.search(r'^\s*category:\s*["\']?([a-zA-Z0-9_-]+)["\']?$', content, re.MULTILINE)
        if not category_match:
            if fm_status != "❌":
                fm_status = "⚠️"
            fm_findings.append("Missing 'category' field in YAML frontmatter metadata.")
        else:
            category = category_match.group(1).strip()
            if category not in VALID_CATEGORIES:
                fm_status = "❌"
                fm_findings.append(f"Invalid category '{category}' in frontmatter. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}.")

        if fm_findings:
            report["frontmatter"]["status"] = fm_status
            report["frontmatter"]["finding"] = " ".join(fm_findings)

        # 3. Instruction & Tone Audit
        forbidden_pronouns = [r'(?<![A-Z/])\bI\b(?![/A-Z])', r'\bme\b', r'\bmy\b', r'\bwe\b']
        for p in forbidden_pronouns:
            if re.search(p, content, re.IGNORECASE):
                report["tone"]["status"] = "❌"
                report["tone"]["finding"] = "Found first-person pronouns (I, me, my, we)."
                break
        
        # Only check for passive prose in non-reference/non-guide skills
        is_discipline_skill = not any(x in dir_name.lower() for x in ["reference", "guide", "pattern", "skills", "doc", "style", "layout"])
        if is_discipline_skill:
            forbidden_prose = [r'\bshould\b', r'\bconsider\b', r'\bmight\b']
            for p in forbidden_prose:
                if re.search(p, content, re.IGNORECASE):
                    report["tone"]["status"] = "❌"
                    report["tone"]["finding"] = "Found passive suggestion prose (should, consider, might). Use MUST/NEVER for discipline skills."
                    break
        
        if "[ ]" not in content and "Checklist" not in content:
            report["tone"]["status"] = "⚠️"
            report["tone"]["finding"] = "Missing explicit [ ] checklists or structured workflow section."

        # Structural requirement check
        structural_sections = ["Gotcha", "Anti-Pattern", "Common Mistake", "Pitfall", "Red Flag", "STOP", "Common Mistakes"]
        if not any(s.lower() in content.lower() for s in structural_sections):
            report["tone"]["status"] = "❌"
            report["tone"]["finding"] = "Missing 'Gotchas' or 'Anti-Patterns' section for bulletproofing."

        # 4. Path Audit
        escapes = ["\\n", "\\t", "\\r", "\\\"", "\\'"]
        clean_content = content
        for e in escapes:
            clean_content = clean_content.replace(e, "")
        
        if "\\" in clean_content:
            report["paths"]["status"] = "❌"
            report["paths"]["finding"] = "Found backslashes in paths or code. Use forward slashes."

    # 5. Scripts Audit
    scripts_dir = os.path.join(skill_path, "scripts")
    if os.path.isdir(scripts_dir):
        for root, dirs, files in os.walk(scripts_dir):
            for file in files:
                f_path = os.path.join(root, file)
                with open(f_path, 'r', errors='ignore') as f:
                    s_content = f.read()
                    
                    if file.endswith(".sh"):
                        if "set -e" not in s_content:
                            report["scripts"]["status"] = "❌"
                            report["scripts"]["finding"] = f"Script '{file}' is missing 'set -e'."
                        if "read " in s_content or "confirm" in s_content:
                            report["scripts"]["status"] = "❌"
                            report["scripts"]["finding"] = f"Script '{file}' contains interactive commands (read/confirm)."
                    
                    if file.endswith(".py"):
                        if "# /// script" not in s_content:
                            report["scripts"]["status"] = "⚠️"
                            report["scripts"]["finding"] = f"Python script '{file}' missing PEP 723 inline dependencies."

                    if "--help" not in s_content and "help" not in s_content.lower():
                        report["scripts"]["status"] = "⚠️"
                        report["scripts"]["finding"] = f"Script '{file}' potentially missing --help documentation."
                    
                    if any(x in s_content for x in ["rm ", "delete", "drop", "write_file"]):
                        if "--dry-run" not in s_content:
                            report["scripts"]["status"] = "⚠️"
                            report["scripts"]["finding"] = f"Destructive script '{file}' missing --dry-run flag."

    # 6. References Audit
    ref_dir = os.path.join(skill_path, "references")
    if os.path.isdir(ref_dir):
        for root, dirs, files in os.walk(ref_dir):
            for file in files:
                if file.endswith(".md"):
                    with open(os.path.join(root, file), 'r') as f:
                        lines = f.readlines()
                        if len(lines) > 100:
                            has_toc = any(re.search(r'Table of Contents|TOC|##? Contents', line, re.I) for line in lines[:30])
                            if not has_toc:
                                report["references"]["status"] = "❌"
                                report["references"]["finding"] = f"Reference '{file}' exceeds 100 lines but lacks a Table of Contents."

    # 7. Evals Audit
    evals_dir = os.path.join(skill_path, "evals")
    if not os.path.isdir(evals_dir):
        report["evals"]["status"] = "❌"
        report["evals"]["finding"] = "Missing 'evals/' directory."
    else:
        eval_files = [f for f in os.listdir(evals_dir) if f.endswith((".json", ".toml"))]
        if len(eval_files) == 0:
            report["evals"]["status"] = "❌"
            report["evals"]["finding"] = "No evaluation files found in 'evals/'."
        else:
            try:
                with open(os.path.join(evals_dir, eval_files[0]), 'r') as f:
                    eval_data = json.load(f)
                    if isinstance(eval_data, list) and len(eval_data) > 0:
                        first_case = eval_data[0]
                        if "trap" not in first_case or "assertions" not in first_case:
                            report["evals"]["status"] = "⚠️"
                            report["evals"]["finding"] = "Eval cases should include 'trap' and 'assertions' fields."
            except:
                pass

    # 8. Security & Config Isolation Audit
    report["config"] = {"status": "✅", "finding": "Configuration isolation standards are satisfied."}
    
    config_json_path = os.path.join(skill_path, "config.json")
    has_config_json = os.path.exists(config_json_path)
    config_indicators = []
    
    secret_patterns = [r'api[_-]?key', r'secret', r'password', r'token']
    for root, dirs, files in os.walk(skill_path):
        # Skip standard subdirectories like .git or evals/
        if any(p in root for p in [".git", "evals"]):
            continue
        for file in files:
            if file.endswith((".md", ".sh", ".py", ".json", ".yaml", ".js")):
                if file == "config.json":
                    continue
                f_path = os.path.join(root, file)
                try:
                    with open(f_path, 'r', errors='ignore') as f:
                        f_content = f.read()
                        
                        # Custom Config check
                        if "os.getenv" in f_content or "os.environ" in f_content or "process.env" in f_content or ".env" in f_content or "load_dotenv" in f_content:
                            config_indicators.append(file)
                        
                        # Secret check
                        for p in secret_patterns:
                            if re.search(p + r'\s*[:=]\s*["\\]?[a-zA-Z0-9]{10,}', f_content, re.IGNORECASE):
                                # Exclude common placeholders and non-secrets
                                if not any(x in f_content for x in ["PLACEHOLDER", "example", "YOUR_", "EXAMPLE_"]):
                                    report["security"]["status"] = "❌"
                                    report["security"]["finding"] = f"Potential hardcoded secret found in '{file}'."
                                    break
                except:
                    pass

    if config_indicators and not has_config_json:
        report["config"]["status"] = "⚠️"
        report["config"]["finding"] = f"Potential environment/configuration references detected in {', '.join(sorted(list(set(config_indicators)))[:3])}, but 'config.json' is missing. Externalize your settings to config.json."
    return report

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No skill path provided"}))
        sys.exit(1)
    
    skill_path = sys.argv[1]
    results = audit_skill(skill_path)
    print(json.dumps(results, indent=2))
