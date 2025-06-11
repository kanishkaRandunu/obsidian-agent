import os
import time
from datetime import datetime, timedelta
import openai
from dotenv import load_dotenv
import re
import urllib.parse
from config import SUMMARY_SAVE_PATH, ALLOWED_FOLDERS, EXTRACTION_PROMPT
load_dotenv()

def list_recent_documents(vault_path, days=2):
    """
    List all .md document names in the specified folders within vault_path that were created or updated within the last `days` days.
    Only includes .md files (not directories or other file types).
    """
    if not os.path.isdir(vault_path):
        raise ValueError(f"Provided path is not a directory: {vault_path}")

    now = time.time()
    cutoff = now - days * 24 * 60 * 60
    recent_files = []

    for folder in ALLOWED_FOLDERS:
        folder_path = os.path.join(vault_path, folder)
        if not os.path.isdir(folder_path):
            continue
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if not file.lower().endswith(".md"):
                    continue
                file_path = os.path.join(root, file)
                stat = os.stat(file_path)
                # Use the most recent of ctime (creation) or mtime (modification)
                last_activity = max(stat.st_mtime, stat.st_ctime)
                if last_activity >= cutoff:
                    # Store relative path from vault root
                    rel_path = os.path.relpath(file_path, vault_path)
                    recent_files.append(rel_path)

    return recent_files


def extract_todos_and_special_points(note_content, api_key, model="gpt-4o"):
    """
    Use OpenAI to extract to-do list tasks and special points from a note's content.
    Returns a markdown string with three sections.
    """
    client = openai.OpenAI(api_key=api_key)
    prompt = EXTRACTION_PROMPT + f"Note content:\n{note_content}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You extract actionable tasks and special points from Obsidian notes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def extract_section(markdown, section_title):
    # Find the section by its title and extract bullet points
    pattern = rf"## {re.escape(section_title)}\s*((?:- .*\n?)*)"
    match = re.search(pattern, markdown, re.IGNORECASE)
    if match:
        bullets = [line[2:].strip() for line in match.group(1).splitlines() if line.startswith("- ")]
        return bullets
    return []


def extract_from_recent_notes(vault_path, api_key, days=2):
    """
    For each recent note, extract to-do tasks and special points using OpenAI.
    Returns a dict: {note_path: markdown_string}
    """
    recent_files = list_recent_documents(vault_path, days)
    all_todos = []
    all_followups = []
    all_papers = []
    for rel_path in recent_files:
        abs_path = os.path.join(vault_path, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            markdown = extract_todos_and_special_points(content, api_key)
            # Attach note path to each item
            all_todos.extend([(item, rel_path) for item in extract_section(markdown, "To-Do Tasks")])
            all_followups.extend([(item, rel_path) for item in extract_section(markdown, "Important things to follow up")])
            all_papers.extend([(item, rel_path) for item in extract_section(markdown, "Papers to read")])
        except Exception as e:
            pass
    return {
        "To-Do Tasks": all_todos,
        "Important things to follow up": all_followups,
        "Papers to read": all_papers,
    }


def write_section_to_md(vault_path, section_name, items, vault_name):
    """
    Write a markdown file for a section in the specified folder, including note links.
    """
    sirimal_folder = os.path.join(vault_path, SUMMARY_SAVE_PATH)
    os.makedirs(sirimal_folder, exist_ok=True)
    filename = f"{section_name.replace(' ', '_')}.md"
    file_path = os.path.join(sirimal_folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {section_name}\n\n")
        for item in items:
            # item is (text, note_path)
            if isinstance(item, tuple):
                text, note_path = item
                encoded_path = urllib.parse.quote(note_path)
                obsidian_url = f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                f.write(f"- {text} [🔗]({obsidian_url})\n")
            else:
                f.write(f"- {item}\n")
    return file_path


def read_existing_summary(vault_path, section_name):
    """
    Read the existing summary .md file for a section and return a set of tasks.
    """
    sirimal_folder = os.path.join(vault_path, SUMMARY_SAVE_PATH)
    filename = f"{section_name.replace(' ', '_')}.md"
    file_path = os.path.join(sirimal_folder, filename)
    tasks = set()
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- "):
                    # Remove the link if present
                    task_text = line[2:].split(" [🔗]", 1)[0].strip()
                    tasks.add(task_text)
    return tasks


def write_all_sections_to_md(vault_path, api_key, days=2, vault_name="kenny's mind"):
    results = extract_from_recent_notes(vault_path, api_key, days)
    paths = {}
    for section in ["To-Do Tasks", "Important things to follow up", "Papers to read"]:
        items = results[section]
        # Read existing tasks
        existing_tasks = read_existing_summary(vault_path, section)
        # Only add new tasks (ignore duplicates)
        unique_items = []
        for item in items:
            text = item[0] if isinstance(item, tuple) else item
            if text not in existing_tasks:
                unique_items.append(item)
        # Combine old and new
        all_items = list(existing_tasks) + [item[0] if isinstance(item, tuple) else item for item in unique_items]
        # Write with note links for new items, plain for old
        # For simplicity, you can keep note links only for new items, or you can store note_path for old items as well if you want
        file_path = write_section_to_md(vault_path, section, items, vault_name)
        paths[section] = file_path
    return paths


if __name__ == "__main__":
    # Example usage: replace this with your selected vault path
    vault_path = "./your_obsidian_vault_folder"  # Replace with actual path
    recent_docs = list_recent_documents(vault_path)
    print("Documents created or updated in the last 7 days:")
    for doc in recent_docs:
        print(doc)
