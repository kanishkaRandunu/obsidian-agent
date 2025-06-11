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


def is_valid_paper_task(text):
    # Only accept if there's a link to a paper (arxiv, doi, or http(s) link)
    if "arxiv.org" in text or "doi.org" in text or "http://" in text or "https://" in text:
        return True
    return False


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
            all_papers.extend([
                (item, rel_path)
                for item in extract_section(markdown, "Papers to read")
                if is_valid_paper_task(item) and "1H Read a Paper" not in item
            ])
        except Exception as e:
            pass
    return {
        "To-Do Tasks": all_todos,
        "Important things to follow up": all_followups,
        "Papers to read": all_papers,
    }


def write_section_to_md(vault_path, section_name, items, vault_name):
    """
    Overwrite the markdown file for a section in the specified folder, including note links, with the full deduplicated list.
    """
    sirimal_folder = os.path.join(vault_path, SUMMARY_SAVE_PATH)
    os.makedirs(sirimal_folder, exist_ok=True)
    filename = f"{section_name.replace(' ', '_')}.md"
    file_path = os.path.join(sirimal_folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# {section_name}\n\n")
        for item in items:
            text, note_path = item
            # Some tasks might not have an originating note (note_path is None).
            # When no note is available, simply write the text without an Obsidian link.
            if note_path:
                encoded_path = urllib.parse.quote(note_path)
                obsidian_url = (
                    f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                )
                f.write(f"- {text} [🔗]({obsidian_url})\n")
            else:
                f.write(f"- {text}\n")
    return file_path


def read_existing_summary(vault_path, section_name):
    """
    Read the existing summary .md file for a section and return a set of (task_text, note_path) tuples.
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
                    main_part = line[2:]
                    # Try to extract note_path from the obsidian link. If no
                    # link is present, note_path will remain None and we'll
                    # store the task without a source note.
                    note_path = None
                    text = main_part
                    if "[🔗](obsidian://open?vault=" in main_part:
                        # Extract the note_path from the URL
                        try:
                            link_start = main_part.index("[🔗](obsidian://open?vault=")
                            url = main_part[link_start+5:].split(')',1)[0]
                            # Find &file= param
                            file_param = url.split('&file=')[-1]
                            note_path = urllib.parse.unquote(file_param)
                            text = main_part[:link_start].strip()
                        except Exception:
                            note_path = None
                    # Normalize text for deduplication
                    norm_text = text.strip().lower()
                    if note_path:
                        tasks.add((norm_text, note_path))
                    else:
                        tasks.add((norm_text, None))
    return tasks


def process_and_update_summaries(vault_path, api_key, days=2, vault_name="kenny's mind"):
    results = extract_from_recent_notes(vault_path, api_key, days)
    new_counts = {}
    for section in ["To-Do Tasks", "Important things to follow up", "Papers to read"]:
        # Read all existing tasks
        existing_tasks = read_existing_summary(vault_path, section)
        # Add new tasks from LLM extraction
        new_items = results[section]
        # Combine and deduplicate by (normalized text, note_path)
        combined = set(existing_tasks)
        for item in new_items:
            norm_text = item[0].strip().lower()
            combined.add((norm_text, item[1]))
        # Convert back to (original text, note_path) for writing
        # We'll use the latest version of the text from new_items if available
        deduped = {}
        for item in new_items:
            norm_text = item[0].strip().lower()
            deduped[(norm_text, item[1])] = item[0]  # keep original text
        for norm_text, note_path in combined:
            if (norm_text, note_path) not in deduped:
                deduped[(norm_text, note_path)] = norm_text  # fallback to normalized text
        # Prepare list for writing
        final_list = [(text, note_path) for (norm_text, note_path), text in deduped.items()]
        # Sort for consistency. `x[1]` may be None when a task has no link,
        # so use an empty string as a fallback to avoid TypeError.
        final_list.sort(key=lambda x: (x[1] or "", x[0]))
        write_section_to_md(vault_path, section, final_list, vault_name)
        new_counts[section] = len(final_list)
    return new_counts


if __name__ == "__main__":
    # Example usage: replace this with your selected vault path
    vault_path = "./your_obsidian_vault_folder"  # Replace with actual path
    recent_docs = list_recent_documents(vault_path)
    print("Documents created or updated in the last 7 days:")
    for doc in recent_docs:
        print(doc)
