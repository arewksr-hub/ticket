import discord
from discord.ext import commands
from discord import app_commands

TOKEN = "حط_توكن_بوتك"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ──────────────── عند تشغيل البوت ────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"تم تشغيل البوت: {bot.user}")

# ──────────────── زر إنشاء تكت ────────────────
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 إنشاء تكت", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user = interaction.user

        # تحقق هل عنده تكت
        for channel in guild.text_channels:
            if channel.name == f"ticket-{user.id}":
                await interaction.followup.send("❌ عندك تكت مفتوح بالفعل", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 تم إنشاء التكت",
            description="اكتب مشكلتك وسيتم الرد عليك قريبًا",
            color=discord.Color.green()
        )

        await channel.send(
            content=f"{user.mention}",
            embed=embed,
            view=CloseButton()
        )

        await interaction.followup.send(f"✅ تم إنشاء التكت: {channel.mention}", ephemeral=True)

# ──────────────── زر إغلاق التكت ────────────────
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 إغلاق التكت", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        await interaction.channel.send("⏳ جاري حذف التكت...")
        await interaction.channel.delete()

# ──────────────── أمر إرسال لوحة التكت ────────────────
@bot.tree.command(name="ticket", description="إرسال لوحة التكت")
async def ticket_panel(interaction: discord.Interaction):

    await interaction.response.defer()

    embed = discord.Embed(
        title="📩 نظام التذاكر",
        description="اضغط على الزر بالأسفل لإنشاء تكت",
        color=discord.Color.blue()
    )

    await interaction.followup.send(embed=embed, view=TicketButton())

# ──────────────── تشغيل البوت ────────────────
bot.run(TOKEN)
