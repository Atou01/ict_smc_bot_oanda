import os
import discord
from discord import app_commands
import openai
import yaml
import json
import pathlib
import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parents[2] / ".env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("OPENAI_API_KEY not set")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")
SHARED_STATE_PATH = os.path.join(
    os.path.dirname(__file__), "../../logs/shared_state.json"
)


# --- Chargement config ---
def load_config():
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("discord_llm", {})


def get_env_or_config(key, config, env_var=None):
    cfg_value = config.get(key)
    if env_var and os.getenv(env_var):
        return os.getenv(env_var)
    if cfg_value and "${OPENAI_API_KEY}" in str(cfg_value):
        return os.getenv("OPENAI_API_KEY")
    return cfg_value


def read_shared_state():
    try:
        with open(SHARED_STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


class LLMDiscordBot(discord.Client):
    def __init__(self, channel_id, allowed_users, openai_api_key, gpt_model, **kwargs):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.channel_id = int(channel_id)
        self.allowed_users = set(str(uid) for uid in allowed_users)
        # Correction : ne jamais transmettre le placeholder littéral à openai.api_key
        if openai_api_key == "${OPENAI_API_KEY}":
            openai_api_key = os.getenv("OPENAI_API_KEY")
            print("[WARN][LLMDiscordBot] Correction de la clé OpenAI: le placeholder YAML a été remplacé par la vraie valeur d'environnement.")
        openai.api_key = openai_api_key
        self.gpt_model = gpt_model

    async def setup_hook(self):
        # Enregistre les commandes slash
        await self.tree.sync()

    async def on_ready(self):
        print(
            f"[Discord LLM Bot] Connecté en tant que {self.user} (ID: {self.user.id})"
        )
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send(
                "🤖 LLM Discord Bot en ligne. Utilisez la commande /ask pour discuter avec GPT-4 !"
            )


bot_config = load_config()
discord_token = get_env_or_config("token", bot_config, env_var="DISCORD_LLM_BOT_TOKEN")
channel_id = get_env_or_config("channel_id", bot_config)
allowed_users = bot_config.get("allowed_users", [])
gpt_model = bot_config.get("gpt_model", "gpt-4")

bot = LLMDiscordBot(channel_id, allowed_users, OPENAI_KEY, gpt_model)


# --- Commande /ask ---
@bot.tree.command(name="ask", description="Pose une question à GPT-4")
@app_commands.describe(question="Ta question à GPT-4")
async def ask(interaction: discord.Interaction, question: str):
    print(f"[DEBUG] User ID reçu: {interaction.user.id}")
    print(f"[DEBUG] Allowed users: {bot.allowed_users}")
    if bot.allowed_users and str(interaction.user.id) not in bot.allowed_users:
        # Vérifie si une réponse a déjà été envoyée
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "⛔️ Tu n'es pas autorisé à utiliser cette commande.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "⛔️ Tu n'es pas autorisé à utiliser cette commande.", ephemeral=True
            )
        return
    await interaction.response.defer(thinking=True)
    try:
        response = openai.ChatCompletion.create(
            model=bot.gpt_model,
            messages=[{"role": "user", "content": question}],
            max_tokens=800,
            temperature=0.7,
        )
        answer = response.choices[0].message["content"]
        await interaction.followup.send(f"**Q:** {question}\n**GPT-4 :** {answer}")
    except Exception as e:
        await interaction.followup.send(f"❌ Erreur lors de la requête LLM : {e}")


# --- Commande /state ou /strategie ---
@bot.tree.command(name="strategie", description="Affiche la stratégie actuelle du bot")
async def strategie(interaction: discord.Interaction):
    print(f"[DEBUG] User ID reçu: {interaction.user.id}")
    print(f"[DEBUG] Allowed users: {bot.allowed_users}")
    if bot.allowed_users and str(interaction.user.id) not in bot.allowed_users:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "⛔️ Tu n'es pas autorisé à utiliser cette commande.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                "⛔️ Tu n'es pas autorisé à utiliser cette commande.", ephemeral=True
            )
        return
    state = read_shared_state()
    strat = state.get("strategy", "Aucune stratégie détectée.")
    mode = state.get("mode", "Inconnu")
    bot_on = state.get("bot_on", False)
    txt = f"**Mode :** {mode}\n**Bot actif :** {'Oui' if bot_on else 'Non'}\n**Stratégie :** {strat}"
    await interaction.response.send_message(txt)


# --- Préparation pour ajout de boutons ou autres commandes ---
# (Structure prête à accueillir des app_commands ou views discord.ui plus tard)

if __name__ == "__main__":
    if not discord_token or not channel_id or not openai_api_key:
        print(
            "[ERREUR] Merci de renseigner 'token', 'channel_id', 'openai_api_key' dans config.yaml ou via variables d'environnement."
        )
        exit(1)
    bot.run(discord_token)
