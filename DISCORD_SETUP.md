# Discord Bot Setup Guide

This guide will help you set up Discord notifications for your RTL (Recent Tab List) website.

## 🤖 Option 1: Discord Webhook (Recommended - Easier)

### Step 1: Create a Discord Webhook
1. Go to your Discord server
2. Right-click on the channel where you want notifications
3. Select "Edit Channel" → "Integrations" → "Webhooks"
4. Click "New Webhook"
5. Give it a name like "RTL Notifications"
6. Copy the webhook URL

### Step 2: Add to Environment Variables
Add this to your `.env` file:
```env
# Discord Webhook Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE
WEBSITE_URL=http://localhost:10000  # Your website URL
```

### Step 3: Install Dependencies
```bash
pip install aiohttp python-dotenv
```

### Step 4: Test
Submit a record on your website - you should see a notification in Discord!

---

## 🤖 Option 2: Full Discord Bot (Advanced)

### Step 1: Create a Discord Bot
1. Go to https://discord.com/developers/applications
2. Click "New Application"
3. Give it a name like "RTL Bot"
4. Go to "Bot" section
5. Click "Add Bot"
6. Copy the bot token
7. Enable "Message Content Intent" if needed

### Step 2: Invite Bot to Server
1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`
3. Select permissions: `Send Messages`, `Embed Links`
4. Copy the generated URL and open it
5. Select your server and authorize

### Step 3: Get Channel and Server IDs
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click your server → "Copy Server ID"
3. Right-click the admin channel → "Copy Channel ID"

### Step 4: Add to Environment Variables
Add these to your `.env` file:
```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_ADMIN_CHANNEL_ID=your_channel_id_here
DISCORD_GUILD_ID=your_server_id_here
WEBSITE_URL=http://localhost:10000  # Your website URL
```

### Step 5: Install Dependencies
```bash
pip install -r requirements_discord.txt
```

### Step 6: Run the Bot
```bash
python discord_bot.py
```

### Step 7: Test Bot Commands
In your Discord server:
- `!rtl ping` - Test if bot is responsive
- `!rtl status` - Check bot status

---

## 🔧 Features

### Automatic Notifications
- **New Record Submitted** - Yellow embed with player, level, progress, and video link
- **Record Approved** - Green embed with points earned
- **Record Rejected** - Red embed with rejection notice

### Notification Content
Each notification includes:
- 👤 Player name
- 🎮 Level name  
- 📊 Progress percentage
- 🎥 Video link (if provided)
- ⚙️ Direct link to admin panel
- 🏆 Points earned (for approvals)

### Example Notification
```
📝 New Record Submission
A new record has been submitted for review

👤 Player: PlayerName
🎮 Level: deimonx
📊 Progress: 100%
🎥 Video: [Watch Video](https://youtube.com/...)
⚙️ Admin Panel: [Review Submission](http://localhost:10000/admin)
```

---

## 🛠️ Troubleshooting

### Webhook Not Working
- Check if webhook URL is correct in `.env`
- Make sure the channel still exists
- Verify webhook wasn't deleted

### Bot Not Responding
- Check if bot token is correct
- Verify bot has permissions in the channel
- Make sure bot is online (`python discord_bot.py`)

### No Notifications
- Check console for error messages
- Verify environment variables are loaded
- Test with a simple record submission

### Permission Issues
- Bot needs "Send Messages" and "Embed Links" permissions
- Make sure bot role is above other roles if needed
- Check channel-specific permissions

---

## 📝 Notes

- **Webhook method** is simpler and doesn't require a constantly running bot
- **Bot method** allows for interactive commands and more advanced features
- Notifications are sent in background threads to avoid blocking your Flask app
- All errors are logged to console for debugging
- The integration gracefully handles Discord API failures

Choose the webhook method for simplicity, or the bot method if you want additional Discord features!