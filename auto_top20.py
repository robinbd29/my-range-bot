import asyncio
import json
import os
import time
import logging
from telethon import TelegramClient, events

# ================== YOUR INFORMATION ==================
api_id = 33029205
api_hash = '1d349b8b3c508198313943fb26297bb9'

CONFIG_FILE = 'config.json'
LOG_FILE = 'auto_range.log'
# =====================================================

# Logging Setup (Console + File)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Default Configuration
    default = {
        "interval_minutes": 10,
        "bots": {
            "@ActiveRangeBot": "Top 20 Range"
        },
        "target_group_id": -1003386339135,
        "delete_after_minutes": 3,
        "wait_for_response": 35
    }
    save_config(default)
    return default

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

async def main():
    client = TelegramClient('auto_top20_session', api_id, api_hash)
    await client.start()
    logging.info("✅ Automation System Started Successfully!")

    config = load_config()
    me = await client.get_me()

    # Load Target Group
    dialogs = await client.get_dialogs(limit=100)
    group = None
    for dialog in dialogs:
        if dialog.id == config["target_group_id"]:
            group = dialog.entity
            break
    if not group:
        logging.error("❌ Target group not found!")
        return

    logging.info(f"✅ Group Loaded: {group.title}")
    logging.info(f"✅ Active Bots: {list(config['bots'].keys())}")

    # Global Variables
    automation_task = None
    is_running = False

    # ================== AUTOMATION FUNCTION ==================
    async def automation():
        nonlocal is_running
        is_running = True
        logging.info("🚀 Automation Started")

        while is_running:
            try:
                for bot_username, command in config["bots"].items():
                    logging.info(f"📤 Sending to {bot_username} → {command}")
                    bot = await client.get_entity(bot_username)
                    await client.send_message(bot, command)

                    await asyncio.sleep(config["wait_for_response"])

                    messages = await client.get_messages(bot, limit=3)
                    if messages:
                        latest_msg = messages[0]
                        forwarded = await client.forward_messages(group, latest_msg)
                        logging.info(f"✅ Forwarded Successfully → {bot_username}")

                        # Auto Delete after set time
                        await asyncio.sleep(config["delete_after_minutes"] * 60)
                        await client.delete_messages(group, forwarded)
                        logging.info(f"🗑️ Message Deleted ({config['delete_after_minutes']} min) → {bot_username}")
            except Exception as e:
                error_msg = f"❌ Automation Error: {e}"
                logging.error(error_msg)
                try:
                    await client.send_message(me, f"⚠️ **Error Notification**\n\n{error_msg}\n\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass

            await asyncio.sleep(config["interval_minutes"] * 60)

        logging.info("⛔ Automation Stopped")
        is_running = False

    # ================== ADMIN PANEL ==================
    @client.on(events.NewMessage(pattern=r'^/(\w+)(?:\s+(.+))?$', from_users=me.id))
    async def admin_panel(event):
        nonlocal automation_task, is_running, config
        cmd = event.pattern_match.group(1).lower()
        arg = event.pattern_match.group(2)

        if cmd == "start":
            if not is_running:
                automation_task = asyncio.create_task(automation())
                await event.reply("🚀 **Automation Started Successfully**")
            else:
                await event.reply("⚠️ Automation is already running")

        elif cmd == "stop":
            if is_running:
                is_running = False
                if automation_task:
                    automation_task.cancel()
                await event.reply("⛔ **Automation Stopped**")
            else:
                await event.reply("⚠️ Automation is already stopped")

        elif cmd == "restart":
            if is_running:
                is_running = False
                if automation_task:
                    automation_task.cancel()
                await asyncio.sleep(2)
            automation_task = asyncio.create_task(automation())
            await event.reply("🔄 **System Restarted**")

        elif cmd == "status":
            status_text = f"""**System Status**
• Automation: {'🟢 Running' if is_running else '🔴 Stopped'}
• Interval: {config['interval_minutes']} minutes
• Delete Time: {config['delete_after_minutes']} minutes
• Active Bots: {len(config['bots'])}
• Bot List: {', '.join(config['bots'].keys())}"""
            await event.reply(status_text)

        elif cmd == "help":
            help_text = (
                "🛠 **Admin Panel Commands**\n\n"
                "/start → Start Automation\n"
                "/stop → Stop Automation\n"
                "/restart → Restart System\n"
                "/set_interval <minutes> → Change Interval Time\n"
                "/set_command @bot <command> → Set Command for Specific Bot\n"
                "/add_bot @bot <command> → Add New Bot\n"
                "/remove_bot @bot → Remove Bot\n"
                "/set_delete <minutes> → Change Auto Delete Time\n"
                "/status → Show Current Status\n"
                "/clear_log → Clear Log File\n"
                "/list_config → Show All Settings\n"
                "/help → Show This Help"
            )
            await event.reply(help_text)

        elif cmd == "set_interval" and arg:
            config["interval_minutes"] = int(arg)
            save_config(config)
            await event.reply(f"✅ Interval Updated → {arg} minutes")

        elif cmd == "set_command" and arg:
            parts = arg.split(maxsplit=1)
            if len(parts) == 2:
                bot, new_cmd = parts
                if bot in config["bots"]:
                    config["bots"][bot] = new_cmd
                    save_config(config)
                    await event.reply(f"✅ Command Updated for {bot} → {new_cmd}")
                else:
                    await event.reply("⚠️ This bot is not in the list")
            else:
                await event.reply("⚠️ Format: /set_command @botname New Command Here")

        elif cmd == "add_bot" and arg:
            parts = arg.split(maxsplit=1)
            bot = parts[0]
            cmd_text = parts[1] if len(parts) > 1 else "Top 20 Range"
            config["bots"][bot] = cmd_text
            save_config(config)
            await event.reply(f"✅ Bot Added → {bot} | Command: {cmd_text}")

        elif cmd == "remove_bot" and arg:
            bot = arg.strip()
            if bot in config["bots"]:
                del config["bots"][bot]
                save_config(config)
                await event.reply(f"✅ Bot Removed → {bot}")
            else:
                await event.reply("⚠️ This bot is not in the list")

        elif cmd == "set_delete" and arg:
            config["delete_after_minutes"] = int(arg)
            save_config(config)
            await event.reply(f"✅ Auto Delete Time Updated → {arg} minutes")

        elif cmd == "clear_log":
            open(LOG_FILE, 'w', encoding='utf-8').close()
            await event.reply("🗑️ Log File Cleared Successfully!")

        elif cmd == "list_config":
            bot_list = "\n".join([f"• {b} → {c}" for b, c in config["bots"].items()])
            txt = f"""**Current Settings:**
• Interval: {config['interval_minutes']} minutes
• Delete After: {config['delete_after_minutes']} minutes
• Bots & Commands:\n{bot_list}"""
            await event.reply(txt)

    logging.info("📋 Admin Panel is Ready!")
    logging.info("   → Go to 'Saved Messages' and send /start to begin automation.")

    await client.run_until_disconnected()

asyncio.run(main())