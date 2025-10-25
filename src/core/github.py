from github import Github, Auth, GithubException, UnknownObjectException
from typing import Dict
import os
import requests

from src.core.logger import logger


token = os.getenv('GITHUB_ACCESS_TOKEN')


async def create_new_repo(new_repo_name: str) -> Dict[str, str]:
    """
    Create a new GitHub repository
    
    Args:
        new_repo_name: Name for the new repository
    
    Returns:
        {"message": "created"} - Repository created successfully
        {"message": "already exist"} - Repository already exists
        {"message": "failed"} - If some error happens
    
    Example:
        >>> create_new_repo("my-project-123")
        {"message": "created"}
    """
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        
        # Check if repo already exists
        try:
            user.get_repo(new_repo_name)
            logger.info(f"create_new_repo({new_repo_name}): already exist")
            return {"message": "already exist"}
        except UnknownObjectException:
            # Repo doesn't exist, create it
            user.create_repo(
                name=new_repo_name,
                description="New Repo Created",
                private=False,
                auto_init=True
            )
            logger.info(f"create_new_repo({new_repo_name}): created")
            return {"message": "created"}
            
    except GithubException as e:
        logger.error(f"GitHub API error on creating new repo({new_repo_name}): {e.status} - {e.message}")
        return {"message": "failed"}
    except Exception as e:
        logger.error(f"Unexpected error on creating new repo({new_repo_name}): {e}")
        return {"message": "failed"}
    finally:
        g.close()


async def enable_github_pages(repo_name: str) -> Dict[str, str]:
    """
    Enable GitHub Pages for a repository.

    Args:
        repo_name: Name of the repository
    
    Returns:
        {"message": "enabled"} - Pages enabled successfully
        {"message": "already enabled"} - Pages already active
        {"message": "failed"} - Operation failed
    """
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        owner_name = user.login

        url = f"https://api.github.com/repos/{owner_name}/{repo_name}/pages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        data = {
            "source": {
                "branch": "main",
                "path": "/"
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 201:
            logger.info(f"enable_github_pages({repo_name}): enabled")
            return {"message": "enabled"}
        elif response.status_code == 409:
            logger.info(f"enable_github_pages({repo_name}): already enabled")
            return {"message": "already enabled"}
        else:
            logger.error(f"enable_github_pages({repo_name}): failed: {response.status_code} - {response.text}")
            return {"message": "failed"}
            
    except requests.RequestException as e:
        logger.error(f"enable_github_pages({repo_name}): Request error: {e}")
        return {"message": "failed"}
    except Exception as e:
        logger.error(f"Unexpected error on enable_github_pages({repo_name}): {e}")
        return {"message": "failed"}
    finally:
        g.close()


async def create_or_update_file(
    repo_name: str,
    file_path: str,
    file_content: str,
    commit_message: str = "File created/updated"
) -> Dict[str, str]:
    """
    Create a new file or update an existing file in a repository.
    
    This function handles both file creation and updates intelligently:
    - If file doesn't exist: creates it
    - If file exists: updates it with new content
    
    Args:
        repo_name: Name of the repository
        file_path: Path to the file within repository (e.g., "src/index.html")
        file_content: Content to write to the file (string)
        commit_message: Git commit message (default: "File created/updated")
    
    Returns:
        {"message": "created"} - File created successfully
        {"message": "updated"} - File updated successfully
        {"message": "failed"} - Operation failed
    
    Example:
        >>> create_or_update_file("my-repo", "index.html", "<!DOCTYPE html>...", "Add homepage")
        {"message": "created"}
    
    Note:
        - File content must be string, not bytes
        - Creates intermediate directories automatically if needed
        - Each call creates a new commit
    """
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        repo = user.get_repo(repo_name)
        
        # Check if file exists
        try:
            existing_file = repo.get_contents(file_path, ref="main")
            # File exists, update it
            repo.update_file(
                path=existing_file.path,
                message=commit_message,
                content=file_content,
                sha=existing_file.sha,
                branch="main"
            )
            logger.info(f"create_or_update_file(repo={repo_name}, file_path={file_path}): updated")
            return {"message": "updated"}
            
        except UnknownObjectException:
            # File doesn't exist, create it
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=file_content,
                branch="main"
            )
            logger.info(f"create_or_update_file(repo={repo_name}, file_path={file_path}): created")
            return {"message": "created"}
            
    except GithubException as e:
        logger.error(f"GitHub API error on create_or_update_file(repo={repo_name}, file_path={file_path}): {e.status} - {e.message}")
        return {"message": "failed"}
    except Exception as e:
        logger.error(f"Unexpected error on create_or_update_file(repo={repo_name}, file_path={file_path}): {e}")
        return {"message": "failed"}
    finally:
        g.close()


async def get_all_files_url(repo_name: str) -> Dict[str, str]:
    """
    Returns a dictionary mapping file paths to their GitHub URLs for all files 
    in the given repository. Only files (not directories) are included.
    
    Args:
        repo_name: Name of the repository
    
    Returns:
        Dictionary with file paths as keys and download URLs as values
        Empty dict if error occurs
    """
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        repo = user.get_repo(repo_name)
        result = {}

        def walk_contents(path: str = ""):
            """Recursively walk through repository contents"""
            try:
                contents = repo.get_contents(path, ref="main")
                # get_contents returns a list for directories, single item for files
                if not isinstance(contents, list):
                    contents = [contents]
                    
                for content_file in contents:
                    if content_file.type == "dir":
                        walk_contents(content_file.path)
                    elif content_file.type == "file":
                        result[content_file.path] = content_file.download_url
            except GithubException as e:
                logger.error(f"Error walking path '{path}' for get_all_files_url({repo_name}): {e.message}")

        walk_contents("")
        logger.info(f"get_all_files_url({repo_name}): done")
        return result

    except GithubException as e:
        logger.error(f"GitHub API error on get_all_files_url({repo_name}): {e.status} - {e.message}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error on get_all_files_url({repo_name}): {e}")
        return {}
    finally:
        g.close()


async def get_output_data(repo_name: str) -> Dict[str, str]:
    """
    Get repository output data including URLs and latest commit SHA.
    
    Args:
        repo_name: Name of the repository
    
    Returns:
        Dictionary with repo_url, commit_sha, and pages_url
        Empty dict if error occurs
    """
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        user_name = user.login
        repo = user.get_repo(repo_name)

        repo_url = repo.html_url
        commits = repo.get_commits()
        commit_sha = commits[0].sha if commits.totalCount > 0 else "no commits"
        pages_url = f"https://{user_name}.github.io/{repo_name}/"

        logger.info(f"get_output_data({repo_name}): done")
        return {
            "repo_url": repo_url,
            "commit_sha": commit_sha,
            "pages_url": pages_url
        }
        
    except GithubException as e:
        logger.error(f"GitHub API error on get_output_data({repo_name}): {e.status} - {e.message}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error on get_output_data({repo_name}): {e}")
        return {}
    finally:
        g.close()
