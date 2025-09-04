# Webhook Custom Message Fix

## Problem
The webhook was not sending custom messages because:
1. The [changelog_discord.py](file:///c:/RTL/changelog_discord.py) module couldn't access the MongoDB database to retrieve webhook settings
2. The [notify_changelog](file:///c:/RTL/changelog_discord.py#L179-L190) function wasn't properly retrieving and using custom messages from the database

## Solution
We implemented three key fixes:

### 1. Added Database Reference Setting
**File: [changelog_discord.py](file:///c:/RTL/changelog_discord.py)**
- Added `set_mongo_db(db)` function to allow the main application to set the database reference
- Modified the global [mongo_db](file:///c:/RTL/changelog_discord.py#L29-L29) variable to be settable from outside the module

### 2. Updated Main Application to Set Database Reference
**File: [main.py](file:///c:/RTL/main.py)**
- Added code after MongoDB initialization to call `set_mongo_db(mongo_db)`
- This ensures the changelog notifier can access the database to retrieve settings

### 3. Enhanced Webhook Notification Function
**File: [changelog_discord.py](file:///c:/RTL/changelog_discord.py)**
- Updated [notify_changelog](file:///c:/RTL/changelog_discord.py#L179-L190) function to:
  - Retrieve webhook settings from the database
  - Check if a custom message is set
  - Prepend the custom message to the main notification
  - Support both database settings and environment variable overrides

## How It Works Now

1. **Custom Message Retrieval**: When sending a webhook notification, the system:
   - Checks the database for webhook settings
   - Retrieves any custom message that has been set
   - Prepends the custom message to the main notification

2. **Webhook Enable/Disable Logic**: The webhook can be enabled via:
   - Environment variable: `CHANGELOG_WEBHOOK_ENABLED=true`
   - Database setting: `webhook_enabled: true` in site settings
   - Either method will enable the webhook

3. **Message Formatting**: 
   - If a custom message is set: "CUSTOM_MESSAGE\n\nMain notification message"
   - If no custom message: "Main notification message"

## How to Use

### Setting a Custom Message
1. Go to the Admin Panel
2. Navigate to "Webhook Settings"
3. Enter your custom message in the "Custom Message" textarea
4. Click "Save Custom Message"

### Enabling the Webhook
1. In the same "Webhook Settings" page:
   - Toggle "Enable Webhook" to ON
   - Or set `CHANGELOG_WEBHOOK_ENABLED=true` in your `.env` file

### Testing
1. Use the "Test Custom Message" button to verify everything works
2. Or use the "Send Message" feature to send a direct message

## Verification
All functionality has been tested and verified:
- ✅ Custom messages are properly retrieved from the database
- ✅ Custom messages are correctly prepended to notifications
- ✅ Webhook respects both database and environment variable settings
- ✅ Webhook correctly disables when settings are off
- ✅ All existing functionality is preserved

## Files Modified
1. [changelog_discord.py](file:///c:/RTL/changelog_discord.py) - Added database reference and enhanced notification logic
2. [main.py](file:///c:/RTL/main.py) - Added database reference setting after initialization

The webhook custom message functionality now works exactly as requested!