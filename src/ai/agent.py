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
    You are an expert in building static web apps for GitHub Pages.

    You will only return those files which are required for github pages like index.html, style.css, script.js or any other file which require to pass checks.

    The file must exist and contain appropriate content to pass all checks.
    Ensure all file paths and relative links are written according to GitHub Pages directory structure requirements.
    Paths should be relative to the project root(same levele where index.html wrote, path of index.html="index.html") as GitHub Pages serves files directly from directories.
    The project must include a valid `index.html` file as the main entry point.

    If static web app need some image/svg histogram chart images or pdfs etc, then you will use run_code_in_temp to generate them in `output_folder_location = {public_path}` and you can assume that i will upload these file along with  your provide text file like index.html and other text files. I will iterative upload files/directory that generate by run_code_in_temp in `output_folder_location = {public_path}` in root folder of github repo


    Analyse the that user directly sent by doing ocr or pdf anaylis or text or html anaysis
    Use run_code_in_temp for attachements that has not been sent directly to you.
    You can use one tool at max two time only (DuckDuckGo search, run_code_in_temp).
    For run_code_in_temp first write the code to get metadata and then write a final code to get all required data to pass the checks then whatever the result or code failed in any case then rely on breif and teask only, never call run_code_in_temp more than two time.
    After that, ensure all provided checks are passed.
    User will give `task`, `brief`, and `checks` — build files accordingly.
    Some attachement that can be send directly to you will be send directly to you. And others including the non-sendable and sendable will be available to you by using run_code_in_temp tool
    Use the code_execution_tool at most 4 times, even if it fails.

    After using a tool, rely only on given inputs to generate final files.
    You should focus on completeing the checks donot use tool calls more than two time, rely on passing the checks because you will be evaluted whether the checks passed or not.

    Two files complusory you need to create robustly one is index.html and one is README.md as index.html is entry point for github pages


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
        {client_task.brief}
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