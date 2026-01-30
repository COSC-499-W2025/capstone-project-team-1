from ollama import chat
from ollama import ChatResponse

response: ChatResponse = chat(
    model="lfm2.5-thinking:latest",
    messages=[
        {
            "role": "user",
            "content": "tell me about fc barcelona in 20 words",
        },
    ],
)
print(response["message"]["content"])
# or access fields directly from the response object
print(response.message.content)
