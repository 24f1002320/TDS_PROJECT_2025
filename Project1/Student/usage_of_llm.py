# # /// script
# # requires-python = ">=3.11"
# # dependencies = [
# #   "fastapi[standard]",
# #   "uvicorn",
# #   "requests",
# # ]
# # ///

# import requests
# import os


# # Use this proxy https://aipipe.org/openai/v1 with the correct endpoint
# api_base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
# api_key = os.getenv("OPENAI_API_KEY")  # Make sure to set your OpenAI API key in the environment variable

# def generate_code(prompt: str) -> str:
#     # Ensure we have the correct endpoint
#     if not api_base_url.endswith("/chat/completions"):
#         api_url = f"{api_base_url}/chat/completions"
#     else:
#         api_url = api_base_url
    
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}"
#     }
#     data = {
#         "model": "gpt-4o",
#         "messages": [
#             {
#                 "role": "user",
#                 "content": prompt
#             }
#         ],
#     }
    
#     print(f"Sending request to: {api_url}")  # Debug info
    
#     response = requests.post(api_url, headers=headers, json=data)    
#     if response.status_code == 200:
#         result = response.json()
#         return result['choices'][0]['message']['content']
#     else:
#         raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

# if __name__ == "__main__":
#     # Test with environment variables check
#     if not api_key:
#         print("Error: OPENAI_API_KEY environment variable is not set")
#         exit(1)
    
#     print(f"Using API base URL: {api_base_url}")
    
#     prompt = "Write a Python function that returns the Fibonacci sequence up to n. Give only the code, no explanation."
#     try:
#         code = generate_code(prompt)
#         print("Generated code successfully!")
        
#         with open("generated_code.py", "w") as f:
#             f.write(code)
#         print("Code saved to generated_code.py")
        
#     except Exception as e:
#         print(f"Error: {e}")