from langchain_google_genai import ChatGoogleGenerativeAI
import os
class LLMService:

    def __init__(self):

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
        )

    def invoke(self, prompt: str):

        response = self.llm.invoke(prompt)

        return response.content


model = LLMService()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)