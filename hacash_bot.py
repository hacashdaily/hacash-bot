import os
import httpx
import base64
import json
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ============================================================
# CONFIGURATION
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "hacashdaily/hacash-ai-knowledge"
GITHUB_BRANCH = "development"

# ============================================================
# SYSTEM PROMPT
# ============================================================
SYSTEM_PROMPT = """You are HacashAI, the official AI assistant for the Hacash ecosystem.

Your mission: Answer users' questions about Hacash accurately, clearly, and in a natural conversational tone.

## Your Personality
- Warm and friendly — not formal, talk like a human
- Explain even complex technical topics in simple, fluid language
- Don't give unnecessarily long answers
- Never use phrases like "According to the official Whitepaper..."
- Get straight to the point
- Always reply in the same language the user writes in
- Never ask "Would you like me to explain?" — just explain directly

## Strict Rules
You CAN:
- Answer questions about Hacash
- Explain HAC, HACD, Channel Chain, mining, lending, wallet and other topics
- Break down complex technical concepts in plain language

You CANNOT:
- Generate information not found in official Hacash documentation
- Make price predictions or give investment advice
- Comment on other crypto projects
- Make up answers when you're not sure
- Ask permission before answering — just answer directly

## If a topic is not covered, say:
"I don't have official information on that. I'd rather say nothing than give you wrong information."

## Critical Facts
- HACD is NOT a standard NFT — it has intrinsic PoW value
- HAC has infinite supply but diminishing inflation — perpetual 1 HAC/block after Phase 3
- Channel Chain is NOT the same as Bitcoin Lightning Network
- Istanbul Upgrade activates after block 765,432 (~July 19, 2026)
- HIP20: After Istanbul, third parties CAN create tokens on Hacash — NOT live yet
- HIP-2, 3, 4 (lending) are in discussion — NOT implemented yet
- Used gas after Istanbul is burned, not paid to miners
- Never discuss price or investment"""

# ============================================================
# GITHUB RAG SYSTEM
# ============================================================

# Cache for knowledge files
knowledge_cache = {}

async def fetch_github_file(path: str) -> str:
    """Fetch a single file from GitHub"""
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
    """Fetch all MD files from knowledge base"""
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
    print(f"✅ Loaded {len(all_files)} knowledge files from GitHub")
    return all_files

def find_relevant_files(question: str, all_files: dict, max_files: int = 4) -> str:
    """Find most relevant files for the question using keyword matching"""
    question_lower = question.lower()
    
    # Keywords mapped to file priorities
    keyword_map = {
        "hacd": ["hacd", "diamond", "block diamond"],
        "hac": ["hac", "currency", "supply"],
        "mining": ["mining", "miner", "pow", "proof of work"],
        "channel": ["channel", "chain", "payment", "settlement"],
        "istanbul": ["istanbul", "upgrade", "hvm", "ast", "tex", "hip20", "actionguard"],
        "hvm": ["hvm", "virtual machine", "smart contract"],
        "ast": ["ast", "flow", "if else"],
        "tex": ["tex", "settlement", "atomic"],
        "bitcoin": ["bitcoin", "btc", "transfer"],
        "whitepaper": ["whitepaper", "abstract", "preface"],
        "glossary": ["glossary", "term", "definition"],
        "hip": ["hip", "proposal", "improvement"],
        "ethereum": ["ethereum", "eth", "evm", "solidity"],
        "privacy": ["privacy", "anonymous", "mixing"],
        "risk": ["risk", "attack", "51%", "security"],
    }
    
    # Score each file
    file_scores = {}
    for filename, content in all_files.items():
        score = 0
        content_lower = content.lower()
        
        # Check question keywords against file content
        for word in question_lower.split():
            if len(word) > 3 and word in content_lower:
                score += 1
        
        # Bonus for filename match
        for keyword, terms in keyword_map.items():
            for term in terms:
                if term in question_lower and keyword in filename.lower():
                    score += 5
        
        if score > 0:
            file_scores[filename] = score
    
    # Sort by score and take top files
    sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
    top_files = sorted_files[:max_files]
    
    # Combine content
    combined = ""
    for filename, score in top_files:
        combined += f"\n\n---\n## From: {filename}\n{all_files[filename][:2000]}"
    
    return combined

# ============================================================
# BOT HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Merhaba! Ben HacashAI — Hacash ekosistemi için resmi yapay zeka asistanıyım.\n\n"
        "Hacash, HAC, HACD, Channel Chain, madencilik, Istanbul yükseltmesi ve daha fazlası hakkında sorularını yanıtlayabilirim.\n\n"
        "Ne öğrenmek istersin? 🚀"
    )
    # Preload knowledge base
    await fetch_all_knowledge()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💡 Bana şunları sorabilirsin:\n\n"
        "• Hacash nedir?\n"
        "• HAC ile Bitcoin farkı nedir?\n"
        "• HACD nasıl madencilik yapılır?\n"
        "• Istanbul yükseltmesi nedir?\n"
        "• HVM nedir?\n"
        "• Channel Chain nasıl çalışır?\n"
        "• BTC'yi Hacash'a transfer edebilir miyim?\n\n"
        "Aklına gelen her soruyu sorabilirsin!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Fetch knowledge from GitHub
        all_files = await fetch_all_knowledge()
        
        # Find relevant files
        relevant_context = find_relevant_files(user_message, all_files)
        
        # Build prompt with context
        if relevant_context:
            context_prompt = f"\n\n## Relevant Knowledge Base Content:\n{relevant_context}"
        else:
            context_prompt = ""
        
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
                    "max_tokens": 1024,
                    "temperature": 0.7
                }
            )
            
            data = response.json()
            print(f"Groq status: {response.status_code}")
            
            if "choices" in data and len(data["choices"]) > 0:
                ai_response = data["choices"][0]["message"]["content"]
            elif "error" in data:
                print(f"Groq error: {data['error']}")
                ai_response = "Üzgünüm, şu an bir sorun yaşıyorum. Lütfen tekrar dene. 🙏"
            else:
                print(f"Unexpected response: {data}")
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
    
    print("🚀 HacashAI Bot with RAG starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
