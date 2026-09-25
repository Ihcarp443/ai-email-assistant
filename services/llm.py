# from langchain_google_genai import ChatGoogleGenerativeAI
import os
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
# from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv
load_dotenv()


class LLMService:
    def __init__(self):
        # self.llm = ChatGroq(
        #     model="openai/gpt-oss-20b",
        #     temperature=0,
        #     api_key=os.getenv("GROQ_API_KEY"),
        # )
        # self.llm =ChatHuggingFace(llm=HuggingFaceEndpoint(
        #     repo_id="google/gemma-4-31B-it",   
        #     huggingfacehub_api_token=os.getenv("HF_TOKEN")
        # ))
        self.llm = ChatOllama(
                model="llama3.1:latest",
                temperature=0,
            )

    def invoke(self, prompt: str):
        response = self.llm.invoke(prompt)
        return response.content
    
model = LLMService()

# llm = ChatHuggingFace(llm=HuggingFaceEndpoint(
#             repo_id="google/gemma-4-31B-it",   
#             huggingfacehub_api_token=os.getenv("HF_TOKEN")
#         ))
# llm = ChatGroq(
#             model="openai/gpt-oss-20b",
#             temperature=0,
#             api_key=os.getenv("GROQ_API_KEY"),
        # )

llm = ChatOllama(
        model="llama3.1:latest",
        temperature=0,
    )