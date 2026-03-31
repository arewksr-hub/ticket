"""
🎫 Premium Ticket Bot - Professional Support System
Developer: Abdulaziiz
"""
import discord
from discord import app_commands, ui, ButtonStyle, TextStyle, SelectOption
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from dotenv import load_dotenv
from typing import Optional, Dict, List
import json

load_dotenv()

# ═══════════════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════════════
TOKEN = os.getenv('DISCORD_TOKEN', '')
GUILD_ID = int(os.getenv('GUILD_ID', '0') or '0')
TICKET_CATEGORY_ID = int(os.getenv('TICKET_CHANNEL_ID', '0') or '0')
STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID', '0') or '0')
AUTO_ROLE_ID = int(os.getenv('AUTO_ROLE_ID', '0') or '0')
ADMIN_LOG_CHANNEL_ID = 1487807256622796902

# 🎨 Premium Colors
COLORS = {
    'primary': 0x5865F2,      # Discord Blurple
    'success': 0x57F287,      # Green
    'danger': 0xED4245,         # Red
    'warning': 0xFEE75C,       # Yellow
    'info': 0x5865F2,          # Blue
    'premium': 0xEB459E,        # Pink
    'gold': 0xFFD700,           # Gold
    'dark': 0x23272A,           # Dark
    'embed_bg': 0x2C2F33       # Embed Background
}

# 💾 Storage
active_tickets: Dict[int, dict] = {}
ticket_counter: int = 0
ticket_types = {
    'support': {'name': '🎫 تذكرة دعم', 'emoji': '🎫', 'color': COLORS['info'], 'desc': 'للمشاكل التقنية والطلبات العامة'},
    'inquiry': {'name': '💬 استفسار', 'emoji': '�', 'color': COLORS['success'], 'desc': 'لأي سؤال أو استفسار'},
    'delivery': {'name': '📦 استلام منتج', 'emoji': '�', 'color': COLORS['gold'], 'desc': 'لمتابعة استلام طلبك'}
}

# ═══════════════════════════════════════════════════════════════
# 🎨 EMBED BUILDER
# ═══════════════════════════════════════════════════════════════
class PremiumEmbed:
    @staticmethod
    def create(title: str, description: str = "", color: int = COLORS['primary'], 
               thumbnail: str = None, image: str = None, footer_text: str = None,
               author_name: str = None, author_icon: str = None) -> discord.Embed:
        """Create a premium styled embed"""
        embed = discord.Embed(
            title=f"{title}",
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if image:
            embed.set_image(url=image)
        if footer_text:
            embed.set_footer(text=footer_text, icon_url="https://cdn.discordapp.com/emojis/1038306783263641710.png")
        else:
            embed.set_footer(text="🎫 Premium Ticket System | Dev: Abdulaziiz", 
                           icon_url="https://cdn.discordapp.com/emojis/1038306783263641710.png")
        
        if author_name:
            embed.set_author(name=author_name, icon_url=author_icon)
            
        return embed
    
    @staticmethod
    def success(title: str, description: str = "") -> discord.Embed:
        return PremiumEmbed.create(f"✅ {title}", description, COLORS['success'])
    
    @staticmethod
    def error(title: str, description: str = "") -> discord.Embed:
        return PremiumEmbed.create(f"❌ {title}", description, COLORS['danger'])
    
    @staticmethod
    def info(title: str, description: str = "") -> discord.Embed:
        return PremiumEmbed.create(f"ℹ️ {title}", description, COLORS['info'])
    
    @staticmethod
    def warning(title: str, description: str = "") -> discord.Embed:
        return PremiumEmbed.create(f"⚠️ {title}", description, COLORS['warning'])
    
    @staticmethod
    def premium(title: str, description: str = "") -> discord.Embed:
        return PremiumEmbed.create(f"💎 {title}", description, COLORS['premium'])

# ═══════════════════════════════════════════════════════════════
# 🎫 TICKET TYPE SELECT
# ═══════════════════════════════════════════════════════════════
class TicketTypeSelect(ui.Select):
    def __init__(self):
        options = [
            SelectOption(
                label=info['name'],
                value=ticket_type,
                emoji=info['emoji'],
                description=info.get('desc', f"فتح تذكرة {info['name']}")
            )
            for ticket_type, info in ticket_types.items()
        ]
        super().__init__(placeholder="🎯 اختر نوع التذكرة...", options=options, custom_id="ticket_type_select")
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ticket_type = self.values[0]
        await TicketManager.create_ticket(interaction, ticket_type)

class TicketTypeView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

# ═══════════════════════════════════════════════════════════════
# 🎫 TICKET MANAGER
# ═══════════════════════════════════════════════════════════════
class TicketManager:
    @staticmethod
    async def create_ticket(interaction: discord.Interaction, ticket_type: str = 'support'):
        """Create a premium ticket"""
        global ticket_counter
        
        try:
            guild = interaction.guild
            user = interaction.user
            ticket_counter += 1
            ticket_info = ticket_types.get(ticket_type, ticket_types['support'])
            
            # Check existing ticket
            safe_name = "".join(c for c in user.name if c.isalnum() or c in '-_').lower()
            for ch in guild.text_channels:
                if ch.name.startswith(f"ticket-{safe_name}"):
                    await interaction.followup.send(
                        embed=PremiumEmbed.error("تذكرة موجودة", 
                            f"عندك تذكرة مفتوحة بالفعل: {ch.mention}"),
                        ephemeral=True
                    )
                    return
            
            category = guild.get_channel(TICKET_CATEGORY_ID)
            staff_role = guild.get_role(STAFF_ROLE_ID)
            
            # Premium Permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    attach_files=True, embed_links=True, add_reactions=True
                )
            }
            
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    manage_messages=True, manage_channels=True, attach_files=True,
                    embed_links=True, add_reactions=True
                )
            
            # Create Premium Channel
            ticket_ch = await guild.create_text_channel(
                name=f"ticket-{safe_name}-{ticket_counter:04d}",
                category=category,
                overwrites=overwrites,
                topic=f"🎫 #{ticket_counter:04d} | {ticket_info['emoji']} {ticket_info['name']} | العميل: {user.display_name}"
            )
            
            # Store Data
            active_tickets[ticket_ch.id] = {
                "user_id": user.id,
                "user_name": user.name,
                "ticket_type": ticket_type,
                "status": "open",
                "created_at": datetime.now().isoformat(),
                "ticket_number": ticket_counter
            }
            
            # Premium Welcome Embed
            welcome_embed = PremiumEmbed.create(
                title=f"{ticket_info['emoji']} تذكرة #{ticket_counter:04d}",
                description=(
                    f"**مرحباً {user.mention} 👋**\n\n"
                    f"تم إنشاء تذكرتك بنجاح!\n"
                    f"**النوع:** {ticket_info['emoji']} {ticket_info['name']}\n\n"
                    f"📝 **صف مشكلتك بوضوح** وسيقوم فريق الدعم بالرد عليك في أقرب وقت.\n\n"
                    f"⏱️ **وقت الاستجابة:** عادةً خلال 1-24 ساعة"
                ),
                color=ticket_info['color'],
                thumbnail=user.display_avatar.url if user.display_avatar else None,
                footer_text=f"🆔 Ticket #{ticket_counter:04d} | {ticket_info['name']}"
            )
            
            welcome_embed.add_field(
                name="📊 معلومات التذكرة",
                value=(
                    f"👤 **العميل:** {user.mention}\n"
                    f"🎫 **الرقم:** `#{ticket_counter:04d}`\n"
                    f"🏷️ **النوع:** {ticket_info['emoji']} {ticket_info['name']}\n"
                    f"📅 **التاريخ:** <t:{int(datetime.now().timestamp())}:F>\n"
                    f"🟢 **الحالة:** مفتوحة"
                ),
                inline=False
            )
            
            if staff_role:
                welcome_embed.add_field(
                    name="👥 فريق الدعم",
                    value=staff_role.mention,
                    inline=False
                )
            
            # Send with Premium View
            view = PremiumTicketView(ticket_ch.id)
            mentions = [user.mention]
            if staff_role:
                mentions.append(staff_role.mention)
            
            await ticket_ch.send(" ".join(mentions), embed=welcome_embed, view=view)
            
            # Success Message
            success_embed = PremiumEmbed.success(
                "تم إنشاء التذكرة",
                f"تم إنشاء تذكرتك بنجاح!\n\n📋 **تذكرتك:** {ticket_ch.mention}\n🎫 **الرقم:** `#{ticket_counter:04d}`"
            )
            success_embed.add_field(name="⏱️ وقت الاستجابة", value="عادةً 1-24 ساعة", inline=True)
            success_embed.add_field(name="📊 نوع التذكرة", value=f"{ticket_info['emoji']} {ticket_info['name']}", inline=True)
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
        except Exception as e:
            print(f"[ERROR] Ticket creation: {e}")
            await interaction.followup.send(
                embed=PremiumEmbed.error("خطأ في النظام", f"حدث خطأ: {str(e)[:200]}"),
                ephemeral=True
            )

# ═══════════════════════════════════════════════════════════════
# 🎛️ PREMIUM VIEWS
# ═══════════════════════════════════════════════════════════════
class PremiumPanelView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🎫 فتح تذكرة جديدة", style=ButtonStyle.primary, custom_id="premium_open_ticket", 
               emoji="✨", row=0)
    async def open_ticket_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "اختر نوع التذكرة:",
            view=TicketTypeView(),
            ephemeral=True
        )
    
    @ui.button(label="📊 إحصائياتي", style=ButtonStyle.secondary, custom_id="my_stats", 
               emoji="📈", row=1)
    async def my_stats_btn(self, interaction: discord.Interaction, button: ui.Button):
        user_tickets = [t for t in active_tickets.values() if t['user_id'] == interaction.user.id]
        open_count = len([t for t in user_tickets if t['status'] == 'open'])
        closed_count = len([t for t in user_tickets if t['status'] == 'closed'])
        
        embed = PremiumEmbed.info(
            "📊 إحصائياتي",
            f"**تذاكرك في النظام**\n\n🟢 مفتوحة: **{open_count}**\n🔴 مغلقة: **{closed_count}**\n📊 الإجمالي: **{len(user_tickets)}**"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PremiumTicketView(ui.View):
    def __init__(self, ch_id: int):
        super().__init__(timeout=None)
        self.ch_id = ch_id
    
    @ui.button(label="🔒 إغلاق التذكرة", style=ButtonStyle.danger, custom_id="premium_close", emoji="🔐")
    async def close_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PremiumCloseModal(self.ch_id))
    
    @ui.button(label="👤 إضافة مستخدم", style=ButtonStyle.secondary, custom_id="premium_add_user", emoji="➕")
    async def add_user_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PremiumAddUserModal())
    
    @ui.button(label="📝 ملخص", style=ButtonStyle.primary, custom_id="premium_summary", emoji="📋")
    async def summary_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        ch = interaction.channel
        ticket_data = active_tickets.get(ch.id, {})
        
        embed = PremiumEmbed.info(
            "📋 ملخص التذكرة",
            f"**معلومات سريعة عن التذكرة**"
        )
        
        if ticket_data:
            ticket_type = ticket_types.get(ticket_data.get('ticket_type', 'support'))
            created = ticket_data.get('created_at', 'غير معروف')
            status = "🟢 مفتوحة" if ticket_data.get('status') == 'open' else "🔴 مغلقة"
            
            embed.add_field(name="🎫 الرقم", value=f"`#{ticket_data.get('ticket_number', '---'):04d}`", inline=True)
            embed.add_field(name="🏷️ النوع", value=f"{ticket_type['emoji']} {ticket_type['name']}", inline=True)
            embed.add_field(name="🟢 الحالة", value=status, inline=True)
            embed.add_field(name="👤 العميل", value=f"<@{ticket_data.get('user_id')}>", inline=True)
            embed.add_field(name="📅 التاريخ", value=created[:10] if created != 'غير معروف' else created, inline=True)
            embed.add_field(name="💬 الرسائل", value="جاري العد...", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class PremiumDeleteView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="🗑️ حذف التذكرة", style=ButtonStyle.danger, custom_id="premium_delete", emoji="⚠️")
    async def delete_btn(self, interaction: discord.Interaction, button: ui.Button):
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        has_perm = (
            interaction.user.guild_permissions.administrator or 
            (staff_role and staff_role in interaction.user.roles)
        )
        
        if not has_perm:
            await interaction.response.send_message(
                embed=PremiumEmbed.error("لا يوجد صلاحية", "فريق الدعم فقط يمكنه حذف التذاكر"),
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            embed=PremiumEmbed.warning("تأكيد الحذف", "🗑️ سيتم حذف التذكرة خلال **5 ثواني**..."),
            ephemeral=True
        )
        await asyncio.sleep(5)
        
        if interaction.channel.id in active_tickets:
            del active_tickets[interaction.channel.id]
        
        await interaction.channel.delete()

# ═══════════════════════════════════════════════════════════════
# 📝 MODALS
# ═══════════════════════════════════════════════════════════════
class PremiumCloseModal(ui.Modal, title="🔒 إغلاق التذكرة"):
    reason = ui.TextInput(
        label="💭 سبب الإغلاق",
        placeholder="اكتب سبب إغلاق التذكرة هنا...",
        style=TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    rating = ui.TextInput(
        label="⭐ تقييم الخدمة (1-5)",
        placeholder="اختياري: اكتب رقم من 1 إلى 5",
        style=TextStyle.short,
        required=False,
        max_length=1
    )
    
    def __init__(self, ch_id: int):
        super().__init__()
        self.ch_id = ch_id
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            ch = interaction.channel
            ticket_data = active_tickets.get(ch.id, {})
            
            # Generate Premium Transcript
            msgs = []
            async for msg in ch.history(limit=1000, oldest_first=True):
                time_str = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                content = msg.content or "(ملف مرفق/إيمبد)"
                msgs.append(f"[{time_str}] {msg.author.display_name}: {content}")
            
            transcript = "\n".join(reversed(msgs))
            
            # Send to Admin Log
            log_ch = interaction.guild.get_channel(ADMIN_LOG_CHANNEL_ID)
            ticket_type = ticket_types.get(ticket_data.get('ticket_type', 'support'))
            
            if log_ch:
                file = discord.File(StringIO(transcript), filename=f"transcript_{ch.name}.txt")
                
                log_embed = PremiumEmbed.create(
                    title="🔒 تذكرة مغلقة",
                    description=(
                        f"**تفاصيل إغلاق التذكرة**\n\n"
                        f"📋 **القناة:** `{ch.name}`\n"
                        f"👤 **الموظف:** {interaction.user.mention}\n"
                        f"💭 **السبب:** {self.reason.value}\n"
                        f"💬 **الرسائل:** {len(msgs)}\n"
                        f"🏷️ **النوع:** {ticket_type['emoji']} {ticket_type['name']}"
                    ),
                    color=COLORS['danger'],
                    footer_text=f"🆔 Ticket #{ticket_data.get('ticket_number', '---'):04d} | Closed by {interaction.user.name}"
                )
                
                if self.rating.value and self.rating.value.isdigit():
                    stars = "⭐" * int(self.rating.value)
                    log_embed.add_field(name="⭐ تقييم العميل", value=stars or "بدون تقييم", inline=True)
                
                await log_ch.send(embed=log_embed, file=file)
            
            # Notify Owner with Premium Style
            owner_id = ticket_data.get("user_id")
            if owner_id:
                try:
                    owner = await interaction.guild.fetch_member(owner_id)
                    dm_embed = PremiumEmbed.create(
                        title="🎫 تذكرتك أُغلقت",
                        description=(
                            f"**تم إغلاق تذكرتك بنجاح**\n\n"
                            f"📋 **التذكرة:** `#{ticket_data.get('ticket_number', '---'):04d}`\n"
                            f"💭 **سبب الإغلاق:** {self.reason.value}\n"
                            f"👤 **أغلقها:** {interaction.user.mention}\n"
                            f"📅 **التاريخ:** <t:{int(datetime.now().timestamp())}:F>"
                        ),
                        color=COLORS['premium'],
                        footer_text="شكراً لاستخدامك نظام الدعم 🙏"
                    )
                    
                    file = discord.File(StringIO(transcript), filename=f"transcript_{ch.name}.txt")
                    await owner.send(embed=dm_embed, file=file)
                except:
                    pass
            
            # Close Message in Channel
            close_embed = PremiumEmbed.create(
                title="🔒 تم إغلاق التذكرة",
                description=(
                    f"**تم إغلاق التذكرة بنجاح**\n\n"
                    f"👤 **أغلقها:** {interaction.user.mention}\n"
                    f"💭 **السبب:** {self.reason.value}\n"
                    f"📅 **التاريخ:** <t:{int(datetime.now().timestamp())}:F>"
                ),
                color=COLORS['danger'],
                thumbnail=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            
            if self.rating.value and self.rating.value.isdigit():
                stars = "⭐" * int(self.rating.value)
                close_embed.add_field(name="⭐ تقييم العميل", value=stars or "بدون تقييم", inline=False)
            
            close_embed.add_field(
                name="📄 نسخة المحادثة",
                value="تم إرسال نسخة كاملة من المحادثة إلى السجلات",
                inline=False
            )
            
            await ch.send(embed=close_embed)
            
            # Restrict Permissions
            for target in ch.overwrites:
                if isinstance(target, discord.Member) and not target.bot:
                    await ch.set_permissions(target, send_messages=False, add_reactions=False)
            
            # Update Data
            active_tickets[ch.id]["status"] = "closed"
            active_tickets[ch.id]["closed_by"] = interaction.user.id
            active_tickets[ch.id]["closed_at"] = datetime.now().isoformat()
            active_tickets[ch.id]["close_reason"] = self.reason.value
            if self.rating.value:
                active_tickets[ch.id]["rating"] = self.rating.value
            
            # Add Delete Button
            del_view = PremiumDeleteView()
            await ch.send(
                embed=PremiumEmbed.warning("التذكرة مغلقة", 
                    "⚠️ هذه التذكرة مغلقة. يمكن لفريق الدعم حذفها عند الضرورة."),
                view=del_view
            )
            
        except Exception as e:
            print(f"[ERROR] Closing: {e}")
            await interaction.followup.send(
                embed=PremiumEmbed.error("خطأ", "حدث خطأ أثناء إغلاق التذكرة"),
                ephemeral=True
            )

class PremiumAddUserModal(ui.Modal, title="👤 إضافة مستخدم"):
    user_id = ui.TextInput(
        label="🆔 معرف المستخدم (ID)",
        placeholder="ضع معرف المستخدم هنا...",
        style=TextStyle.short,
        required=True,
        max_length=20
    )
    reason = ui.TextInput(
        label="💭 السبب (اختياري)",
        placeholder="لماذا تريد إضافة هذا المستخدم؟",
        style=TextStyle.paragraph,
        required=False,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value)
            user = interaction.guild.get_member(uid)
            
            if not user:
                await interaction.response.send_message(
                    embed=PremiumEmbed.error("المستخدم غير موجود", "لم يتم العثور على المستخدم في هذا السيرفر"),
                    ephemeral=True
                )
                return
            
            await interaction.channel.set_permissions(
                user,
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True
            )
            
            embed = PremiumEmbed.success(
                "تم إضافة المستخدم",
                f"تم إضافة {user.mention} للتذكرة بنجاح!"
            )
            embed.add_field(name="🆔 المعرف", value=f"`{uid}`", inline=True)
            embed.add_field(name="👤 الأسم", value=user.display_name, inline=True)
            if self.reason.value:
                embed.add_field(name="💭 السبب", value=self.reason.value, inline=False)
            
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message(
                embed=PremiumEmbed.success("تم", f"تم إضافة {user.mention} للتذكرة"),
                ephemeral=True
            )
            
        except ValueError:
            await interaction.response.send_message(
                embed=PremiumEmbed.error("معرف غير صالح", "الرجاء إدخال معرف رقمي صحيح"),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=PremiumEmbed.error("خطأ", f"حدث خطأ: {str(e)[:200]}"),
                ephemeral=True
            )

# ═══════════════════════════════════════════════════════════════
# 🤖 BOT CLASS
# ═══════════════════════════════════════════════════════════════
class PremiumBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
    
    async def setup_hook(self):
        # Register persistent views
        self.add_view(PremiumPanelView())
        self.add_view(TicketTypeView())
        self.add_view(PremiumTicketView(0))
        self.add_view(PremiumDeleteView())
        
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            try:
                synced = await self.tree.sync(guild=guild)
                print(f"✅ Synced {len(synced)} slash commands")
            except Exception as e:
                print(f"⚠️ Sync error: {e}")
    
    async def on_ready(self):
        print("═" * 60)
        print(f"🎫 Premium Ticket Bot - Online!")
        print(f"🤖 Bot: {self.user.name}")
        print(f"🆔 ID: {self.user.id}")
        print(f"🏠 Guilds: {len(self.guilds)}")
        print(f"📊 Active Tickets: {len(active_tickets)}")
        print("═" * 60)
        
        # Premium Presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="🎫 Premium Support System"
            ),
            status=discord.Status.online
        )
    
    async def on_member_join(self, member):
        if AUTO_ROLE_ID:
            role = member.guild.get_role(AUTO_ROLE_ID)
            if role:
                try:
                    await member.add_roles(role, reason="🎁 Auto-role on join")
                    print(f"✅ Auto-role: {member.display_name}")
                except Exception as e:
                    print(f"❌ Auto-role failed: {e}")

bot = PremiumBot()

# ═══════════════════════════════════════════════════════════════
# 🎫 SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════
@bot.tree.command(name="panel", description="🎫 إرسال لوحة التذاكر المتقدمة")
@app_commands.checks.has_permissions(administrator=True)
async def panel_cmd(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    try:
        target = channel or interaction.channel
        
        # Premium Panel Embed
        panel_embed = PremiumEmbed.create(
            title="🎫 مركز الدعم الفني",
            description=(
                f"**✨ مرحباً بك في نظام التذاكر المتقدم**\n\n"
                f"⏱️ **نسعد بخدمتك دائماً**\n\n"
                f"🎫 **فتح تذكرة جديدة:** اضغط على الزر أدناه واختر القسم المناسب\n"
                f"📊 **إحصائياتك:** شاهد تذاكرك السابقة\n"
                f"⚡ **وقت الاستجابة:** عادةً خلال 1-24 ساعة\n\n"
                f"💎 **الأقسام المتوفرة:**\n"
                f"🎫 تذكرة دعم - للمشاكل التقنية والطلبات العامة\n"
                f"💬 استفسار - لأي سؤال أو استفسار\n"
                f"📦 استلام منتج - لمتابعة استلام طلبك"
            ),
            color=COLORS['premium'],
            thumbnail=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        panel_embed.add_field(
            name="⏱️ وقت العمل",
            value="🌙 24/7",
            inline=True
        )
        panel_embed.add_field(
            name="📊 متوسط الاستجابة",
            value="⚡ 1-24 ساعة",
            inline=True
        )
        panel_embed.add_field(
            name="💎 جودة الخدمة",
            value="⭐⭐⭐⭐⭐",
            inline=True
        )
        
        await target.send(embed=panel_embed, view=PremiumPanelView())
        
        await interaction.response.send_message(
            embed=PremiumEmbed.success("تم إرسال اللوحة", f"تم إرسال لوحة التذاكر في {target.mention}"),
            ephemeral=True
        )
        
    except Exception as e:
        await interaction.response.send_message(
            embed=PremiumEmbed.error("خطأ", str(e)[:200]),
            ephemeral=True
        )

@bot.tree.command(name="addstaff", description="👤 إضافة موظف للتذكرة الحالية")
@app_commands.checks.has_permissions(manage_channels=True)
async def addstaff_cmd(interaction: discord.Interaction, member: discord.Member):
    try:
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                embed=PremiumEmbed.error("خطأ", "هذا الأمر يعمل فقط في قنوات التذاكر"),
                ephemeral=True
            )
            return
        
        await interaction.channel.set_permissions(
            member,
            view_channel=True, send_messages=True, read_message_history=True,
            manage_messages=True, manage_channels=True, attach_files=True
        )
        
        embed = PremiumEmbed.success(
            "تم إضافة الموظف",
            f"تم إضافة {member.mention} للتذكرة بصلاحيات الموظفين"
        )
        embed.add_field(name="👤 الموظف", value=member.mention, inline=True)
        embed.add_field(name="🆔 المعرف", value=f"`{member.id}`", inline=True)
        embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            embed=PremiumEmbed.error("خطأ", str(e)[:200]),
            ephemeral=True
        )

@bot.tree.command(name="stats", description="📊 عرض إحصائيات التذاكر")
@app_commands.checks.has_permissions(administrator=True)
async def stats_cmd(interaction: discord.Interaction):
    try:
        total = len(active_tickets)
        active = len([t for t in active_tickets.values() if t.get("status") == "open"])
        closed = len([t for t in active_tickets.values() if t.get("status") == "closed"])
        
        # Type breakdown
        type_counts = {}
        for t in active_tickets.values():
            t_type = t.get('ticket_type', 'other')
            type_counts[t_type] = type_counts.get(t_type, 0) + 1
        
        embed = PremiumEmbed.create(
            title="📊 إحصائيات النظام",
            description="**إحصائيات شاملة لنظام التذاكر**",
            color=COLORS['info']
        )
        
        embed.add_field(name="📊 إجمالي التذاكر", value=f"`{total}`", inline=True)
        embed.add_field(name="🟢 المفتوحة", value=f"`{active}`", inline=True)
        embed.add_field(name="🔴 المغلقة", value=f"`{closed}`", inline=True)
        
        # Type breakdown
        types_text = ""
        for t_type, count in type_counts.items():
            info = ticket_types.get(t_type)
            if info:
                types_text += f"{info['emoji']} {info['name']}: `{count}`\n"
            else:
                types_text += f"📋 {t_type}: `{count}`\n"
        
        if types_text:
            embed.add_field(name="🏷️ حسب النوع", value=types_text, inline=False)
        
        embed.set_footer(text=f"📅 إحصائيات بتاريخ: {datetime.now().strftime('%Y/%m/%d')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            embed=PremiumEmbed.error("خطأ", str(e)[:200]),
            ephemeral=True
        )

@bot.tree.command(name="close", description="🔒 إغلاق التذكرة الحالية")
async def close_cmd(interaction: discord.Interaction, reason: Optional[str] = "تم إغلاقها من قبل الموظف"):
    try:
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                embed=PremiumEmbed.error("خطأ", "هذا الأمر يعمل فقط في قنوات التذاكر"),
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(PremiumCloseModal(interaction.channel.id))
        
    except Exception as e:
        await interaction.response.send_message(
            embed=PremiumEmbed.error("خطأ", str(e)[:200]),
            ephemeral=True
        )

@bot.tree.command(name="rename", description="✏️ إعادة تسمية التذكرة")
@app_commands.checks.has_permissions(manage_channels=True)
async def rename_cmd(interaction: discord.Interaction, name: str):
    try:
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message(
                embed=PremiumEmbed.error("خطأ", "هذا الأمر يعمل فقط في قنوات التذاكر"),
                ephemeral=True
            )
            return
        
        old_name = interaction.channel.name
        await interaction.channel.edit(name=f"ticket-{name}")
        
        embed = PremiumEmbed.success(
            "تم إعادة التسمية",
            f"تم تغيير اسم التذكرة من `{old_name}` إلى `ticket-{name}`"
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            embed=PremiumEmbed.error("خطأ", str(e)[:200]),
            ephemeral=True
        )

# ═══════════════════════════════════════════════════════════════
# 🚀 RUN BOT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if not TOKEN:
        print("❌ خطأ: DISCORD_TOKEN غير موجود في .env")
        exit(1)
    
    print("🚀 جاري تشغيل Premium Ticket Bot...")
    print("💎 إصدار متطور - Abdulaziiz")
    bot.run(TOKEN)
