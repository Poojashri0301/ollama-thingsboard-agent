# main.py
print("\n[Choice] Which AI Backend would you like to use?")
print("1. Gemini (Google AI)")
print("2. Ollama (Local AI)")
choice = input("Select (1/2, default: 2): ").strip()

if choice == "1":
    from gemini_agent import GeminiTBAgent
    agent = GeminiTBAgent()
    agent_name = "Gemini"
else:
    from ollama_agent import OllamaTBAgent
    from auth_service import get_ollama_models
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    
    print(f"\n[Ollama] Connecting to {OLLAMA_BASE_URL}...")
    models = get_ollama_models(OLLAMA_BASE_URL)
    
    selected_model = OLLAMA_MODEL
    if models:
        print("\nAvailable Ollama Models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
        
        try:
            model_choice = input(f"\nSelect a model (1-{len(models)}, default: {OLLAMA_MODEL}): ").strip()
            if model_choice:
                idx = int(model_choice) - 1
                if 0 <= idx < len(models):
                    selected_model = models[idx]
        except (ValueError, IndexError):
            print(f"Invalid selection. Using default: {OLLAMA_MODEL}")
    else:
        print(f"\n[Warning] No models found at {OLLAMA_BASE_URL}. Using default: {OLLAMA_MODEL}")

    agent = OllamaTBAgent(model_name=selected_model)
    agent_name = f"Ollama ({selected_model})"

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
    print("Agent > ", end="", flush=True)
    for chunk in agent.ask_stream(question):
        print(chunk, end="", flush=True)
    print("\n")