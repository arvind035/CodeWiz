import os
import urllib.request
from llama_cpp import Llama
import datetime
#from pdflatex import PDFLaTeX
from fpdf import FPDF

class Coder:
    def __init__(self):
        self.model_base = "/home/adminuser/hackathon/models"
        self.model_name = "codellama-7b-instruct.Q4_0.gguf"

    def coder(self, language, question: str) -> str:

        llm = Llama(model_path=os.path.join(self.model_base, self.model_name), verbose=False, n_ctx=32768, n_batch=512, n_threads=32, use_mmap=False, use_mlock=True, chat_format="chatml", repeat_penalty=1.1)

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
                stop=["# END OF CODE"]
            )
            print('End time',datetime.datetime.now())
            output_text = output["choices"][0]["text"].strip()
            
            return output_text

        def generate_prompt_from_template_coder(input: str, language: str) -> str:
            
            
            chat_prompt_template = f"""
                [INST] 
                <<SYS>>        
                You are an expert {language} developer. Who writes consistent, optimized and well commented code.
            
                Your task is to code for the following request.
                - In case of code unrelated requests, reply "I don't understand, Please give me code requests."


                Request - 
                <</SYS>>
                {input}
                [/INST]
                # END OF INSTRUCTION"""
            return chat_prompt_template

        prompt = generate_prompt_from_template_coder(question, language)

        res = generate_text(prompt, max_tokens=4096)

        return res