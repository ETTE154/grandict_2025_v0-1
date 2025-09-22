from ollama import chat
from ollama import ChatResponse

response: ChatResponse = chat(model='exaone3.5:7.8b', messages=[
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
])
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)