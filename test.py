import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def main():
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )
    chat_template = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful AI assistant named {ai_name}."),
            ("human", "Hello, my name is {user_name}!"),
            ("human", "{user_query}"),
        ]
    )

    formatted_prompt = chat_template.format_messages(
        ai_name="Gemini",
        user_name="Alice",
        user_query="What's the weather like today?",
    )

    response = model.invoke(formatted_prompt)

    print(response.content)


if __name__ == "__main__":
    main()
