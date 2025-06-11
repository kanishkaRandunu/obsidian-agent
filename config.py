import os

# User-specific configurations
DEFAULT_VAULT_PATH = "/Users/kanishkarandunu/Google Drive/My Drive/14-Obsidian-Notes"  # Replace with your Obsidian vault path
DEFAULT_VAULT_NAME = "kenny's mind"  # Replace with your vault name
AGENT_NAME = "Sirimal"  # Replace with your desired agent name
DAYS_TO_LOOK_BACK = 2  # Number of days to look back for recent documents
SUMMARY_SAVE_PATH = "10 - Sirimal"  # Replace with your desired summary save path

# List of allowed folders to search
ALLOWED_FOLDERS = [
    "2- LEAP Meeting Notes",
    "3 - PhD Meeting Notes",
    "4 - All Notes",
    "8 - Week Planner",
    "zotero-notes"
]

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Ensure this is set in your .env file

# Prompt for OpenAI extraction
EXTRACTION_PROMPT = (
    "I am a PhD student in the field of AI doing research on hyperpersonalization, recommendation systems, and other related topics. I am trying to keep track of my tasks and papers to read and important things to follow up within my Obsidian vault."
    "You are an assistant that reads Obsidian notes in markdown format. "
    "Identify and extract actionable tasks and categorize them into one of three sections: "
    "1. To-Do Tasks, 2. Important things to follow up, 3. Papers to read. "
    "A To-Do Task is any line that is a markdown task (starts with '- [ ]'), or contains action words like: to do, follow up, study, start, develop, explore, learn, finish, read, etc. Ignore other tasks if they do not have these keywords "
    "Do NOT include completed tasks (marked as '- [x]' or containing words like 'done', 'completed', 'ok', 'couldn't finish', 'ignore task', 'not a task'). "
    "If a task fits more than one category, choose the most suitable and do not duplicate it across sections 1. To-Do Tasks, 2. Important things to follow up, 3. Papers to read. "
    "For 'Papers to read', only include tasks that are about reading or studying specific papers or articles. Only consider papers to read with a paper link in the note. "
    "For 'Important things to follow up', include tasks that require further attention, investigation, or follow-up, interesting notes, but are not reading tasks. "
    "Return your answer in markdown format with three sections: "
    "## To-Do Tasks (as a markdown bullet list), "
    "## Important things to follow up (as a markdown bullet list), and "
    "## Papers to read (as a markdown bullet list). "
    "If nothing is found for a category, leave that section empty (do not write anything, not even 'No items found.').\n\n"
) 