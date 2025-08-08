import openai
from backend.config import EMBEDDING_DEPLOYMENT,GPT_DEPLOYMENT
#AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, EMBEDDING_DEPLOYMENT, GPT_DEPLOYMENT,API_VERSION
import os


os.environ['AZURE_OPENAI_API_KEY'] = os.getenv("AZURE_OPENAI_API_KEY")  # Set in your env or .env file
os.environ['AZURE_OPENAI_ENDPOINT'] = os.getenv("AZURE_OPENAI_ENDPOINT")
os.environ['API_VERSION'] = os.getenv("API_VERSION") 


client = openai.AzureOpenAI(
    api_key=os.environ['AZURE_OPENAI_API_KEY'],
    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
    api_version=os.environ['API_VERSION']
)


def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model=EMBEDDING_DEPLOYMENT
    )
    return response.data[0].embedding


def chat_completion(messages, model: str = GPT_DEPLOYMENT, temperature: float = 0.2):
    # Azure OpenAI chat completions v1+[9]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

def generate_image_url(prompt: str, size: str = "1024x1024") -> str:
    # If you have an Azure image generation deployment, call it here.
    # Placeholder returns empty string to avoid runtime error if not configured.
    # You can integrate Azure AI Vision or external service as needed.
    return ""
