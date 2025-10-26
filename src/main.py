from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import shutil
from pathlib import Path
import asyncio
import os

from src.ai.agent import get_file_content
from src.core.model import Attachment, ClientTask, FileContent
from src.core.logger import logger
from src.core.github import create_new_repo, enable_github_pages, create_or_update_file, get_all_files_url, get_output_data, uploade_all_public_file_from_local_directory
from src.core.send_eval import send_evaluation
logger.info("Fresh Starting")
logger.info("")
logger.info("")
logger.info("")

# Required Environment Variables
AIMODEL_NAME = os.getenv("AIMODEL_NAME", None)
GITHUB_ACCESS_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN", None)
GFORM_SECRET = os.getenv("GFORM_SECRET", None)
if not AIMODEL_NAME or not GITHUB_ACCESS_TOKEN or not GFORM_SECRET:
    raise EnvironmentError('Missing some environment variables. Please read README.md')

# App and Enables Cors
app = FastAPI(title="Github Application Builder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def timeouttest(t):
    await asyncio.sleep(t)
    print("+++++++++++++++++++++++++++++++++++++++++++++++++++=")


async def background_job(client_task: ClientTask):
    try:
        logger.info(f"Background job started | Round={client_task.round} | Email={client_task.email} | Task={client_task.task}")

        # Start the Github Task based on round value
        try:
            public_path = Path(__file__).parent.parent / "public" / client_task.task
            if public_path.exists():
                shutil.rmtree(public_path)
                print(f"Deleted: {public_path}")
            public_path.mkdir(parents=True, exist_ok=True)
            

            new_repo_name = "test_" + client_task.task
            await create_new_repo(new_repo_name)

            list_file = await get_file_content(client_task=client_task, public_path=public_path)
            for file in list_file:
                await create_or_update_file(repo_name=new_repo_name, file_path=file.path, file_content=file.content, commit_message=file.commit_message)

            await uploade_all_public_file_from_local_directory(path=public_path, repo_name=new_repo_name)

            await enable_github_pages(new_repo_name)

            new_data = await get_output_data(new_repo_name)
            logger.info("Sending newly created application data")
        except asyncio.TimeoutError:
            new_data = {  # Fallback Data
                "repo_url": "...",
                "commit_sha": "...",
                "pages_url": "..."
            }
            logger.error(f"=====Github task timed out after 9 minutes | Round={client_task.round} | Email={client_task.email}=====")
            logger.info("Sending fallback application data due to timeout")

        except Exception as e:
            new_data = {  # Fallback Data
                "repo_url": "...",
                "commit_sha": "...",
                "pages_url": "..."
            }
            logger.error(f"=====Github task failed=====\n{e}\n===============", exc_info=True)
            logger.info("Sending fallback application data")

        # Get Required Data to send
        payload = {
            "email": str(client_task.email),
            "task": str(client_task.task),
            "round": int(client_task.round),
            "nonce": str(client_task.nonce),
            "repo_url": str(new_data.get("repo_url")),
            "commit_sha": str(new_data.get("commit_sha")),
            "pages_url": str(new_data.get("pages_url")),
        }

        # Send data to evaluation endpoint with retry logic
        await send_evaluation(str(client_task.evaluation_url), payload, max_retries=5, timeout=30)
        logger.info(f"Background job completed | Round={client_task.round} | Email={client_task.email}")

    except Exception as e:
        logger.error(f"Background job failed | Round={client_task.round} | Email={client_task.email} | Error: {e}", exc_info=True)


# Just Health Check
@app.get("/", response_class=HTMLResponse)
async def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Github Application Builder</title>
    </head>
    <body>
        <h1>GitHub Application Builder</h1>
        <p>API is <strong>running</strong> and ready to receive tasks.</p>
        <p>API is currently using AIMODEL = <strong>{AIMODEL_NAME}</strong></p>
        <h2>Endpoints:</h2>
        <ul>
            <li>
                POST /task - Submit deployment task
                <ul>
                    <li> Data in <strong>JsonBody</strong> Required </li>
                    <li> <strong>email, secret, round, task, evaluation_url</strong>: are required</li>
                    <li> <strong>secret</strong>: must match </li>
                    <li></li>
                    <li> email: EmailStr</li> 
                    <li> secret: str</li>
                    <li> task: str</li>
                    <li> round: int</li>
                    <li> evaluation_url: AnyUrl</li>
                    <li> nonce: Optional[str] = None</li>
                    <li> brief: Optional[str] = None</li>
                    <li> checks: Optional[List[str] | str] = None</li>
                    <li> attachments: Optional[List[Attachment]] = None</li>
                    <li></li>
                    <li>Attachments</li>
                    <li>name: str = Field(..., description="Filename, e.g., sample.png")</li>
                    <li>url: str = Field(..., description="Data URI or file link")</li>

                </ul>
            </li>
        </ul>

    </body>
    </html>
    """



@app.post("/task")
async def task(client_task: ClientTask, background_tasks: BackgroundTasks):

    # Log the client data
    logger.info(f"=====New task received | Email={client_task.email} | Round={client_task.round} | Task={client_task.task}=====")
    logger.info(f"=====Full task data=====\n{client_task.model_dump_json(indent=2)}\n===============")


    # Verify secret
    if client_task.secret != GFORM_SECRET:
        logger.warning(f"==========Invalid secret received from {client_task.email}==========")
        logger.warning(f"==========Sending 403 since secret received is invalid==========")
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Start background task
    background_tasks.add_task(background_job, client_task)

    # Return 200 OK immediately
    return {
        "status": "accepted",
        "message": "Task is being processed",
        "email": client_task.email,
        "round": client_task.round,
        "task": client_task.task,
        "evaluation_url": client_task.evaluation_url
    }
