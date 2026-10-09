from dotenv import load_dotenv
import anthropic

load_dotenv()
client = anthropic.Anthropic()

msg = client.messages.create(
    model="claude-haiku-5-5",
    max_tokens=200,
    messages=[{"role": "user", "content": "Give me 5 space-themed words as a JSON list."}],
)
print(msg.content[0].text)