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


# Use this proxy https://aipipe.org/openai/v1 with the correct endpoint
api_base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
api_key = os.getenv("OPENAI_API_KEY")  # Make sure to set your OpenAI API key in the environment variable

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
        "Accept": "application/vnd.github+json"
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
    Files must be a list of dicts: [{'name': 'file.txt', 'content': 'file content'}]
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

        # 2. Prepare payload
        payload = {
            "message": f"Add/Update {file_name} for Round {round_num}",
            "content": encoded_content,
            "branch": "main" 
        }

        # 3. CRITICAL FIX: Get SHA for the specific file if updating in round 2
        current_sha = None
        if round_num == 2:
            current_sha = get_sha_of_latest_commit(repo_name, file_path=file_name)
        
        if current_sha:
            payload["sha"] = current_sha # Include file's SHA for updating

        # 4. Perform the API call
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_name}"

        response = requests.put(
            url,
            headers=headers,
            json=payload
        )

        if response.status_code not in [200, 201]:
             # Provide more context if the SHA was missing/wrong
             sha_info = f" with SHA: {current_sha}" if current_sha else ""
             raise Exception(f"Failed to push file '{file_name}'{sha_info}. Status code: {response.status_code}, Response: {response.text}")
        else:
             action = "Updated" if response.status_code == 200 else "Created"
             print(f"File '{file_name}' {action} successfully (Status {response.status_code}).")


def generate_code(prompt: str) -> str:
    api_base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise Exception("OPENAI_API_KEY environment variable is not set")
    
    if not api_base_url.endswith("/chat/completions"):
        api_url = f"{api_base_url}/chat/completions"
    else:
        api_url = api_base_url
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
    }
    
    response = requests.post(api_url, headers=headers, json=data)    
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

def write_code_using_llm():
    prompt = "give me five city name of India?"
    return generate_code(prompt)

if __name__ == "__main__":
    try:
        code = write_code_using_llm()
        print("Generated code:")
        print(code)
        
        with open("fibonacci_code.py", "w") as f:
            f.write(code)
        print("Code saved to fibonacci_code.py")
        
    except Exception as e:
        print(f"Error: {e}")

def round1(data):
  try:
    files_to_push = write_code_using_llm()
    
    repo_name = f"{data['task']}_{data['nonce']}"

    # CRITICAL: Uncomment these lines to create the repo and enable pages
    create_github_repo(repo_name) 
    enable_github_pages(repo_name) 

    # Push files to the newly created repo
    push_files_to_repo(repo_name, files_to_push, round_num=1)
    
    return {"message": "Round 1 processing complete", "repo_name": repo_name} 
  
  except Exception as e:
    print(f"Error during round1 processing: {e}") 
    return {"error": str(e)}

def round2(data: dict):
  try:
    # 1. Get the repo name from the previous round (assuming task/nonce remain same)
    repo_name = f"{data['task']}_{data['nonce']}"
    
    # 2. CRITICAL: The task server should send 'feedback' or 'evaluation_results' in the Round 2 JSON Request.
    # This information is VITAL for the LLM to know what to fix.
    feedback = data.get("evaluation_feedback", "Fix known issues and ensure all checks are passed.")

    # 3. Call the LLM to generate modified code
    # NOTE: You'd call a similar LLM function, but with a different prompt:
    # "The existing code is in {repo_name}. The feedback is: {feedback}. Provide the modified files only."
    
    # Placeholder for modified files (LLM should generate the fixes)
    files_to_modify = [
      {
        "name": "index.html",
        "content": "<h1>Fixed Hello World!</h1>\n<p>This is the Round 2 modified code.</p>" # LLM generated FIX
      },
    ]

    # 4. Push/Update files to the existing repo (push_files_to_repo handles the update by using the SHA)
    push_files_to_repo(repo_name, files_to_modify, round_num=2)
    
    return {"message": "Round 2 code modification complete", "repo_name": repo_name}

  except Exception as e:
    print(f"Error during round2 processing: {e}") 
    return {"error": str(e)}


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
          result = round2(data)
          return result
      else:
          return {"error": "Invalid round"}

if __name__ == "__main__":
  import uvicorn
  # NOTE: You must run the server with the GITHUB_USERNAME env var set:
  # e.g., GITHUB_TOKEN=... GITHUB_USERNAME=... uv run main.py
  uvicorn.run(app, host="0.0.0.0", port=8000)