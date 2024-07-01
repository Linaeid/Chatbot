import asyncio
from typing import AsyncIterable
from decouple import config
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from pydantic import BaseModel, Field

# Create the app object
app = FastAPI()

# Message history
app.message_history = []

# Message history model
class MessageHistoryModel(BaseModel):
    message: str = Field(title='Message')

# Chat form
class ChatForm(BaseModel):
    chat: str = Field(title=' ', max_length=1000)

# SSE endpoint
@app.post('/api/sse/')
async def sse_ai_response(prompt: str = Form(...)) -> StreamingResponse:
    # Check if prompt is empty
    if not prompt:
        return StreamingResponse(empty_response(), media_type='text/event-stream')
    return StreamingResponse(ai_response_generator(prompt), media_type='text/event-stream')

# Empty response generator
async def empty_response() -> AsyncIterable[str]:
    # Send the message
    msg = 'data: \n\n'
    yield msg
    # Avoid the browser reconnecting
    while True:
        yield msg
        await asyncio.sleep(10)

# MistralAI response generator
async def ai_response_generator(prompt: str) -> AsyncIterable[str]:
    # Mistral client
    mistral_client = MistralClient(api_key=config('MISTRAL_API_KEY'))
    system_message = "You are a helpful chatbot. You will help people with answers to their questions."
    # Output variables
    output = f"**User:** {prompt}\n\n"
    msg = ''
    # Prompt template for message history
    prompt_template = "Previous messages:\n"
    for message_history in app.message_history:
        prompt_template += message_history.message + "\n"
    prompt_template += f"Human: {prompt}"
    # Mistral chat messages
    mistral_messages = [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content=prompt_template)
    ]
    # Stream the chat
    output += f"**Chatbot:** "
    for chunk in mistral_client.chat_stream(model="mistral-small", messages=mistral_messages):
        if token := chunk.choices[0].delta.content or "":
            # Add the token to the output
            output += token
            # Send the message
            msg = f'data: {output}\n\n'
            yield msg
    # Append the message to the history
    message = MessageHistoryModel(message=output)
    app.message_history.append(message)
    # Avoid the browser reconnecting
    while True:
        yield msg
        await asyncio.sleep(10)

@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse("React app goes here")
