import os

from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path

class LLMManager:
    def __init__(self) -> None:
        # .envファイルの読み込み
        dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
        load_dotenv(dotenv_path = dotenv_path)

        # API-KEYの設定
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=GOOGLE_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    def infer(self, prompt, tools=None):
        if tools == None :
            return self.gemini_model.generate_content(prompt)
        else :
            return self.gemini_model.generate_content(
                prompt, 
                tools=tools, 
                tool_config={"function_calling_config": {"mode": "ANY"}}
                )