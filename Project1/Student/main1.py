# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastapi[standard]",
#   "uvicorn",
#   "requests",
# ]
# ///

import requests
import os
import base64
from fastapi import FastAPI
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  
# NOTE: Replace 'YOUR_GITHUB_USERNAME' with the actual username associated with GITHUB_TOKEN
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME") 


def validate_secret(secret: str) -> bool:
    # Simple secret validation
    return secret == os.getenv("SecretKey")


def create_github_repo(repo_name: str):
  # use github api create with the given name
  payload = {
    "name": repo_name,
    "private": False,
    "auto_init": True,
    "license_template": "mit",
    }
  
  headers = {
          "Authorization": f"Bearer {GITHUB_TOKEN}", 
          "Accept": "application/vnd.github.json" # Using the specific MIME type
      }
  response = requests.post(
      "https://api.github.com/user/repos",
      headers=headers,
      json= payload
  )
  if response.status_code != 201:
       raise Exception(f"Failed to create repository '{repo_name}'. Status code: {response.status_code}. Response: {response.text}")
  else:
     return response.json()

   
# --- FIX: New implementation for enable_github_pages ---
def enable_github_pages(repo_name: str):
    # This uses the 'Create a GitHub Pages site' endpoint, which sets the source.
    # We assume deployment from the 'main' branch.
    
    # You MUST set the GITHUB_USERNAME environment variable for this to work.
    if not GITHUB_USERNAME:
        raise Exception("GITHUB_USERNAME environment variable is not set. Cannot enable GitHub Pages.")
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages"
    
    # Payload configures the source branch and directory
    payload = {
        "source": {
            "branch": "main",
            "path": "/" # Deploy from the root of the branch
        }
    }
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github.json"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    # Success codes are 201 (Created) or 204 (No Content) if the site already existed (though POST shouldn't do that)
    if response.status_code not in [201, 204]:
        # A 409 Conflict can occur if Pages is already enabled
        if response.status_code == 409:
            print(f"GitHub Pages for {repo_name} already enabled. Continuing.")
            return
        
        raise Exception(f"Failed to enable GitHub Pages for '{repo_name}'. Status code: {response.status_code}. Response: {response.text}")
    else:
        print(f"GitHub Pages enabled successfully for {repo_name}.")
        return response.json()

def get_sha_of_latest_commit(repo_name: str, file_path: str): # file_path argument is now mandatory
    """
    Retrieves the SHA of the latest commit for a specific file on the 'main' branch.
    Needed for updating existing files.
    """
    if not GITHUB_USERNAME:
        return None # Return None if username is missing, error handled elsewhere

    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_path}?ref=main"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github.json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('sha')
    elif response.status_code == 404:
        # File doesn't exist, this is expected if the file is new
        return None
    else:
        # Handle API errors
        raise Exception(f"Failed to get file SHA for '{file_path}' in '{repo_name}'. Status code: {response.status_code}. Response: {response.text}")


def push_files_to_repo(repo_name: str, files: list[dict], round_num: int):
    """
    Pushes multiple files (or updates them) to the repository using the GitHub API.
    It now ALWAYS checks for file existence and fetches the SHA for updates, 
    making it robust for repeated runs on the same repository (fixing the 422 error).
    """
    
    if not GITHUB_USERNAME:
        raise Exception("GITHUB_USERNAME environment variable is not set.")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.json"
    }

    # Iterate and push/update each file
    for file in files:
        file_name = file.get("name")
        file_content = file.get("content")

        if not file_name or file_content is None:
            print(f"Skipping file due to missing name or content: {file}")
            continue

        # 1. Base64 encode the content
        if isinstance(file_content, bytes):
            encoded_content = base64.b64encode(file_content).decode("utf-8")
        elif isinstance(file_content, str):
            encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        else:
            raise TypeError(f"File content for '{file_name}' must be bytes or string, got {type(file_content)}")

        # 2. CRITICAL FIX: ALWAYS get SHA for the specific file
        current_sha = get_sha_of_latest_commit(repo_name, file_path=file_name)
        
        # 3. Prepare payload
        payload = {
            "message": f"Add/Update {file_name} for Round {round_num}",
            "content": encoded_content,
            "branch": "main" 
        }

        # 4. Include SHA if the file already exists (for update/overwrite)
        if current_sha:
            payload["sha"] = current_sha 

        # 5. Perform the API call
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_name}"

        response = requests.put(
            url,
            headers=headers,
            json=payload
        )

        if response.status_code not in [200, 201]:
             sha_info = f" with SHA: {current_sha}" if current_sha else ""
             raise Exception(f"Failed to push file '{file_name}'{sha_info}. Status code: {response.status_code}, Response: {response.text}")
        else:
             action = "Updated" if response.status_code == 200 else "Created"
             print(f"File '{file_name}' {action} successfully (Status {response.status_code}).")


def write_code_using_llm():
    """
    Simulates the LLM generating the initial code files.
    Returns a list of file dictionaries for push_files_to_repo.
    """
    return [
        {
            "name": "index.html",
            "content": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>This is a test page pushed by LLM for round 1 for GitHub Pages deployment.</p>
</body>
</html>
"""
        }
    ]

def write_code_using_llm_round2():
    """Simulates LLM generating an updated file for Round 2."""
    return [
        {
            "name": "index.html",
            "content": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello World - Round 2</title>
</head>
<body>
    <h1>Hello, World! (Updated in Round 2)</h1>
    <p>This confirms the file update was successful.</p>
</body>
</html>
"""
        }
    ]


def round1(data):
  try:
    files_to_push = write_code_using_llm()
    
    repo_name = f"{data['task']}_{data['nonce']}"
    
    # Push files. Since repo creation is skipped, this handles the file creation/update now.
    push_files_to_repo(repo_name, files_to_push, round_num=1)
    
    return {"message": "Round 1 processing complete (Files pushed/updated)", "repo_name": repo_name} 
  
  except Exception as e:
    print(f"Error during round1 processing: {e}") 
    return {"error": str(e)}

def round2(data):
  try:
    files_to_push = write_code_using_llm_round2()
    
    repo_name = f"{data['task']}_{data['nonce']}"
    
    # Push the updated files with round_num=2
    push_files_to_repo(repo_name, files_to_push, round_num=2)
    
    return {"message": "Round 2 processing complete (Files updated)", "repo_name": repo_name} 
  
  except Exception as e:
    print(f"Error during round2 processing: {e}") 
    return {"error": str(e)}


# The deploy_github_pages is a placeholder and has been removed from the final structure for clarity.

app = FastAPI()

@app.post("/handle_task")
async def handle_task(data:dict):
  # validate secret
  if not validate_secret(data.get("secret", "")):
      return {"error": "Invalid secret"}
  else:
      if data.get("round") == 1:
          result = round1(data)
          return result
      elif data.get("round") == 2:
          # Pass data to round2
          result = round2(data)
          return result
      else:
          return {"error": "Invalid round"}

if __name__ == "__main__":
  import uvicorn
  # NOTE: You must run the server with the GITHUB_USERNAME env var set:
  # e.g., GITHUB_TOKEN=... GITHUB_USERNAME=... uv run main.py
  uvicorn.run(app, host="0.0.0.0", port=8000)