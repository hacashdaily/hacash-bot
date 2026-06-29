import os
import httpx
import base64
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "hacashdaily/hacash-ai-knowledge"
GITHUB_BRANCH = "development"

SYSTEM_PROMPT = """You are HacashAI, created by Hacash Daily — the official Hacash ecosystem media and development team.

Your mission: Answer questions about Hacash accurately and in a natural conversational tone.

## Personality
- Warm and friendly, talk like a human
- Explain complex topics simply
- Always reply in the same language the user writes in
- Never say "According to the official Whitepaper"
- Get straight to the point

## Rules
- NEVER give price predictions or investment advice
- NEVER mention unknown software: Hacash Miner, CGMiner, EasyMiner, MinerGate, GUI Miner — these DO NOT support Hacash
- NEVER recommend ASIC hardware — X16RS is specifically ANTI-ASIC
- NEVER recommend specific mining pool names — they change frequently
- NEVER say you were made by Anthropic, OpenAI or any AI company
- If asked who made you: "I was created by Hacash Daily"
- If topic not covered: "I don't have official information on that."

## HAC Mining Facts (ALWAYS use these exact facts)
- Algorithm: X16RS — anti-ASIC, anti-FPGA, combines 16 hash algorithms randomly
- Official software: Hacash fullnode only — https://github.com/hacash/fullnode
- Mining options: CPU solo mining via fullnode, or join a community mining pool (GPU supported by community tools)
- HACD mining: NO pool available — solo mining only via fullnode
- Block time: ~5 minutes

## Identity
- Name: HacashAI
- Creator: Hacash Daily
- Purpose: Official AI assistant for the Hacash ecosystem"""

knowledge_cache = {}

async def fetch_github_file(path: str) -> str:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            return content
        return ""

async def fetch_all_knowledge() -> dict:
    global knowledge_cache
    if knowledge_cache:
        return knowledge_cache

    folders = [
        "knowledge/whitepaper",
        "knowledge/glossary",
        "knowledge/hac",
        "knowledge/hacd",
        "knowledge/mining",
        "knowledge/hips",
        "knowledge/specifications",
        "knowledge/examples"
    ]

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    all_files = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for folder in folders:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{folder}?ref={GITHUB_BRANCH}"
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                files = response.json()
                for file in files:
                    if file["name"].endswith(".md"):
                        content = await fetch_github_file(file["path"])
                        if content:
                            all_files[file["name"]] = content

    knowledge_cache = all_files
    print(f"Loaded {len(all_files)} knowledge files from GitHub")
    return all_files

def find_relevant_files(question: str, all_files: dict, max_files: int = 4) -> str:
    question_lower = question.lower()

    keyword_map = {
        "hacd": ["hacd", "diamond", "block diamond", "elmas"],
        "hac": ["hac", "currency", "supply", "para"],
        "mining": ["mining", "miner", "pow", "madenci", "madencilik"],
        "channel": ["channel", "chain", "payment", "kanal", "ödeme"],
        "istanbul": ["istanbul", "upgrade", "hvm", "ast", "tex", "hip20", "actionguard", "yükseltme"],
        "hvm": ["hvm", "virtual machine", "sanal makine"],
        "bitcoin": ["bitcoin", "btc", "transfer"],
        "hip": ["hip", "proposal", "öneri"],
        "ethereum": ["ethereum", "eth", "evm", "solidity"],
        "privacy": ["privacy", "anonymous", "gizlilik"],
        "risk": ["risk", "attack", "saldırı", "güvenlik"],
        "glossary": ["nedir", "ne demek", "tanım"],
    }

    file_scores = {}
    for filename, content in all_files.items():
        score = 0
        content_lower = content.lower()

        for word in question_lower.split():
            if len(word) > 3 and word in content_lower:
                score += 1

        for keyword, terms in keyword_map.items():
            for term in terms:
                if term in question_lower and keyword in filename.lower():
                    score += 5

        if score > 0:
            file_scores[filename] = score

    sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    top_files = sorted_files[:max_files]

    combined = ""
    for filename, score in top_files:
        combined += f"\n\n---\n## Source: {filename}\n{all_files[filename][:2000]}"

    return combined

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Merhaba! Ben HacashAI — Hacash Daily tarafından geliştirilen resmi Hacash AI asistanıyım.\n\n"
        "Hacash, HAC, HACD, Channel Chain, madencilik, Istanbul yükseltmesi ve daha fazlası hakkında sorularını yanıtlayabilirim.\n\n"
        "Ne öğrenmek istersin? 🚀"
    )
    await fetch_all_knowledge()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 Bana şunları sorabilirsin:\n\n"
        "• Hacash nedir?\n"
        "• HAC ile Bitcoin farkı nedir?\n"
        "• HACD nasıl madencilik yapılır?\n"
        "• Istanbul yükseltmesi nedir?\n"
        "• HVM nedir?\n"
        "• Channel Chain nasıl çalışır?\n\n"
        "Aklına gelen her soruyu sorabilirsin!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    try:
        all_files = await fetch_all_knowledge()
        relevant_context = find_relevant_files(user_message, all_files)

        context_prompt = f"\n\n## Knowledge Base:\n{relevant_context}" if relevant_context else ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT + context_prompt
                        },
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    "max_tokens": 800,
                    "temperature": 0.3
                }
            )

            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                ai_response = data["choices"][0]["message"]["content"]
            elif "error" in data:
                print(f"Groq error: {data['error']}")
                ai_response = "Üzgünüm, şu an bir sorun yaşıyorum. Lütfen tekrar dene. 🙏"
            else:
                ai_response = "Üzgünüm, şu an bir sorun yaşıyorum. Lütfen tekrar dene. 🙏"

    except Exception as e:
        ai_response = "Üzgünüm, şu an bir sorun yaşıyorum. Lütfen tekrar dene. 🙏"
        print(f"Error: {e}")

    await update.message.reply_text(ai_response)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("HacashAI Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
 
