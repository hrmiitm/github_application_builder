import os
import re
import base64
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.messages import BinaryContent
from src.core.model import Attachment, ClientTask, FileContent
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from src.core.logger import logger

AIMODEL_NAME = os.getenv('AIMODEL_NAME')


from typing import List

def run_code_in_temp(ctx: RunContext[ClientTask], code: str, dependency: List[str] = None) -> str:
    """
    Execute arbitrary Python code inside a temporary directory using uv run.
    
    Workflow that this tool will use:
    1. Creates script.py with the provided code
    2. Runs `uv add --script script.py <packages>` to add dependencies
    3. Runs `uv run script.py` to execute the script
    
    Args:
        ctx: Run context with client task data
        code: Python code to execute
        dependency: List of all packages names(think for optional dependency also) without versions, e.g., ["pandas", "numpy"]
    
    Returns:
        stdout or error message with execution details
    """
    logger.info(f"=====run_code_in_temp on code=====\n{code}\n====================")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        script = workdir / "script.py"

        # Write user-provided code to script.py
        script.write_text(code)

        # Access the current task context (client data)
        client_task = ctx.deps

        # Write all attachments to the temp directory
        if client_task.attachments:
            for file in client_task.attachments:
                loc = workdir / file.name

                # Handle base64 encoded data URIs
                if file.url.startswith("data:"):
                    header, b64data = file.url.split(",", 1)
                    binary_data = base64.b64decode(b64data)
                    loc.write_bytes(binary_data)
                else:
                    # Assume plain text content
                    loc.write_text(file.url)

        result = subprocess.run(
            ["ls"],
            capture_output=True,
            text=True,
            cwd=workdir,
            timeout=10,
        )
        logger.info(f"=====Files in temp directory\n{result.stdout}\n=====")

        # Add dependencies to script using uv add --script if provided
        if dependency and len(dependency) > 0:
            try:
                add_cmd = ["uv", "add", "--script", str(script)] + dependency
                add_result = subprocess.run(
                    add_cmd,
                    capture_output=True,
                    text=True,
                    cwd=workdir,
                    timeout=30,
                )
                logger.info(f"=====uv add output=====\n{add_result.stdout}\n{add_result.stderr}\n=====")
                
                if add_result.returncode != 0:
                    return f"❌ Error adding dependencies:\n{add_result.stderr}"
                    
            except subprocess.TimeoutExpired:
                return "⏰ Timeout while adding dependencies."
            except FileNotFoundError:
                return "❌ Error: 'uv' command not found. Please install uv first."

        # Run the script using uv run
        try:
            result = subprocess.run(
                ["uv", "run", str(script)],
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=30,
            )
            output = result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            output = "⏰ Execution timed out."
        except FileNotFoundError:
            output = "❌ Error: 'uv' command not found. Please install uv first."

        # List created files for reference
        files_created = [p.name for p in workdir.iterdir()]
        logger.info(f"===final script.py content==={subprocess.run(
                ["cat", str(script)],
                capture_output=True,
                text=True,
                cwd=workdir,
                timeout=30,
            ).stdout}\n=====")

        code_result = (
            f"📂 Temp directory: {workdir}\n\n"
            f"🧾 Files created: {files_created}\n\n"
            f"🪄 Output:\n{output}"
        )
        logger.info(f"=====code_result=====\n{code_result}\n====================")
        return code_result


# def run_code_in_temp(ctx: RunContext[ClientTask], code: str, dependecy=List[str]) -> str:
#     """
#     Execute arbitrary Python code inside a temporary directory using uv run.
    
#     Args:
#         ctx: Run context with client task data
#         code: Python code to execute
#         dependency: List of package names without versions, e.g., ["pandas", "numpy"]
    
#     Returns:
#         stdout or error message with execution details
#     """
#     logger.info(f"=====run_code_in_temp on code=====\n{code}\n====================")
#     with tempfile.TemporaryDirectory() as tmpdir:
#         workdir = Path(tmpdir)
#         script = workdir / "script.py"

#         # Write user-provided code to script.py
#         script.write_text(code)

#         # Access the current task context (client data)
#         client_task = ctx.deps

#         # Write all attachments to the temp directory
#         if client_task.attachments:
#             for file in client_task.attachments:
#                 loc = workdir / file.name

#                 # Handle base64 encoded data URIs
#                 if file.url.startswith("data:"):
#                     header, b64data = file.url.split(",", 1)
#                     binary_data = base64.b64decode(b64data)
#                     loc.write_bytes(binary_data)
#                 else:
#                     # Assume plain text content
#                     loc.write_text(file.url)

#         result = subprocess.run(
#                 ["ls"],
#                 capture_output=True,
#                 text=True,
#                 cwd=workdir,
#                 timeout=10,  # prevent infinite loops
#         )
#         logger.info(f"=====Files in temp directory\n{result.stdout}\n=====")

#         # Run the provided code in the isolated directory
#         try:
#             result = subprocess.run(
#                 ["uv", "run", str(script)],
#                 capture_output=True,
#                 text=True,
#                 cwd=workdir,
#                 timeout=10,  # prevent infinite loops
#             )
#             output = result.stdout or result.stderr
#         except subprocess.TimeoutExpired:
#             output = "⏰ Execution timed out."

#         # List created files for reference
#         files_created = [p.name for p in workdir.iterdir()]

#         code_result =  (
#             f"📂 Temp directory: {workdir}\n\n"
#             f"🧾 Files created: {files_created}\n\n"
#             f"🪄 Output:\n{output}"
#         )
#         logger.info(f"=====code_result=====\n{code_result}\n====================")
#         return code_result


async def get_file_content(client_task: ClientTask, public_path: str):
    build_app_agent = Agent(
        AIMODEL_NAME,
        deps_type=ClientTask,
        tools=[duckduckgo_search_tool(), Tool(run_code_in_temp, takes_ctx=True)],
        output_type=List[FileContent],
        system_prompt=f"""
You are an **expert in building static web apps for GitHub Pages**. Your primary goal is to ensure every generated project passes **all user-provided checks**.

1. **Required outputs:** only produce files needed for GitHub Pages: `index.html` (mandatory), `README.md` (mandatory), `style.css`, `script.js`, and any additional static assets (images/SVGs/PDFs/JSON) **only if required to pass checks**.

2. **File validity:** every file must be complete, valid, and ready to be served; links and paths must be **relative to the project root** (same level as `index.html` and index.html path must be `index.html`).

3. **Non-text assets:** if assets must be generated, create them via `run_code_in_temp` and save to:

```
output_folder_location = {public_path}
```

Assume the user will upload those generated files into the repo root alongside your text files.

4. **Attachment analysis:** analyze attachments via OCR/PDF/HTML/text etc parsing. For attachments not sent directly, use `run_code_in_temp` tool to execute python script(must provide necessary dependency).

5. **Tool limits:** strictly follow:

   * `run_code_in_temp` — **at most 4 calls** (use first to extract metadata/preview, later to generate final outputs).
   * `DuckDuckGo search` — **at most 1 call** if absolutely needed.
   * After tool use, rely only on provided inputs (`task`, `brief`, `checks`) to produce final files.

6. **Process:** interpret `task`, `brief`, and `checks`; build files to **fully satisfy all checks**; prefer reliability and standards compliance over complexity.

7. **Constraints:** never output files unrelated to GitHub Pages; ensure assets referenced in `index.html` exist at the specified relative paths; prioritize passing checks.

        """
    )



    def parse_data_uri(data_uri):
        # Example: data:image/png;base64,iVBORw...
        match = re.match(r'data:(.*?);base64,(.*)', data_uri)
        if not match:
            raise ValueError("Invalid data URI")
        media_type, b64_data = match.groups()
        return media_type, base64.b64decode(b64_data)
    SENDABLE_TYPES = {
        # 🖼️ Visual content
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp',
        
        # 📄 Documents that LLM can read directly
        'application/pdf',  # LLM can summarize text content, not extract structured tables perfectly
        'text/plain',       # .txt, .md, logs, etc.
        'text/html',        # Can be summarized, parsed semantically
    }

    sendable_attachement_list = [a.name for a in client_task.attachments if parse_data_uri(a.url)[0] in SENDABLE_TYPES]
    all_attachements_list = [a.name for a in client_task.attachments]

    binary_attachments = []
    for att in client_task.attachments:
        if att.name in sendable_attachement_list:
            media_type, data = parse_data_uri(att.url)
            binary_attachments.append(BinaryContent(data=data, media_type=media_type))
    logger.info(f"no of binary attachment sendin\n{len(binary_attachments)}\n==========")

    prompt = f"""
        -----task-----
        {client_task.task}
        --------------
        -----brief-----
        {client_task.brief}
        --------------
        -----checks-----
        {client_task.checks}
        --------------
        -----attachements directly sent to you(not required run_code_in_temp tool call-----
        {sendable_attachement_list}
        -------------
        -----all attachements availabe in run_code_in_temp-----
        {all_attachements_list}
        ------------
    """

    logger.info(f"running build_app_agent on prompt:\n{prompt}\n=====")

    result = await build_app_agent.run([prompt, *binary_attachments], deps=client_task)

    logger.info(f"output of build_app_agent\n{result.output}\n=====")
    with open("./a.txt", 'w') as f:
        f.write(str(result.output))
    
    return result.output