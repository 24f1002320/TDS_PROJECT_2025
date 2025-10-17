# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastapi[standard]",
#   "uvicorn",
#   "requests",
# ]
# ///

import os
import requests
import base64
import time
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Use this proxy https://aipipe.org/openai/v1 with the correct endpoint
api_base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
api_key = os.getenv("OPENAI_API_KEY")  # Make sure to set your OpenAI API key in the environment variable

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "24f1002320") 

def validate_secret(secret: str) -> bool:
    return secret == os.getenv("SecretKey")

def create_github_repo(repo_name: str):
    payload = {
        "name": repo_name,
        "private": False,
        "auto_init": True,
        "license_template": "mit",
    }
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github+json"
    }
    
    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 201:
        raise Exception(f"Failed to create repository '{repo_name}'. Status code: {response.status_code}. Response: {response.text}")
    else:
        print(f"Successfully created repository: {repo_name}")
        return response.json()

def enable_github_pages(repo_name: str):
    if not GITHUB_USERNAME:
        raise Exception("GITHUB_USERNAME environment variable is not set.")
        
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/pages"
    
    payload = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github+json"
    }

    print(f"Enabling GitHub Pages for: {repo_name}")
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code not in [201, 204]:
        if response.status_code == 409:
            print(f"GitHub Pages for {repo_name} already enabled.")
            return
        raise Exception(f"Failed to enable GitHub Pages. Status: {response.status_code}. Response: {response.text}")
    else:
        print(f"GitHub Pages enabled successfully for {repo_name}.")
        return response.json()

def get_sha_of_latest_commit(repo_name: str, file_path: str):
    if not GITHUB_USERNAME:
        return None

    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_path}?ref=main"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('sha')
    elif response.status_code == 404:
        return None
    else:
        raise Exception(f"Failed to get file SHA. Status: {response.status_code}. Response: {response.text}")

def push_files_to_repo(repo_name: str, files: list[dict], round_num: int):
    if not GITHUB_USERNAME:
        raise Exception("GITHUB_USERNAME environment variable is not set.")

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    for file in files:
        file_name = file.get("name")
        file_content = file.get("content")

        if not file_name or file_content is None:
            print(f"Skipping file due to missing name or content: {file}")
            continue

        # Base64 encode the content
        encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        
        # Prepare payload
        payload = {
            "message": f"Add/Update {file_name} for Round {round_num}",
            "content": encoded_content,
            "branch": "main" 
        }

        # Always get SHA for the file
        current_sha = get_sha_of_latest_commit(repo_name, file_path=file_name)
        
        if current_sha:
            payload["sha"] = current_sha
            print(f"File {file_name} exists, updating with SHA: {current_sha[:8]}...")
        else:
            print(f"File {file_name} is new, creating without SHA")

        # Push the file
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/contents/{file_name}"
        print(f"Pushing file: {file_name}")

        response = requests.put(url, headers=headers, json=payload)

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to push file '{file_name}'. Status: {response.status_code}, Response: {response.text}")
        else:
            action = "Updated" if response.status_code == 200 else "Created"
            print(f"File '{file_name}' {action} successfully!")

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

def write_code_using_llm(task_brief: str, round_num: int = 1, feedback: str = ""):
    if round_num == 1:
        prompt = f"""
        Create a complete web application for: {task_brief}
        
        The application should be a professional, working solution that includes:
        
        1. index.html - Main HTML file with a clean, modern interface
        2. README.md - Professional documentation with setup instructions
        3. script.js - JavaScript functionality
        4. style.css - CSS styling
        5. Any other necessary files for the application
        
        For a captcha solver, include:
        - Input for captcha image URL
        - Display area for the captcha image
        - Area to show solved text
        - Clean, user-friendly interface
        
        Return ONLY a JSON array where each object has:
        - "name": filename (e.g., "index.html")
        - "content": the complete file content
        
        Example format:
        [
          {{
            "name": "index.html",
            "content": "<!DOCTYPE html>..."
          }},
          {{
            "name": "README.md", 
            "content": "# Project..."
          }}
        ]
        
        Make sure the code is complete and runnable.
        """
    else:
        prompt = f"""
        Based on this feedback: {feedback}
        
        Improve and fix the existing code for: {task_brief}
        
        The previous implementation had issues that need to be addressed.
        Provide the complete updated files.
        
        Return ONLY a JSON array where each object has:
        - "name": filename (e.g., "index.html")
        - "content": the complete file content
        
        Make sure all issues from the feedback are resolved.
        """
    
    try:
        llm_response = generate_code(prompt)
        print("LLM Response received, parsing...")
        
        # Parse the JSON response from LLM
        # Sometimes LLM adds markdown code blocks, so we need to clean it
        cleaned_response = llm_response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]
            
        files = json.loads(cleaned_response)
        
        # Validate the file structure
        if not isinstance(files, list):
            raise ValueError("LLM response is not a list")
            
        for file in files:
            if "name" not in file or "content" not in file:
                raise ValueError("Invalid file structure in LLM response")
                
        print(f"Successfully parsed {len(files)} files from LLM")
        return files
        
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Raw LLM response: {llm_response}")
        # Fallback to basic files if LLM fails
        return get_fallback_files()

def get_fallback_files():
    """Fallback files in case LLM fails"""
    return [
        {
            "name": "index.html",
            "content": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Captcha Solver</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Captcha Solver</h1>
        <div class="input-section">
            <label for="captchaUrl">Enter Captcha Image URL:</label>
            <input type="url" id="captchaUrl" placeholder="https://example.com/captcha.png">
            <button onclick="solveCaptcha()">Solve Captcha</button>
        </div>
        <div class="result-section">
            <h3>Captcha Image:</h3>
            <div id="imageContainer"></div>
            <h3>Solved Text:</h3>
            <div id="solution"></div>
        </div>
    </div>
    <script src="script.js"></script>
</body>
</html>"""
        },
        {
            "name": "README.md",
            "content": """# Captcha Solver

A web application that solves captcha challenges from image URLs.

## Features
- URL-based captcha image input
- Automatic captcha solving
- Clean, responsive interface

## Usage
1. Open `index.html` in a web browser
2. Enter the URL of a captcha image
3. Click "Solve Captcha"
4. View the solved text

## Setup
No installation required. Just open the HTML file in a browser.

## License
MIT License"""
        },
        {
            "name": "script.js",
            "content": """async function solveCaptcha() {
    const url = document.getElementById('captchaUrl').value;
    const imageContainer = document.getElementById('imageContainer');
    const solutionDiv = document.getElementById('solution');
    
    if (!url) {
        alert('Please enter a valid URL');
        return;
    }
    
    // Display the captcha image
    imageContainer.innerHTML = `<img src="${url}" alt="Captcha Image" style="max-width: 300px;">`;
    
    // Simulate captcha solving (in real implementation, this would call an API)
    solutionDiv.innerHTML = '<p>Solving captcha... (This is a demo)</p>';
    
    setTimeout(() => {
        // Demo solution - in real implementation, this would be the actual solved text
        solutionDiv.innerHTML = '<p><strong>Solved:</strong> ABC123</p>';
    }, 2000);
}

// Handle Enter key in input field
document.getElementById('captchaUrl').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        solveCaptcha();
    }
});"""
        },
        {
            "name": "style.css",
            "content": """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f4f4f4;
    padding: 20px;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1 {
    text-align: center;
    margin-bottom: 30px;
    color: #2c3e50;
}

.input-section {
    margin-bottom: 30px;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 5px;
}

label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

input[type="url"] {
    width: 100%;
    padding: 10px;
    margin-bottom: 10px;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 16px;
}

button {
    background: #3498db;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
}

button:hover {
    background: #2980b9;
}

.result-section {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 5px;
}

#imageContainer {
    margin: 10px 0;
    padding: 10px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
}

#solution {
    margin: 10px 0;
    padding: 15px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    font-size: 18px;
}"""
        }
    ]
    

# def create_huggingface_space(repo_name: str, files: list[dict]):
#     HF_TOKEN = os.getenv("HF_TOKEN")
#     HF_USERNAME = "irfanhugginh"
    
#     if not HF_TOKEN:
#         raise Exception("HF_TOKEN environment variable not set")
    
#     # Create space
#     create_url = "https://huggingface.co/api/repos/create"
#     create_payload = {
#         "name": repo_name,
#         "type": "space",
#         "sdk": "static",
#         "private": False
#     }
    
#     headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    
#     response = requests.post(create_url, headers=headers, json=create_payload)
    
#     if response.status_code == 409:
#         print(f"Space {repo_name} already exists")
#     elif response.status_code not in [200, 201]:
#         raise Exception(f"Failed to create space: {response.status_code}")
    
    # Wait longer for Space initialization
    # print("Waiting for Space to initialize...")
    # time.sleep(20)  # Hugging Face needs more time
    
    # # DELETE existing files first (important!)
    # try:
    #     # Get existing files and delete them
    #     list_url = f"https://huggingface.co/api/spaces/{HF_USERNAME}/{repo_name}/tree/main"
    #     list_response = requests.get(list_url, headers=headers)
        
    #     if list_response.status_code == 200:
    #         existing_files = list_response.json()
    #         for file_info in existing_files:
    #             if file_info['type'] == 'file':
    #                 delete_url = f"https://huggingface.co/api/spaces/{HF_USERNAME}/{repo_name}/content/main/{file_info['path']}"
    #                 delete_response = requests.delete(delete_url, headers=headers)
    #                 if delete_response.status_code in [200, 201]:
    #                     print(f"Deleted existing file: {file_info['path']}")
    # except Exception as e:
    #     print(f"Note: Could not clear existing files: {e}")
    
    # # Upload NEW files with proper error handling
    # uploaded_count = 0
    # for file in files:
    #     file_name = file.get("name")
    #     file_content = file.get("content")
        
    #     if not file_name or file_content is None:
    #         continue
            
    #     upload_url = f"https://huggingface.co/api/spaces/{HF_USERNAME}/{repo_name}/content/main/{file_name}"
        
    #     headers_upload = {
    #         "Authorization": f"Bearer {HF_TOKEN}",
    #         "Content-Type": "text/plain"
    #     }
        
    #     try:
    #         upload_response = requests.put(upload_url, headers=headers_upload, data=file_content)
            
    #         if upload_response.status_code not in [200, 201]:
    #             print(f"❌ FAILED to upload {file_name}: {upload_response.status_code} - {upload_response.text}")
    #             # Don't continue - this is critical
    #             raise Exception(f"Failed to upload {file_name} to Hugging Face")
    #         else:
    #             print(f"✅ Uploaded {file_name} to Hugging Face Space")
    #             uploaded_count += 1
                
    #     except Exception as e:
    #         print(f"❌ Error uploading {file_name}: {e}")
    #         raise Exception(f"Hugging Face file upload failed: {e}")
    
    # print(f"✅ Successfully uploaded {uploaded_count}/{len(files)} files to Hugging Face")
    
    # return f"https://huggingface.co/spaces/{HF_USERNAME}/{repo_name}"
  

def round1(data):
    try:
        print("=== STARTING ROUND 1 ===")
        
        # Use LLM to generate code based on the task brief
        task_brief = data.get('brief', 'Create a captcha solver web application')
        files_to_push = write_code_using_llm(task_brief, round_num=1)
        
        repo_name = f"{data['task']}-{data['nonce']}"
        print(f"Repository name: {repo_name}")

        # Create repo and enable pages
        repo_info = create_github_repo(repo_name)
        print(f"Repository created: {repo_info.get('html_url', 'N/A')}")

        pages_info = enable_github_pages(repo_name)
        print("GitHub Pages configured")

        # Push files to GitHub
        push_files_to_repo(repo_name, files_to_push, round_num=1)
        print("All files pushed to GitHub successfully")
        
        # Create Hugging Face Space
        # huggingface_url = create_huggingface_space(repo_name,files_to_push)
        
        return {
            "message": "Round 1 processing complete", 
            "repo_name": repo_name,
            "repo_url": repo_info.get('html_url', ''),
            "pages_url": f"https://{GITHUB_USERNAME}.github.io/{repo_name}/",
            # "huggingface_url": huggingface_url,
            "files_created": len(files_to_push)
        } 
    
    except Exception as e:
        print(f"Error during round1 processing: {e}")
        return {"error": str(e)}
    
    except Exception as e:
        print(f"Error during round1 processing: {e}")
        return {"error": str(e)}

def round2(data: dict):
    try:
        print("=== STARTING ROUND 2 ===")
        repo_name = f"{data['task']}_{data['nonce']}"
        
        # Get feedback from the evaluation
        feedback = data.get("evaluation_feedback", "Fix issues and improve the implementation")
        task_brief = data.get('brief', 'Create a captcha solver web application')
        
        # Use LLM to generate improved code based on feedback
        files_to_modify = write_code_using_llm(task_brief, round_num=2, feedback=feedback)
        
        print(f"Updating {len(files_to_modify)} files based on feedback")
        push_files_to_repo(repo_name, files_to_modify, round_num=2)
        
        return {
            "message": "Round 2 code modification complete", 
            "repo_name": repo_name,
            "files_updated": len(files_to_modify),
            "feedback_applied": feedback[:100] + "..." if len(feedback) > 100 else feedback
        }

    except Exception as e:
        print(f"Error during round2 processing: {e}")
        return {"error": str(e)}

app = FastAPI(title="Captcha Solver Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the HTML frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Captcha Solver Agent"}

@app.post("/handle_task")
async def handle_task(data: dict):
    print(f"Received request: round={data.get('round')}, task={data.get('task')}")
    
    if not validate_secret(data.get("secret", "")):
        return {"error": "Invalid secret"}
    
    round_num = data.get("round")
    if round_num == 1:
        result = round1(data)
        return result
    elif round_num == 2:
        result = round2(data)
        return result
    else:
        return {"error": "Invalid round"}

@app.get("/test")
async def test_endpoint():
    """Test endpoint to check if server is running"""
    return {"status": "Server is running", "github_user": GITHUB_USERNAME}

# Optional: Add a frontend-specific endpoint
@app.get("/frontend")
async def frontend_info():
    return {
        "message": "Captcha Solver Agent Frontend",
        "endpoints": {
            "main": "/",
            "api": "/handle_task",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("Starting server with LLM integration...")
    print(f"GitHub Username: {GITHUB_USERNAME}")
    print(f"GitHub Token set: {'YES' if GITHUB_TOKEN else 'NO'}")
    print(f"OpenAI API Key set: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)