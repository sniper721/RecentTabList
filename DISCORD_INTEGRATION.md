# Discord Bot Integration for RTL

This document explains the Discord bot integration that handles verification submissions, role checking, and changelog notifications.

## Features

### 🤖 Discord Bot
- **Role Checking**: Verifies users have the "List Player" role before allowing verification submissions
- **Admin Notifications**: Sends notifications to admin channel when verifications are submitted
- **User DMs**: Automatically sends direct messages to users when their verifications are approved/rejected
- **Changelog Notifications**: Enhanced changelog messages with proper formatting

### ✅ Verification Submissions
- **Role-Based Access**: Only users with "List Player" role can submit verifications
- **Discord Account Required**: Users must link their Discord account to submit verifications
- **Comprehensive Form**: Includes video URL, level name, difficulty, placement, experience/enjoyment ratings
- **Admin Management**: Full admin panel for reviewing and managing verification submissions

### 🔗 Discord OAuth
- **Account Linking**: Users can link their Discord accounts to their RTL accounts
- **Secure Authentication**: Uses Discord OAuth2 for secure account linking
- **Profile Integration**: Shows Discord connection status in user profiles

### 📋 Enhanced Changelog
- **Smart Formatting**: Automatically formats changelog messages as requested
- **List Type Support**: Handles main list, legacy list, and future list updates
- **Position Context**: Shows what levels are above/below new placements
- **Legacy Push Notifications**: Alerts when levels get pushed to legacy list

## Setup Instructions

### 1. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token
5. Go to "OAuth2" section and copy Client ID and Client Secret

### 2. Environment Variables

Add these to your `.env` file:

```env
# Discord Bot Configuration
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id_here
DISCORD_ADMIN_CHANNEL_ID=your_admin_channel_id_here

# Discord OAuth Configuration
DISCORD_CLIENT_ID=your_discord_client_id_here
DISCORD_CLIENT_SECRET=your_discord_client_secret_here

# Enhanced Changelog
CHANGELOG_WEBHOOK_URL=your_changelog_webhook_url_here
CHANGELOG_WEBHOOK_ENABLED=true
```

### 3. Bot Permissions

Your bot needs these permissions in your Discord server:
- Send Messages
- Read Message History
- View Channels
- Manage Roles (to check List Player role)
- Send Messages in DMs

### 4. Server Setup

1. Create a "List Player" role in your Discord server
2. Assign this role to users who should be able to submit verifications
3. Create an admin channel for verification notifications
4. Invite the bot to your server with the required permissions

## Usage

### For Users

1. **Link Discord Account**:
   - Go to your profile page
   - Click "Link Discord Account"
   - Authorize the connection

2. **Submit Verification**:
   - Must have "List Player" role in Discord
   - Must have linked Discord account
   - Fill out verification form with video, difficulty, ratings
   - Submit and wait for admin review

3. **Get Notifications**:
   - Receive DM when verification is approved/rejected
   - Get notified about changelog updates

### For Admins

1. **Review Verifications**:
   - Go to Admin Panel → Verification Submissions
   - View all pending submissions
   - Approve or reject with optional reason

2. **Manage Changelog**:
   - Level changes automatically generate changelog messages
   - Messages are sent to Discord with enhanced formatting
   - Supports main list, legacy list, and future list updates

## Bot Commands

The bot includes these commands for testing:

- `!ping` - Test if bot is online
- `!checkrole @user` - Check if user has List Player role
- `!rtlstatus` - Show bot status and configuration

## Message Formats

### Verification Submission
```
📝 **New Verification Submission**
👤 **Player:** Username
🎮 **Level:** Level Name
⭐ **Difficulty:** Extreme Demon
📊 **Placement:** #50
🎯 **Experience:** 8/10
😊 **Enjoyment:** 9/10
⏰ **Submitted:** 2024-01-01 12:00:00 UTC
```

### Changelog Updates
```
Level Name has been placed at #50 above Level2 and below Level1. This pushes OldLevel to the legacy list.
```

### User DM Notifications
```
✅ **Verification Approved!**

Your verification for **Level Name** has been approved and added to the list!

**Placement:** #50
**Difficulty:** Extreme Demon
```

## Troubleshooting

### Bot Not Starting
- Check if `DISCORD_BOT_TOKEN` is set correctly
- Verify bot has proper permissions in server
- Check console for error messages

### Role Checking Not Working
- Ensure "List Player" role exists in server
- Check if bot has "Manage Roles" permission
- Verify `DISCORD_GUILD_ID` is correct

### DMs Not Sending
- Check if users have DMs enabled
- Verify bot can send DMs to users
- Check if users share a server with the bot

### Changelog Not Posting
- Verify `CHANGELOG_WEBHOOK_URL` is set
- Check if `CHANGELOG_WEBHOOK_ENABLED=true`
- Test webhook URL manually

## Technical Details

### Architecture
- **Flask App**: Main web application
- **Discord Bot**: Runs in separate thread alongside Flask
- **MongoDB**: Stores verification submissions and user data
- **OAuth2**: Handles Discord account linking

### Database Collections
- `verification_submissions`: Stores verification submissions
- `users`: Extended with `discord_id` and `discord_username` fields
- `admin_logs`: Tracks verification approval/rejection actions

### Security
- Role-based access control for verification submissions
- Secure OAuth2 flow for account linking
- Input validation and profanity filtering
- Admin-only access to verification management

## Support

If you encounter issues:
1. Check the console logs for error messages
2. Verify all environment variables are set correctly
3. Test the bot commands in Discord
4. Run `python test_discord_bot.py` to verify setup

The integration is designed to be robust and will gracefully handle Discord outages by falling back to webhook notifications where possible.