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

async def uploade_all_public_file_from_local_directory(path: str, repo_name: str) -> Dict[str, str]:
    """
    Upload all files from a local directory to a GitHub repository.
    Recursively walks through the directory and uploads all files.
    
    Args:
        path: Local directory path to upload from
        repo_name: Name of the repository to upload to
    
    Returns:
        {"message": "uploaded", "count": "X"} - Files uploaded successfully
        {"message": "failed"} - Operation failed
    
    Example:
        >>> uploade_all_public_file_from_local_directory("./my-project", "my-repo")
        {"message": "uploaded", "count": "5"}
    
    Note:
        - Automatically detects text vs binary files
        - Creates directory structure in repo matching local structure
        - Skips hidden files and common ignore patterns (.git, __pycache__, etc.)
    """
    import os
    
    g = Github(auth=Auth.Token(token))
    
    try:
        user = g.get_user()
        repo = user.get_repo(repo_name)
        
        # Patterns to skip
        skip_patterns = {'.git', '__pycache__', '.DS_Store', 'node_modules', '.env', '.venv'}
        
        uploaded_count = 0
        
        # Walk through local directory
        for root, dirs, files in os.walk(path):
            # Remove skip patterns from dirs to prevent recursing into them
            dirs[:] = [d for d in dirs if d not in skip_patterns]
            
            for filename in files:
                # Skip hidden files and unwanted patterns
                if filename.startswith('.') or filename in skip_patterns:
                    continue
                
                local_file_path = os.path.join(root, filename)
                
                # Calculate relative path for GitHub
                relative_path = os.path.relpath(local_file_path, path)
                # Normalize path separators for GitHub (use forward slash)
                github_path = relative_path.replace(os.sep, '/')
                
                try:
                    # Read file content
                    # Try reading as text first
                    try:
                        with open(local_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except (UnicodeDecodeError, UnicodeError):
                        # If text read fails, read as binary
                        with open(local_file_path, 'rb') as f:
                            content = f.read()
                    
                    # Check if file exists in repo
                    try:
                        existing_file = repo.get_contents(github_path, ref="main")
                        # Update existing file
                        repo.update_file(
                            path=existing_file.path,
                            message=f"Update {github_path}",
                            content=content,
                            sha=existing_file.sha,
                            branch="main"
                        )
                        logger.info(f"Updated: {github_path}")
                    except UnknownObjectException:
                        # Create new file
                        repo.create_file(
                            path=github_path,
                            message=f"Add {github_path}",
                            content=content,
                            branch="main"
                        )
                        logger.info(f"Created: {github_path}")
                    
                    uploaded_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to upload {github_path}: {e}")
                    continue
        
        logger.info(f"uploade_all_public_file_from_local_directory(path={path}, repo={repo_name}): uploaded {uploaded_count} files")
        return {"message": "uploaded", "count": str(uploaded_count)}
        
    except GithubException as e:
        logger.error(f"GitHub API error on uploade_all_public_file_from_local_directory(path={path}, repo={repo_name}): {e.status} - {e.message}")
        return {"message": "failed"}
    except Exception as e:
        logger.error(f"Unexpected error on uploade_all_public_file_from_local_directory(path={path}, repo={repo_name}): {e}")
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
