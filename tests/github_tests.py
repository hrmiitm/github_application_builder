from src.core.github import (
    create_new_repo,
    enable_github_pages,
    create_or_update_file,
    get_all_files_url,
    get_output_data
)

import asyncio

# WARNING: This creates REAL repos on GitHub!

async def manual_test():
    repo_name = "test-repo-delete-me"
    
    print("1. Creating repo...")
    result = await create_new_repo(repo_name)
    print(f"   Result: {result}")

    print("1. Creating again repo...")
    result = await create_new_repo(repo_name)
    print(f"   Result: {result}")
    
    print("2. Creating file...")
    result = await create_or_update_file(repo_name, "index.html", "<h1>Test</h1>")
    print(f"   Result: {result}")

    print("3. Updating file...")
    result = await create_or_update_file(repo_name, "index.html", "<h1>Test2</h1>")
    print(f"   Result: {result}")
    
    print("4. Enabling pages...")
    result = await enable_github_pages(repo_name)
    print(f"   Result: {result}")
    
    print("5. Getting files...")
    result = await get_all_files_url(repo_name)
    print(f"   Result: {result}")
    
    print("6. Getting output data...")
    result = await get_output_data(repo_name)
    print(f"   Result: {result}")
    
    print(f"⚠️  Remember to delete repo: {repo_name}")

asyncio.run(manual_test())
