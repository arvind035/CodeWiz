from urllib.parse import urlparse
from git import Repo, GitCommandError
import json
import re
import traceback
from llama_cpp import Llama
import datetime
from github import Github
import os
import subprocess
from fpdf import FPDF


class SubmitService:
    def __init__(self):
        self.model_base = "/home/adminuser/hackathon/models"
        self.GITHUB_TOKEN = "github_token"
        self.docu_string = ""

    def create_hash(self, user_input_link, req_type):

        # Load existing data if file exists
        if os.path.exists('data.json'):
            with open('data.json', 'r') as f:
                all_data = json.load(f)
        else:
            all_data = {}

        # Use a meaningful key instead of generic 'data'
        specific_key = f"{req_type}_{user_input_link[-30:]}"  # Example: "pdf_abc123"

        if specific_key in all_data:
            return specific_key, True

        # Save under that key
        all_data[specific_key] = {
            "user_input_link": user_input_link,
            "req_type": req_type,
            "status": "Ongoing",
            "data": "This is a dummy value for the hash creation process."
        }

        # Write updated data back
        with open('data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
    
        print(f"Creating hash for user_input_link: {user_input_link}, req_type: {req_type}")

        return specific_key, False
    

    def submit(self, user_input_link, req_type, user_input_language, specific_key=None):
        print(f"user_input_link: {user_input_link}, req_type: {req_type}")

        user_input_language = user_input_language.lower()

        if req_type == "REPO":
            repo_path = self.clone_repo(user_input_link)
            print("repo_path", repo_path)
            files = self.find_files(repo_path)
            print("Files found in the repository:", files)

 
            output_path = self.classify_path(files, user_input_language, "Meta-Llama-3.1-8B-Instruct-Q4_K_S.gguf")
            result = self.process_repo(output_path, specific_key, user_input_language)
            # self.update_data(specific_key, result)
            print("Processing as a repository link")
        else:
            print("Inside else")
            res = self.get_merge_request_changes(user_input_link)
            if not res:
                print("No changes found in the merge request.")
                return False
            result = self.get_data_from_model_for_mr(res)
            self.update_data(specific_key, result)

            return False
        return

    def classify_path(self, paths, language, model_name):

        llm = Llama(model_path=os.path.join(self.model_base, model_name), verbose=False, n_ctx=32768, n_batch=512, n_threads=32, use_mmap=False, use_mlock=True, chat_format="chatml", stop=["<|im_end|>"])

        def generate_text(
            prompt,
            max_tokens=4096,
            temperature=0.1,
            top_p=0.9,
            echo=False,
            stop=["#"],
            min_p=0.7
        ):
            print('Start time',datetime.datetime.now())
            output = llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=echo,
                min_p=min_p,
                stream=False,
            )
            print('End time',datetime.datetime.now())
            output_text = output["choices"][0]["text"].strip()
            
            return output_text
            
        def generate_prompt_from_template_classify(input: str, language: str) -> str:
            
            chat_prompt_template = f"""
                <|begin_of_text|><|start_header_id|>system<|end_header_id|>
                You are a helpful assistant.
                Assign type tags to the given paths from this list - [code, environment, config, others]. 
                Directories don't have any extension, they should be 'others'.
            
                Add tags in following format -
                [
                {{
                "file_path":"string",
                "type":"string"
                }},
                ...
                ]
                <|eot_id|><|start_header_id|>user<|end_header_id|>
                {input}
                <|eot_id|><|start_header_id|>assistant<|end_header_id|>
                # END OF INSTRUCTION
                """
            return chat_prompt_template

        prompt = generate_prompt_from_template_classify(paths, language)

        res = generate_text(prompt, max_tokens=4096)
        print('calssify_path response', res)
        return res

    def process_repo(self, output_path, specific_key, user_input_language):
        
        output_path, status = self.parse_response_2(output_path)
        print('output_path', output_path)
        code_json = {
            "files":[]
        }

        for path in output_path:

            try:
                print("Got...", path["file_path"])
                if(path["type"] == "code"):

                    print("Processing...", path["file_path"])
                    f = open(os.path.join("/", path["file_path"]))
                    code = str(f.read())
                    file_an_json, status = self.parse_response_2(self.analyze_file(str(code), user_input_language, "qwen2.5-coder-7b-instruct-q4_0.gguf"))
                    docu_json = json.dumps({key: file_an_json[key] for key in ["packages_used", "connected_modules", "functions", "simple_description", "classes"]})
                    self.docu_string = self.docu_string + f'''{path["file_path"]}\n{docu_json}\n'''
                    print('file_an_json', file_an_json)
                    file_an_json = file_an_json[0] if isinstance(file_an_json, list) and len(file_an_json) > 0 else file_an_json
                    file_an_json["module_name"] = path["file_path"]
                    code_json["files"].append({
                        "path": path["file_path"],
                        "analysis": file_an_json
                    })
                    self.update_repo_data(specific_key, code_json)
            except Exception as e:
                print(f"Error processing file {path['file_path']}: {e}")     
        else:
            res = self.create_document(self.docu_string, "Meta-Llama-3.1-8B-Instruct-Q4_K_S.gguf", specific_key)
            self.update_status_pdf(specific_key, res)
            self.docu_string = ""


        return code_json

    def parse_response_2(self, repo_content):
        try:
            print('repo_content', repo_content)
            content_match = re.search(r'[\[|\{][\S\s]*[\]|\}]', repo_content, re.DOTALL)
            print("content_match", content_match)
            if content_match:
                raw_json = content_match.group(0)

                try:
                    data_json = json.loads(raw_json)
                except json.JSONDecodeError as e:
                    raise ValueError("Invalid JSON format")
                
                return data_json, True
            else:
                raise ValueError("No valid JSON found in the response")
        except Exception as e:
            traceback.print_exc()
            return None, False

    def analyze_file(self, code, language, model_name):

        llm = Llama(model_path=os.path.join(self.model_base, model_name), verbose=False, n_ctx=32768, n_batch=512, n_threads=32, use_mmap=False, use_mlock=True, chat_format="chatml",stop=["<|im_end|>"], repeat_penalty=1.1)

        def generate_text(
            prompt,
            max_tokens=4096,
            temperature=0.1,
            top_p=0.9,
            echo=False,
            stop=["#"],
            min_p=0.0
        ):
            print('Start time',datetime.datetime.now())
            output = llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=echo,
                min_p=min_p,
                stream=False,
            )
            print('End time',datetime.datetime.now())
            output_text = output["choices"][0]["text"].strip()
            
            return output_text

        def generate_prompt_from_template_repo(input: str, language: str) -> str:
            
            chat_prompt_template = f"""
                <|im_start|>system
                You are a senior {language} code reviewer. Return only valid JSON in the specified format. Once Analyze whole generate response , don't repeat the same code.
                <|im_end|>
                <|im_start|>user
                Analyze the following code and provide your response strictly in JSON format with the following fields:

                - "module_name": Name of the module if identifiable.
                - "packages_used": List all third-party or built-in packages used in the code.
                - "connected_modules": List of any external or internal modules connected or imported.
                - "classes": Name and one-line description (if available) of all classes defined in the code.
                - "functions": Name and one-line description (if available) of all functions or methods.
                - "simple_description": A simple, layman-friendly explanation of what this module does.
                - "scope_of_optimization": Suggest or generate code changes that can improve efficiency or performance.
                - "refactoring_suggestions": Suggest improvements using best coding practices and cleaner structure.
                - "bugs_found": Identify bugs and spelling mistake.

                ### Output JSON Format ###
                {{
                "module_name": "string or null",
                "packages_used": ["package1", "package2"],
                "connected_modules": ["module1", "module2"],
                "classes": [
                    {{
                    "name": "ClassName",
                    "description": "One-line description"
                    }}
                ],
                "functions": [
                    {{
                    "name": "function_name",
                    "description": "One-line description"
                    }}
                ],
                "simple_description": "Layman-friendly module description",
                "scope_of_optimization": [
                    {{
                    "code snippet": "code",
                    "description": "what the optimization does"
                    }}
                ],
                "refactoring_suggestions": [
                    {{
                    "code snippet": "refactored code",
                    "description": "why it is better"
                    }}
                ],
                "bugs_found": [
                    {{
                    "description": "explanation of the bug or risky pattern"
                    }}
                ]
                }}

                Now analyze the following code:

                {input}
                <|im_end|>
                <|im_start|>assistant
                """

            return chat_prompt_template

        prompt = generate_prompt_from_template_repo(code, language)

        res = generate_text(prompt, max_tokens=4096)

        return res      



    def create_document(self, docu_string, model_name, specific_key=None):

        llm = Llama(model_path=os.path.join(self.model_base, model_name), verbose=False, n_ctx=32768, n_batch=512, n_threads=32, use_mmap=False, use_mlock=True, chat_format="chatml",stop=["<|im_end|>"], repeat_penalty=1.1)

        def generate_text(
            prompt,
            max_tokens=4096,
            temperature=0.1,
            top_p=0.9,
            echo=False,
            stop=["#"],
            min_p=0.0
        ):
            print('Start time',datetime.datetime.now())
            output = llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=echo,
                min_p=min_p,
                stream=False,
            )
            print('End time',datetime.datetime.now())
            output_text = output["choices"][0]["text"].strip()
            
            return output_text

        def generate_prompt_from_template_docu(docu_string: str) -> str:
            
            chat_prompt_template = \
                f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
                Consolidate the following details of multiple modules in a complete documentation of the whole repository. Do no delete any information.
                - Explain and format all the details as neccesary. Keep it module-wise, do not mix up.
                - Add relevant information if needed. Do not repeat any information.
                - Make a wholesome documentation with formatting. Maintain titles, header, subheaders, pointers.
                <|eot_id|><|start_header_id|>user<|end_header_id|>

                {docu_string}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
                """
            return chat_prompt_template
            
        prompt = generate_prompt_from_template_docu(docu_string)

        res = generate_text(prompt, max_tokens=4096)

        return res
    
      

    def get_merge_request_changes(self, mr_url):

        parsed = urlparse(mr_url)
        path_parts = parsed.path.strip('/').split('/')

        if len(path_parts) != 4 or path_parts[2].lower() != 'pull':
            print("❌ Invalid GitHub PR URL format.")
            return None

        repo_owner = path_parts[0]
        repo_name = path_parts[1]
        pull_number = int(path_parts[3])

        try:
            g = Github(self.GITHUB_TOKEN)
            repo = g.get_repo(f"{repo_owner}/{repo_name}")
            pull = repo.get_pull(pull_number)

            pr_data = {
                "repo": f"{repo_owner}/{repo_name}",
                "pull_request": {
                    "number": pull_number,
                    "title": pull.title,
                    "files": []
                }
            }
            for file in pull.get_files():
                file_diff = file.patch if file.patch else ""
                pr_data["pull_request"]["files"].append({
                    "filename": file.filename,
                    "status": file.status,
                    "diff": file_diff
                })

            return pr_data
        except Exception as e:
            print(f"❌ Error fetching PR data: {e}")
            return None
    
    def clone_repo(self, repo_url):
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        local_path = os.path.join('data',repo_name)

        if os.path.exists(os.path.join(local_path, '.git')):
            print(f"Repository already exists at: {local_path}")
            try:
                repo = Repo(local_path)
                origin = repo.remotes.origin
                origin.pull()
                print(f"Pulled latest changes for repository at: {local_path}")
            except GitCommandError as e:
                print(f"Error pulling repository: {e}")
            return local_path

        try:
            Repo.clone_from(repo_url, local_path)
            print(f"Repository cloned to: {local_path}")
            return local_path
        except Exception as e:
            print(f"Error cloning repository: {e}")
            return None
        

    def get_data_from_model_for_repo(self, repo_path):

        return {
            "optimization": "Optimized code for better performance.",
            "refactor": "Refactored code for better readability.",
            "bug_identification": "Identified potential bugs in the code.",
            "documentation": "Generated documentation for the codebase."
        }
    
    def get_data_from_model_for_mr(self, diff):
        
        model_name = "qwen2.5-14b-instruct-q4_0-00001-of-00003.gguf"
        llm = Llama(model_path=os.path.join(self.model_base, model_name), verbose=False, n_ctx=32768, n_batch=512, n_threads=32, use_mmap=False, use_mlock=True, chat_format="chatml", stop=["<|im_end|>"])

        def generate_text(
            prompt,
            max_tokens=4096,
            temperature=0.1,
            top_p=0.9,
            echo=False,
            stop=["#"],
            min_p=0.0
        ):
            print('Start time',datetime.datetime.now())
            output = llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=echo,
                min_p=min_p,
                stream=False,
            )
            print('End time',datetime.datetime.now())
            output_text = output["choices"][0]["text"].strip()
            
            return output_text

        def generate_prompt_from_template_mr(input: str, language: str) -> str:
            
            chat_prompt_template = f"""
                <|im_start|>system
                You are an expert {language} code reviewer. Analyze the Git Merge Request (MR) to provide your analysis.
                <|im_end|>
                <|im_start|>user
                Provide the following -

                1. Optimizations - Suggest improvements for readability, structure, or performance.
                2. Refactoring - Recommend refactoring if necessary (e.g., simplify logic, reduce duplication)
                3. Bugs - Identify bugs or potential issues (runtime errors, edge cases, API misuse, spelling mistakes etc.)
                4. Explanation - Provide the summary of changes in simple terms.

                ### Expected Output JSON Format ###
                    [
                        {{
                        "file_name": "string",
                        "Optimizations": ["suggestions"],
                        "Refactoring": ["suggestions"],
                        "Bugs": ["suggestions"],
                        "Explanation": "Description of changes present in the file"
                        }},
                        ...
                    ]

                The following are changes introduced in this MR -
        
                {input}
                <|im_end|>
                <|im_start|>assistant
                """

            chat_prompt_template1 = f"""
                <|im_start|>system
                You are an expert {language} code reviewer. Analyze the Git Merge Request (MR) differences to provide the following.
                <|im_end|>
                <|im_start|>user
                
                Analyze on following points - 

                1. Optimizations - Suggest improvements for readability, structure, or performance. Comment on code consistency, naming, and maintainability
                2. Refactoring - Recommend refactoring if necessary (e.g., simplify logic, reduce duplication)
                3. Bugs - Identify bugs or potential issues (runtime errors, edge cases, API misuse, spelling mistakes etc.)
                4. Explanation - Provide the change logs in simple terms (i.e., what changes or differences are present).

                ### Expected Output JSON Format ###
                    [
                        {{
                        "file_name": "string or null",
                        "Optimizations": [
                            {{
                            "Issue": "suggestion",
                            "description": "One-line description"
                            }}
                        ],
                        "Refactoring": [
                            {{
                            "Issue": "suggestion",
                            "description": "One-line description"
                            }}
                        ],
                        "Bugs": [
                            {{
                            "Issue": "suggestion",
                            "description": "One-line description"
                            }}
                        ],
                        "Explanation": "Layman-friendly description of changes"
                        }},
                        ...
                    ]

                The following code represents changes introduced in this MR -

                File: filename with change
                Diff: differences starts here
                + signifies added code
                - signifies removed code
                
                {input}
                <|im_end|>
                <|im_start|>assistant"""
            return chat_prompt_template1

        prompt = generate_prompt_from_template_mr(diff, "java")
        res = generate_text(prompt, max_tokens=4096)
        response = self.parsed_response(res)

        return response
    
    
    def parsed_response(self, mr_content):

        try:
            content_match = re.search(r'\[.*\]', mr_content, re.DOTALL)
            print("content_match", content_match)
            if content_match:
                raw_json = content_match.group(0)

                try:
                    data_json = json.loads(raw_json)
                except json.JSONDecodeError as e:
                    raise ValueError("Invalid JSON format")
                
                return data_json, True
            else:
                raise ValueError("No valid JSON found in the response")
        except Exception as e:
            traceback.print_exc()
            return None, False

    def find_files(self, path):
        
        repo_path = os.path.join("/home/adminuser/hackathon/flask-api/", path)
        command = f'find "{repo_path}" -not -path "*venv*" -not -path "*git*" -not -path "*pycache*" -not -path "*ReadME*"'

        print("Executing command:", command)

        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        print("Matching files:\n", result.stdout)

        return result.stdout.strip()
     

    def update_data(self, specific_key, model_data):
        
        # Load existing data
        if os.path.exists('data.json'):
            with open('data.json', 'r') as f:
                all_data = json.load(f)
        else:
            all_data = {}
            

        # Update the specific key with new data
        content = all_data[specific_key]
        content.update({
            "status": "Completed",
            "data": model_data
        })
        all_data[specific_key] = content

        # Write updated data back
        with open('data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"Updated data for key: {specific_key}")


    def update_repo_data(self, specific_key, model_data):
        
        # Load existing data
        if os.path.exists('data.json'):
            with open('data.json', 'r') as f:
                all_data = json.load(f)
        else:
            all_data = {}
            

        # Update the specific key with new data
        content = all_data[specific_key]
        content.update({
            "data": model_data
        })
        all_data[specific_key] = content

        # Write updated data back
        with open('data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"Updated data for key: {specific_key}")  

    def update_status_pdf(self, specific_key, pdf_content):
        
        # Load existing data
        if os.path.exists('data.json'):
            with open('data.json', 'r') as f:
                all_data = json.load(f)
        else:
            all_data = {}
            

        # Update the specific key with new data
        content = all_data[specific_key]
        content.update({
            "status": "Completed",  
            "pdf_content": str(pdf_content)
        })
        all_data[specific_key] = content

        # Write updated data back
        with open('data.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        print(f"Updated data for key: {specific_key}")  