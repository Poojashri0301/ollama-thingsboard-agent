# main.py
from config import AGENT_TYPE

if AGENT_TYPE == "ollama":
    from ollama_agent import OllamaTBAgent
    agent = OllamaTBAgent()
    agent_name = "Ollama"
else:
    from gemini_agent import GeminiTBAgent
    agent = GeminiTBAgent()
    agent_name = "Gemini"

print("\n========================================")
print(f"  ThingsBoard + {agent_name} Chat")
print("  Type 'exit' to quit")
print("========================================\n")

while True:
    question = input("You > ").strip()
    if question.lower() in ("exit", "quit"):
        break
    if not question:
        continue
    agent.ask(question)