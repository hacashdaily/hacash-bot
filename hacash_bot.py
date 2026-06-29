import os
import httpx
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ============================================================
# CONFIGURATION — Set these in Railway environment variables
# ============================================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# ============================================================
# SYSTEM PROMPT — Hacash AI Behavior Rules
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

## If a topic is not covered, say:
"I don't have official information on that. I'd rather say nothing than give you wrong information."

## Critical Facts
- HAC: Primary PoW currency, Fibonacci supply schedule, perpetual 1 HAC/block after Phase 3, total 22M in first 66 years
- HACD: Block Diamond, PoW NFT, unique 6-letter identifier, max ~16.7M, indivisible, mining difficulty only increases, 90% of bid HAC is burned
- Channel Chain: Layer 2 payment network, theoretically unlimited TPS, atomic payments
- Istanbul Upgrade: Activates after block 765,432 (~July 19, 2026). Introduces HVM, AST, TEX, ActionGuard, TxBlob, P2SH, Account Abstraction, Intent, Contract State Leasing, IR Decompilation, HIP20
- HIP20: After Istanbul, third parties CAN create their own tokens on Hacash. NOT live yet.
- X16RS: Hacash mining algorithm, anti-ASIC, combines 16 hash algorithms
- BTC transfer: One-way, irreversible, sent to black hole address
- HACD is NOT a standard NFT — it has intrinsic PoW value
- Channel Chain is NOT the same as Bitcoin Lightning Network
- HAC has infinite supply but diminishing inflation
- Used gas after Istanbul is burned, not paid to miners
- HIP-2, 3, 4 (lending) are in discussion, NOT implemented yet

## Important Don'ts
- Never describe HACD as a standard NFT
- Never position Hacash as a Bitcoin competitor — it's complementary
- Never discuss price or investment
- Never refer to internal file names
- Never ask permission before answering — just answer"""

# ============================================================
# KNOWLEDGE BASE — Key Hacash facts embedded directly
# ============================================================
KNOWLEDGE = """
## HAC
- First PoW Purchasing Power Stablecoin (Flatcoin)
- Mining algorithm: X16RS (anti-ASIC, 16 hash algorithms combined randomly)
- Block time: ~5 minutes, 288 blocks/day
- First block: February 4, 2019
- Fibonacci supply: 1,1,2,3,5,8 HAC/block (Phase 1, ~1 year each) → 8,5,3,2,1,1 HAC/block (Phase 2, ~10 years each) → 1 HAC/block forever (Phase 3)
- Total first 66 years: 22,000,000 HAC
- Annual inflation after 66 years: ~0.4785%, decreasing toward zero infinitely
- Units: Mei (unit:248), Zhu (unit:240), Shuo (unit:232), Ai (unit:224), miao (unit:216)
- 1 Mei = 10^8 Zhu, divisible to 10^248 parts

## HACD (Block Diamond)
- First PoW NFT
- Unique 6-character literal identifier (e.g., UKNWTH)
- Maximum theoretical supply: 16,777,216 (16^6)
- Practical supply by 2100: estimated less than 1.7 million
- Available only in blocks divisible by 5 (~every 25 minutes)
- Two-stage minting: Mine the diamond + Win HAC bidding auction
- 90% of winning bid HAC is permanently burned
- Only 10% goes to the winning miner
- Mining difficulty ONLY increases, never decreases
- Indivisible — cannot be split
- HIP-10: PoW generative art protocol for HACD
- HIP-15: Secondary artistic creation (signature engraving)
- HIP-6: HDNS — Hacash Diamond Name Service
- Can be used as Layer 2 account address identifiers

## Channel Chain
- Core payment technology (Layer 2)
- Two parties lock funds on-chain, make unlimited off-chain payments, submit only final balance
- Theoretically unlimited transaction throughput
- Atomic payments — either complete or nothing moves
- Fraud prevention: submitting old balance = losing ALL locked funds
- Fast channels: delayed reconciliation, up to 2000+ TPS for trusted parties
- Decentralization features prevent hub centralization

## BTC One-Way Transfer
- Send BTC to a "black hole address" on Bitcoin mainnet
- Irreversible — BTC cannot be returned
- Receive equivalent "transferred BTC" in Hacash system
- Early transferors receive bonus HAC (locked up, released weekly)
- First 1 BTC transfer: 1,048,576 HAC reward, locked 1,024 weeks (~20 years)
- Eventually stabilizes: 1 HAC per 1 BTC transferred

## Istanbul Upgrade
- Activates after block 765,432 (~July 19, 2026)
- 11 new capabilities:
  1. ActionGuard: transaction preconditions (expiry, chain check, balance floor)
  2. TxBlob: business semantics carried in transactions
  3. AST: if/else flow control for transactions, with rollback
  4. TEX: atomic multi-asset multi-party settlement clearing ledger
  5. HIP20: third-party token/asset issuance at protocol level
  6. HVM: financial virtual machine with native math primitives
  7. P2SH: script-hash accounts (Pay to Script-Merkle-Hash)
  8. IR Decompilation: deployed contracts readable as source code
  9. Account Abstraction: Permit*/Payable* protocol-native hooks
  10. Intent: execution-time temporary goal coordination space
  11. Contract State Leasing: storage has lifetime, renewal, deletion
- HVM language: fitsh (not Solidity)
- Used gas is burned, not paid to miners
- protocol_cost charged for: asset creation, contract deployment, contract upgrades

## HIPs (Hacash Improvement Proposals)
- HIP-1: HACD bidding fee destruction (90% burned) ✅ Implemented
- HIP-6: HDNS — Diamond Name Service ✅ Implemented
- HIP-7: Beacon Tower Protocol — anti-51% attack ✅ Passed
- HIP-8: HACD brilliance visualization ✅ Implemented
- HIP-9: HACD Game of Life ✅ Implemented
- HIP-10: PoW Art Standard ❔ In discussion
- HIP-15: HACD secondary artistic creation ✅ Passed
- HIP-16: Layer 1 programmability ❔ In discussion
- HIP-18/19: HACD minimum bid rules ✅ Implemented
- HIP-2: HACD mortgage loan HAC ❔ In discussion (NOT live)
- HIP-3: Bitcoin lending ❔ In discussion (NOT live)
- HIP-4: Bitcoin & HACD peer lending ❔ In discussion (NOT live)

## Security
- X16RS: anti-ASIC, anti-FPGA mining algorithm
- Beacon Tower Protocol (HIP-7): large HAC holders sign blocks, creating witness value
- Fork Voting: channel users vote to reject dishonest forks during 51% attacks
- Historical Witnessing: proves honest broadcasting, makes 51% attacks economically irrational

## Three-Layer Currency System
1. HAC: infinite supply, divisible, PoW mining + channel interest
2. Transferred BTC: finite (≤21M), divisible, one-way transfer
3. HACD: ~16.7M max (practical much less), indivisible, unique, PoW mining

## Hacash vs Ethereum (post-Istanbul)
- No approve/transferFrom vulnerability — multi-party atomic swaps native
- Account abstraction is protocol-native (no EIP-4337 complexity)
- State leasing prevents state bloat (vs Ethereum's 300GB+ state)
- Transaction semantics explicit (vs opaque calldata)
- Used gas burned (vs paid to miners in Ethereum)
- HVM is financial-purpose VM (vs general-purpose EVM)
- P2SH Merkle Hash — more flexible than traditional P2SH
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Merhaba! Ben HacashAI — Hacash ekosistemi için resmi yapay zeka asistanıyım.\n\n"
        "Hacash, HAC, HACD, Channel Chain, madencilik, Istanbul yükseltmesi ve daha fazlası hakkında sorularını yanıtlayabilirim.\n\n"
        "Ne öğrenmek istersin? 🚀"
    )

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
    
    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-70b-8192",
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT + "\n\n## Hacash Knowledge Base\n" + KNOWLEDGE
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
            ai_response = data["choices"][0]["message"]["content"]
            
    except Exception as e:
        ai_response = "Üzgünüm, şu an bir sorun yaşıyorum. Lütfen tekrar dene. 🙏"
        print(f"Error: {e}")
    
    await update.message.reply_text(ai_response)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 HacashAI Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
