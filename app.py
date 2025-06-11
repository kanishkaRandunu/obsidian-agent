import streamlit as st
import os
from pathlib import Path
from obsidian_agent import list_recent_documents, extract_from_recent_notes, process_and_append_tasks, read_all_tasks_from_summary
from dotenv import load_dotenv
import urllib.parse
load_dotenv()
import os
from config import DEFAULT_VAULT_PATH, DEFAULT_VAULT_NAME, AGENT_NAME, DAYS_TO_LOOK_BACK

api_key = os.getenv("OPENAI_API_KEY")

# Set page configuration FIRST
st.set_page_config(
    page_title="Hi I am Sirimal",
    page_icon="👋",
    layout="wide"
)

# Custom CSS to reduce gap between button columns
st.markdown("""
    <style>
    .block-container .stColumns > div {
        padding-right: 0rem;
        padding-left: 0rem;
    }
    </style>
""", unsafe_allow_html=True)

# Add a title with custom styling
st.markdown("""
    <h1 style='text-align: center; color: #2E86C1;'>
        Hi Kanishka! I am Your Obsidian Agent: Sirimal 👋
    </h1>
""", unsafe_allow_html=True)

# Initialize session state
if 'folder_path' not in st.session_state:
    st.session_state.folder_path = DEFAULT_VAULT_PATH
if 'show_recent_docs' not in st.session_state:
    st.session_state.show_recent_docs = False

# Create a folder selection interface
st.markdown("### 📁 Select Your Obsidian Vault Folder")

# Function to get valid directories
def get_valid_directories(path):
    try:
        items = os.listdir(path)
        directories = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path) and not item.startswith('.'):  # Skip hidden directories
                directories.append(item)
        return sorted(directories)
    except Exception as e:
        st.error(f"Error reading directory: {str(e)}")
        return []

# Create three columns for path, directory selection, and buttons
path_col, dir_col, btn_col = st.columns([2, 2, 2])

# Validate and normalize the path
try:
    current_path = os.path.abspath(st.session_state.folder_path)
    if not os.path.exists(current_path):
        st.error("Path does not exist!")
        current_path = str(Path.home())
    elif not os.path.isdir(current_path):
        st.error("Path is not a directory!")
        current_path = str(Path.home())
except Exception as e:
    st.error(f"Invalid path: {str(e)}")
    current_path = str(Path.home())

# Update session state with validated path
st.session_state.folder_path = current_path

# Get directories in current path
directories = get_valid_directories(current_path)

# Add parent directory option if not at root
parent_dir = os.path.dirname(current_path)
if parent_dir != current_path:  # Don't add if we're at root
    directories.insert(0, "..")

# Display current path in first column
with path_col:
    current_path = st.text_input("Current Path:", st.session_state.folder_path)

# Display directory selection in second column
with dir_col:
    if directories:
        selected_dir = st.selectbox("Select a directory:", directories)
    else:
        st.warning("No accessible directories found in this location.")
        selected_dir = None

# Display buttons in third column, aligned with input fields
with btn_col:
    # Add vertical space to align with input fields (approximate height of input/selectbox)
    st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)
    if selected_dir:
        if selected_dir == "..":
            new_path = parent_dir
        else:
            new_path = os.path.join(current_path, selected_dir)
        # Use tight columns for buttons
        btn_col1, spacer, btn_col2 = st.columns([1, 0.001, 1.8])
        with btn_col1:
            if st.button("Open Selected Directory"):
                st.session_state.folder_path = new_path
                st.session_state.show_recent_docs = False
                st.rerun()
        with spacer:
            st.write("")  # Blank column for spacing
        with btn_col2:
            if st.button("Select This Folder as Obsidian Vault"):
                st.session_state.show_recent_docs = True
                st.session_state.selected_vault_path = current_path
                st.rerun()

# Show recent documents if a vault is selected
if st.session_state.get('show_recent_docs', False):
    st.markdown(f"#### 📝 Notes created or updated in the last {DAYS_TO_LOOK_BACK} days:")
    try:
        recent_docs = list_recent_documents(st.session_state.selected_vault_path, DAYS_TO_LOOK_BACK)
        if recent_docs:
            st.write(f"Found: {len(recent_docs)}")
            vault_name = DEFAULT_VAULT_NAME
            note_links = []
            for note_path in recent_docs:
                encoded_path = urllib.parse.quote(note_path)
                obsidian_url = f"obsidian://open?vault={urllib.parse.quote(vault_name)}&file={encoded_path}"
                note_links.append(f"[{note_path}]({obsidian_url})")
            st.markdown(" &nbsp;|&nbsp; ".join(note_links), unsafe_allow_html=True)
            
            if api_key and st.button(f"Put {AGENT_NAME} to Work"):
                with st.spinner(f"{AGENT_NAME} is working on it with OpenAI..."):
                    new_counts = process_and_append_tasks(st.session_state.selected_vault_path, api_key, DAYS_TO_LOOK_BACK, vault_name=vault_name)
                st.success(f"New to-do tasks: {new_counts['To-Do Tasks']} | New important things to follow up: {new_counts['Important things to follow up']} | New papers to read: {new_counts['Papers to read']}")

                # Read and display all tasks from the updated summary files
                todos = read_all_tasks_from_summary(st.session_state.selected_vault_path, "To-Do Tasks")
                followups = read_all_tasks_from_summary(st.session_state.selected_vault_path, "Important things to follow up")
                papers = read_all_tasks_from_summary(st.session_state.selected_vault_path, "Papers to read")

                col1, col2, col3 = st.columns(3)
                with col1:
                    if todos:
                        st.markdown("### 📝 To-Do Tasks")
                        for line in todos:
                            st.markdown(line, unsafe_allow_html=True)
                with col2:
                    if followups:
                        st.markdown("### 🔎 Important things to follow up")
                        for line in followups:
                            st.markdown(line, unsafe_allow_html=True)
                with col3:
                    if papers:
                        st.markdown("### 📚 Papers to read")
                        for line in papers:
                            st.markdown(line, unsafe_allow_html=True)
            elif not api_key:
                st.error("OpenAI API key not found in environment variables.")
        else:
            st.info("No documents created or updated in the last 2 days.")
    except Exception as e:
        st.error(f"Error reading documents: {e}")



# # Add a divider
# st.divider()




