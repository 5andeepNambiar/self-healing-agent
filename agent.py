import os
import re
import subprocess
from typing import TypedDict, Literal, Optional, List
from git import Repo  # GitPython
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler

load_dotenv()

# --- 1. STATE DEFINITION ---
class AgentState(TypedDict):
    error_message: str
    iteration: int
    test_passed: bool
    relevant_files: List[str]
    files_context: dict
    commit_message: Optional[str]


# --- 2. STRUCTURED LLM SCHEMA ---
class MultiFilePatchInstruction(BaseModel):
    explanation: str = Field(description="Diagnosis of what caused the bug and which file has the faulty implementation")
    file_to_patch: str = Field(description="The exact relative path of the file that contains the bug and needs to be edited (e.g. 'src/math_utils.py')")
    search_block: str = Field(description="The exact snippet of code in that file that must be replaced")
    replace_block: str = Field(description="The corrected code snippet")
    commit_message: str = Field(description="Conventional git commit message, e.g. 'fix(math_utils): correct percentage calculation formula'")


# --- 3. INITIALIZE GEMINI (With verified model & explicit key) ---
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(
    model="gemini-3.8-flash",
    google_api_key=api_key,
    temperature=0,
    max_retries=3,
    request_timeout=60
)

structured_llm = llm.with_structured_output(MultiFilePatchInstruction)


# --- 4. REPO FILE DISCOVERY ---
def get_project_context_files(traceback_text: str) -> List[str]:
    """Finds all relevant repo source and test files involved in the test failure."""
    found_files = set()

    # 1. Check traceback for mentioned files
    matches = re.findall(r'(?:File "([^"]+\.py)"|([a-zA-Z0-9_\-\./]+\.py):)', traceback_text)
    for m in matches:
        f = m[0] or m[1]
        if os.path.exists(f) and "venv" not in f and "site-packages" not in f:
            found_files.add(f)

    # 2. Include project source files under src/
    if os.path.exists("src"):
        for root, _, files in os.walk("src"):
            for file in files:
                if file.endswith(".py") and not file.startswith("__"):
                    found_files.add(os.path.join(root, file))

    return list(found_files)


# --- 5. NODES ---

def run_tests_node(state: AgentState) -> dict:
    """Runs pytest across the whole project."""
    current_iteration = state["iteration"] + 1
    print(f"\n[Attempt {current_iteration}] Running pytest across project...")

    result = subprocess.run(
        ["pytest", "-v"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("  -> SUCCESS: All project tests passed!")
        return {
            "test_passed": True,
            "error_message": "",
            "iteration": current_iteration
        }
    else:
        print("  -> FAILED: Pytest detected errors.")
        traceback = result.stdout + "\n" + result.stderr

        # Discover all relevant files (traceback + src/)
        involved_files = get_project_context_files(traceback)
        print(f"  -> Discovered involved files: {involved_files}")

        files_context = {}
        for fpath in involved_files:
            try:
                with open(fpath, "r") as f:
                    files_context[fpath] = f.read()
            except Exception as e:
                print(f"  -> Warning: Could not read {fpath}: {e}")

        return {
            "test_passed": False,
            "error_message": traceback,
            "relevant_files": involved_files,
            "files_context": files_context,
            "iteration": current_iteration
        }


def fix_code_node(state: AgentState) -> dict:
    """Passes all relevant files to Gemini and applies surgical patch to the faulty file."""
    print("  -> Asking Gemini to diagnose multi-file context and generate patch...")

    context_str = ""
    files_dict = state.get("files_context") or {}
    for fpath, content in files_dict.items():
        context_str += f"\n--- FILE: {fpath} ---\n{content}\n"

    prompt = f"""You are a senior automated software engineer.
A test failure occurred in this Python repository.

=== INVOLVED REPOSITORY FILES ===
{context_str}

=== PYTEST FAILURE TRACEBACK ===
{state.get('error_message', '')}

Analyze the traceback and code. Determine:
1. Which file contains the actual bug (e.g. implementation error in src/ vs contradictory test).
2. The exact lines to replace in that specific file.
Do not modify test assertions unless the test itself is provably wrong.
Fix the implementation so all tests pass.
"""

    patch: MultiFilePatchInstruction = structured_llm.invoke(prompt)
    print(f"  -> Gemini Diagnosis: {patch.explanation}")
    print(f"  -> Target File to Patch: {patch.file_to_patch}")

    target_path = patch.file_to_patch
    if not os.path.exists(target_path):
        print(f"  -> Error: Target file {target_path} does not exist.")
        return {}

    with open(target_path, "r") as f:
        content = f.read()

    # Apply surgical patch
    if patch.search_block in content:
        updated = content.replace(patch.search_block, patch.replace_block, 1)
        with open(target_path, "w") as f:
            f.write(updated)
        print(f"  -> Successfully patched {target_path}")
    elif patch.search_block.strip() in content:
        updated = content.replace(patch.search_block.strip(), patch.replace_block.strip(), 1)
        with open(target_path, "w") as f:
            f.write(updated)
        print(f"  -> Applied trimmed patch to {target_path}")
    else:
        print(f"  -> Warning: Could not find exact search block in {target_path}.")

    return {
        "commit_message": patch.commit_message
    }


def git_commit_node(state: AgentState) -> dict:
    """Commits healed files to Git."""
    print("\n📦 Git Commit Node:")
    repo = Repo(".")

    diff = repo.git.diff()
    if diff:
        print("  -> Detected Git changes:")
        for line in diff.splitlines()[:6]:
            print(f"     {line}")

        commit_msg = state.get("commit_message") or "fix(agent): auto-healed multi-file bug"
        repo.git.add(A=True)
        commit = repo.index.commit(commit_msg)
        print(f"  -> ✅ Committed to Git: [{commit.hexsha[:7]}] {commit_msg}")
    else:
        print("  -> Working tree clean.")

    return {}


# --- 6. ROUTING LOGIC & GRAPH ASSEMBLY ---

def should_continue(state: AgentState) -> Literal["git_commit", "fix_code", "__end__"]:
    if state["test_passed"]:
        return "git_commit"

    if state["iteration"] >= 3:
        print("\n⚠️ Max retries reached. Halting.")
        return END

    return "fix_code"


workflow = StateGraph(AgentState)

workflow.add_node("run_tests", run_tests_node)
workflow.add_node("fix_code", fix_code_node)
workflow.add_node("git_commit", git_commit_node)

workflow.set_entry_point("run_tests")

workflow.add_conditional_edges(
    "run_tests",
    should_continue,
    {
        "git_commit": "git_commit",
        "fix_code": "fix_code",
        END: END
    }
)

workflow.add_edge("fix_code", "run_tests")
workflow.add_edge("git_commit", END)

app = workflow.compile()


if __name__ == "__main__":
    initial_state: AgentState = {
        "error_message": "",
        "iteration": 0,
        "test_passed": False,
        "relevant_files": [],
        "files_context": {},
        "commit_message": None
    }

    langfuse_handler = CallbackHandler()
    print("🤖 Starting Multi-File Self-Healing Agent...")

    config = {"callbacks": [langfuse_handler]}
    app.invoke(initial_state, config=config)

    if hasattr(langfuse_handler, "client"):
        langfuse_handler.client.flush()
    print("📊 Execution trace sent to Langfuse!")
