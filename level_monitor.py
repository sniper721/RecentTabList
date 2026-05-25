#!/usr/bin/env python3
"""
Level Monitor for RTL Discord Bot
Monitors levels from the list to detect when they get removed from GD servers
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class LevelMonitor:
    def __init__(self, mongo_db, discord_bot=None):
        self.mongo_db = mongo_db
        self.discord_bot = discord_bot
        self.session = None
        self.check_interval = 1800  # Check every 30 minutes (increased from 5 minutes)
        self.running = False
        self.recent_notifications = set()  # Track recent notifications to prevent duplicates
        self.notification_cooldown = 3600  # 1 hour cooldown between duplicate notifications
        
        # Load persistent settings from database
        self._load_persistent_settings()
        
    def _load_persistent_settings(self):
        """Load persistent settings from database"""
        try:
            settings = self.mongo_db.site_settings.find_one({"_id": "level_monitor"})
            if settings:
                self.check_interval = settings.get('check_interval', 1800)
                # Note: We don't auto-start here, that's handled by the bot startup
                print(f"✅ Loaded level monitor settings: check_interval={self.check_interval//60}min")
            else:
                # Create default settings
                self._save_persistent_settings()
                print("✅ Created default level monitor settings")
        except Exception as e:
            print(f"⚠️ Could not load level monitor settings: {e}")
    
    def _save_persistent_settings(self):
        """Save persistent settings to database"""
        try:
            settings = {
                "_id": "level_monitor",
                "enabled": self.running,
                "check_interval": self.check_interval,
                "last_updated": datetime.now(timezone.utc)
            }
            
            self.mongo_db.site_settings.update_one(
                {"_id": "level_monitor"},
                {"$set": settings},
                upsert=True
            )
            print(f"✅ Saved level monitor settings: enabled={self.running}, interval={self.check_interval//60}min")
        except Exception as e:
            print(f"⚠️ Could not save level monitor settings: {e}")
    
    def is_enabled_in_settings(self):
        """Check if monitoring is enabled in persistent settings"""
        try:
            settings = self.mongo_db.site_settings.find_one({"_id": "level_monitor"})
            return settings and settings.get('enabled', False)
        except Exception as e:
            print(f"⚠️ Could not check level monitor enabled status: {e}")
            return False
        
    async def start_monitoring(self):
        """Start the level monitoring loop"""
        if self.running:
            print("⚠️ Level monitor is already running")
            return
            
        self.running = True
        self._save_persistent_settings()  # Save enabled state
        print("🔍 Starting level monitoring...")
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'RTL-Level-Monitor/1.0'}
        )
        
        try:
            while self.running:
                await self.check_all_levels()
                await asyncio.sleep(self.check_interval)
        except Exception as e:
            print(f"❌ Level monitor error: {e}")
        finally:
            if self.session:
                await self.session.close()
                
    async def stop_monitoring(self):
        """Stop the level monitoring"""
        self.running = False
        self._save_persistent_settings()  # Save disabled state
        if self.session:
            await self.session.close()
        print("🛑 Level monitoring stopped")
        
    async def check_all_levels(self):
        """Check all levels in the database for removal"""
        try:
            # Get all levels that have level_id (GD server ID) from both main and legacy lists.
            # Exclude thumbnail_url - it's a large base64 blob (100-500KB per doc) that we don't
            # need here, and fetching all of them at once triggers a socket timeout on Atlas M0.
            levels = list(self.mongo_db.levels.find(
                {
                    "level_id": {"$exists": True, "$ne": None, "$ne": ""},
                    "is_removed": {"$ne": True}
                },
                {"thumbnail_url": 0},   # <-- projection: skip large base64 field
                max_time_ms=15000       # tight server-side cap; fail fast if Atlas is struggling
            ))

            print(f"\n{'='*60}")
            print(f"🔍 LEVEL MONITORING CYCLE START - Checking {len(levels)} levels")
            print(f"⏰ Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*60}\n")

            checked_count = 0
            removed_count = 0
            cycle_start = datetime.now(timezone.utc)

            for level in levels:
                try:
                    level_id = level.get('level_id')
                    level_name = level.get('name', 'Unknown')
                    position = level.get('position', '?')
                    is_legacy = level.get('is_legacy', False)
                    
                    if not level_id:
                        continue
                        
                    print(f"🔍 Checking level: {level_name} (ID: {level_id}, Position: {position})")
                    
                    # Check if level still exists on GD servers
                    exists = await self.check_level_exists(level_id)
                    
                    if not exists:
                        print(f"🚨 LEVEL REMOVED: {level_name} (ID: {level_id})")
                        await self.handle_level_removed(level)
                        removed_count += 1
                    else:
                        print(f"✅ Level exists: {level_name} (ID: {level_id})")
                    
                    checked_count += 1
                    
                    # Much longer delay between checks to avoid rate limiting
                    await asyncio.sleep(15)  # Increased from 5 to 15 seconds to prevent 429 errors
                    
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        print(f"⚠️ Rate limited while checking {level.get('name', 'Unknown')}, waiting 60 seconds...")
                        await asyncio.sleep(60)  # Wait 1 minute on rate limit
                    else:
                        print(f"❌ Error checking level {level.get('name', 'Unknown')}: {e}")
            
            cycle_end = datetime.now(timezone.utc)
            cycle_duration = (cycle_end - cycle_start).total_seconds()

            print(f"\n{'='*60}")
            print(f"✅ LEVEL MONITORING CYCLE COMPLETE")
            print(f"   Checked: {checked_count} levels")
            print(f"   Removed: {removed_count} levels")
            print(f"   Duration: {cycle_duration:.1f}s")
            print(f"{'='*60}\n")

            # Log cycle to database for audit trail
            try:
                self.mongo_db.monitoring_cycles.insert_one({
                    "cycle_start": cycle_start,
                    "cycle_end": cycle_end,
                    "duration_seconds": cycle_duration,
                    "levels_checked": checked_count,
                    "levels_removed": removed_count,
                    "total_removed_in_db": self.mongo_db.levels.count_documents({"is_removed": True})
                })
            except Exception as log_err:
                print(f"⚠️ Could not log cycle: {log_err}")

        except Exception as e:
            print(f"❌ Error in check_all_levels: {e}")
            # Don't re-raise - allow monitoring to continue even if there are errors
            # This prevents MongoDB timeouts from breaking the entire monitoring loop
            
    async def check_level_exists(self, level_id):
        """Check if a level exists on GD servers using multiple methods with triple-check and conservative approach"""
        try:
            # First pass - quick check
            print(f"🔍 FIRST CHECK: Level {level_id}")
            first_results = await self._perform_level_checks(level_id)
            
            exists_count = sum(1 for _, result in first_results if result)
            total_checks = len(first_results)
            
            print(f"📊 FIRST CHECK Results: {exists_count}/{total_checks} APIs say it exists")
            for api_name, result in first_results:
                print(f"  - {api_name}: {'✅ EXISTS' if result else '❌ NOT FOUND'}")
            
            # Very conservative approach: Only proceed if MOST APIs say it doesn't exist
            if exists_count <= 1:  # Changed from == 0 to <= 1 for more conservative approach
                print(f"⚠️ Most APIs say level {level_id} doesn't exist - performing DOUBLE CHECK...")
                
                # Wait longer before double check
                await asyncio.sleep(5)
                
                # Second pass - double check
                print(f"🔍 DOUBLE CHECK: Level {level_id}")
                second_results = await self._perform_level_checks(level_id)
                
                second_exists_count = sum(1 for _, result in second_results if result)
                
                print(f"📊 DOUBLE CHECK Results: {second_exists_count}/{len(second_results)} APIs say it exists")
                for api_name, result in second_results:
                    print(f"  - {api_name}: {'✅ EXISTS' if result else '❌ NOT FOUND'}")
                
                # Only proceed to triple check if BOTH checks show very low existence
                if second_exists_count <= 1:
                    print(f"⚠️ Double check also shows low existence - performing TRIPLE CHECK...")
                    
                    # Wait even longer before triple check
                    await asyncio.sleep(10)
                    
                    # Third pass - triple check with different approach
                    print(f"🔍 TRIPLE CHECK: Level {level_id}")
                    third_results = await self._perform_level_checks(level_id)
                    
                    third_exists_count = sum(1 for _, result in third_results if result)
                    
                    print(f"📊 TRIPLE CHECK Results: {third_exists_count}/{len(third_results)} APIs say it exists")
                    for api_name, result in third_results:
                        print(f"  - {api_name}: {'✅ EXISTS' if result else '❌ NOT FOUND'}")
                    
                    # Only mark as removed if ALL THREE checks show it doesn't exist
                    if third_exists_count == 0:
                        print(f"🚨 CONFIRMED AFTER TRIPLE CHECK: Level {level_id} doesn't exist - marking as removed")
                        return False
                    else:
                        print(f"✅ SAVED BY TRIPLE CHECK: Level {level_id} found - keeping as exists")
                        return True
                else:
                    print(f"✅ SAVED BY DOUBLE CHECK: Level {level_id} found - keeping as exists")
                    return True
            else:
                print(f"✅ Level {level_id} exists according to {exists_count}/{total_checks} APIs")
                return True
            
        except Exception as e:
            print(f"❌ Error checking level {level_id}: {e}")
            return True  # Always assume exists on error to avoid false positives
            
    async def _perform_level_checks(self, level_id):
        """Perform the actual API checks and return results"""
        results = []
        
        # Method 1: Try GDBrowser API (most reliable)
        try:
            gdbrowser_result = await self.check_gdbrowser(level_id)
            results.append(('GDBrowser', gdbrowser_result))
            # Add delay between API calls to prevent rate limiting
            await asyncio.sleep(2)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"❌ GDBrowser rate limited: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on rate limit
                results.append(('GDBrowser', True))  # Assume exists on rate limit
            else:
                print(f"❌ GDBrowser failed: {e}")
                results.append(('GDBrowser', True))  # Assume exists on error to reduce false positives
        
        # Method 2: Try alternative API (backup)
        try:
            alt_result = await self.check_alternative_api(level_id)
            results.append(('Alternative', alt_result))
            # Add delay between API calls
            await asyncio.sleep(2)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"❌ Alternative API rate limited: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on rate limit
                results.append(('Alternative', True))  # Assume exists on rate limit
            else:
                print(f"❌ Alternative API failed: {e}")
                results.append(('Alternative', True))  # Assume exists on error to reduce false positives
        
        # Method 3: Try direct GD server check (last resort)
        try:
            direct_result = await self.check_gd_direct(level_id)
            results.append(('Direct', direct_result))
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                print(f"❌ Direct GD rate limited: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on rate limit
                results.append(('Direct', True))  # Assume exists on rate limit
            else:
                print(f"❌ Direct GD failed: {e}")
                results.append(('Direct', True))  # Assume exists on error to reduce false positives
        
        return results
            
    async def check_gdbrowser(self, level_id):
        """Check level existence using GDBrowser API"""
        try:
            url = f"https://gdbrowser.com/api/level/{level_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        
                        # Handle None response
                        if data is None:
                            return False
                        
                        # Check if we got valid level data
                        if isinstance(data, dict):
                            # Check for error messages first
                            if data.get('error') or data.get('message'):
                                error_msg = data.get('error') or data.get('message')
                                if 'not found' in str(error_msg).lower() or 'no level' in str(error_msg).lower():
                                    return False
                                else:
                                    # Changed: For other errors, assume exists to reduce false positives
                                    print(f"⚠️ GDBrowser API error (assuming exists): {error_msg}")
                                    return True
                            
                            # Check for level ID (be more flexible with field names)
                            level_ids = [
                                data.get('id'),
                                data.get('levelID'), 
                                data.get('ID'),
                                data.get('level_id')
                            ]
                            
                            # If any ID field exists and matches, level exists
                            for lid in level_ids:
                                if lid is not None:
                                    try:
                                        if int(lid) == int(level_id):
                                            # Also check that we have actual level data
                                            if data.get('name') or data.get('creator'):
                                                return True
                                    except (ValueError, TypeError):
                                        continue
                            
                            return False
                        else:
                            return False
                            
                    except Exception as json_error:
                        # If we can't parse JSON, assume not found
                        return False
                            
                elif response.status == 404:
                    return False
                else:
                    # Changed: For other status codes, assume exists to reduce false positives
                    print(f"⚠️ GDBrowser unexpected status {response.status} (assuming exists)")
                    return True
                    
        except Exception as e:
            print(f"❌ GDBrowser check failed for level {level_id}: {e}")
            return True  # Changed: Assume exists on complete failure to reduce false positives
            
    async def check_alternative_api(self, level_id):
        """Check level existence using alternative API"""
        try:
            # Try using a simpler API endpoint
            url = f"https://gdbrowser.com/api/search/{level_id}?type=mostliked"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        
                        if data is None:
                            return False
                            
                        # Check if it's a list of levels
                        if isinstance(data, list):
                            for level in data:
                                if isinstance(level, dict):
                                    level_ids = [level.get('id'), level.get('levelID'), level.get('ID')]
                                    for lid in level_ids:
                                        if lid is not None:
                                            try:
                                                if int(lid) == int(level_id):
                                                    # Verify it has actual level data
                                                    if level.get('name') or level.get('creator'):
                                                        return True
                                            except (ValueError, TypeError):
                                                continue
                            return False
                        
                        # Check if it's a single level dict
                        elif isinstance(data, dict):
                            if data.get('error'):
                                return False
                            level_ids = [data.get('id'), data.get('levelID'), data.get('ID')]
                            for lid in level_ids:
                                if lid is not None:
                                    try:
                                        if int(lid) == int(level_id):
                                            # Verify it has actual level data
                                            if data.get('name') or data.get('creator'):
                                                return True
                                    except (ValueError, TypeError):
                                        continue
                            return False
                        else:
                            return False  # Unknown format, assume not found
                    except:
                        return False  # JSON parsing failed, assume not found
                elif response.status == 404:
                    return False
                else:
                    # Changed: Assume exists for other status codes
                    print(f"⚠️ Alternative API unexpected status {response.status} (assuming exists)")
                    return True
                    
        except Exception as e:
            print(f"❌ Alternative API check failed for level {level_id}: {e}")
            return True  # Changed: Assume exists on error to reduce false positives
            
    async def check_gd_direct(self, level_id):
        """Check level existence using direct GD server request"""
        try:
            # Use the official GD server endpoint
            url = "https://www.boomlings.com/database/getGJLevels21.php"
            
            data = {
                'gameVersion': '22',
                'binaryVersion': '42',
                'gdw': '0',
                'type': '0',
                'str': level_id,
                'diff': '-',
                'len': '-',
                'page': '0',
                'total': '0',
                'uncompleted': '0',
                'onlyCompleted': '0',
                'featured': '0',
                'original': '0',
                'twoPlayer': '0',
                'coins': '0',
                'epic': '0',
                'secret': 'Wmfd2893gb7'
            }
            
            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # Check for explicit "not found" responses
                    if text == "-1" or text.strip() == "-1":
                        return False
                    
                    # Check if response is empty or too short
                    if len(text.strip()) < 5:
                        return False
                    
                    # Check if the level ID appears in the response
                    # GD responses contain level data separated by colons and pipes
                    if str(level_id) in text and len(text) > 20:
                        # Additional verification - check for level data structure
                        if ':' in text and '|' in text:
                            return True
                        else:
                            return False
                    else:
                        return False
                else:
                    # Changed: Assume exists for server errors to reduce false positives
                    print(f"⚠️ Direct GD server error {response.status} (assuming exists)")
                    return True
                    
        except Exception as e:
            print(f"❌ Direct GD check failed for level {level_id}: {e}")
            return True  # Changed: Assume exists on error to reduce false positives
            
    async def handle_level_removed(self, level):
        """Handle when a level is detected as removed"""
        try:
            level_name = level.get('name', 'Unknown Level')
            level_id = level.get('level_id')
            position = level.get('position', '?')
            is_legacy = level.get('is_legacy', False)
            
            # Create a unique key for this notification to prevent duplicates
            notification_key = f"{level_id}_{level_name}"
            
            # Check if we've already sent a notification for this level recently
            if notification_key in self.recent_notifications:
                print(f"⚠️ Skipping duplicate notification for {level_name} (ID: {level_id})")
                return
            
            print(f"🚨 LEVEL REMOVED: {level_name} (ID: {level_id}) at position {position}")
            
            # Mark level as removed in database
            self.mongo_db.levels.update_one(
                {"_id": level["_id"]},
                {
                    "$set": {
                        "is_removed": True,
                        "removed_at": datetime.now(timezone.utc),
                        "removal_detected_by": "level_monitor"
                    }
                }
            )
            
            # Add to recent notifications to prevent duplicates
            self.recent_notifications.add(notification_key)
            
            # Send Discord notification (only once)
            await self.send_removal_notification(level_name, level_id, position, is_legacy)
            
            # Log to changelog if available
            await self.log_to_changelog(level_name, level_id, position, is_legacy)
            
            # Schedule removal from recent notifications after cooldown period
            asyncio.create_task(self._remove_from_recent_notifications(notification_key))
            
        except Exception as e:
            print(f"❌ Error handling level removal: {e}")
    
    async def _remove_from_recent_notifications(self, notification_key):
        """Remove a notification key from recent notifications after cooldown"""
        await asyncio.sleep(self.notification_cooldown)
        self.recent_notifications.discard(notification_key)
            
    async def send_removal_notification(self, level_name, level_id, position, is_legacy):
        """Send Discord notification about level removal to specific channel"""
        try:
            if not self.discord_bot:
                print("❌ Discord bot not available for removal notification")
                return
                
            import discord
            
            # Specific channel ID for level removal notifications
            # Can be overridden with LEVEL_REMOVAL_CHANNEL_ID environment variable
            LEVEL_REMOVAL_CHANNEL_ID = int(os.environ.get('LEVEL_REMOVAL_CHANNEL_ID', '1443620267015405712'))
            
            list_type = "Legacy List" if is_legacy else "Main List"
            position_text = f"#{position}" if position != '?' else "Unknown Position"
            
            # Create an embed for better formatting
            embed = discord.Embed(
                title="🚨 LEVEL REMOVED FROM GD SERVERS",
                color=0xff0000,  # Red color
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="📝 Level Name", value=level_name, inline=True)
            embed.add_field(name="🆔 GD Level ID", value=str(level_id), inline=True)
            embed.add_field(name="📊 Position", value=f"{position_text} ({list_type})", inline=True)
            
            embed.add_field(
                name="⚠️ Action Required", 
                value="This level is no longer accessible on Geometry Dash servers and may need to be:\n• Removed from the list\n• Marked as unavailable\n• Replaced with a re-upload", 
                inline=False
            )
            
            embed.set_footer(text="RTL Level Monitor • Automatic Detection")
            
            # Send embed to specific channel
            async def send_to_channel():
                try:
                    # Get the specific channel
                    channel = self.discord_bot.get_channel(LEVEL_REMOVAL_CHANNEL_ID)
                    if channel:
                        await channel.send(embed=embed)
                        return True
                    else:
                        print(f"❌ Could not find channel with ID {LEVEL_REMOVAL_CHANNEL_ID}")
                        return False
                except Exception as e:
                    print(f"❌ Error sending to channel {LEVEL_REMOVAL_CHANNEL_ID}: {e}")
                    return False
            
            loop = self.discord_bot.loop
            if loop and not loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(send_to_channel(), loop)
                success = future.result(timeout=10)
                if success:
                    print(f"✅ Sent removal notification for {level_name} to channel {LEVEL_REMOVAL_CHANNEL_ID}")
                else:
                    print(f"❌ Failed to send notification to channel {LEVEL_REMOVAL_CHANNEL_ID}")
            
        except Exception as e:
            print(f"❌ Error sending removal notification: {e}")
            
    async def log_to_changelog(self, level_name, level_id, position, is_legacy):
        """Log level removal to changelog"""
        try:
            # Create changelog entry
            changelog_entry = {
                "action": "level_removed_from_servers",
                "level_name": level_name,
                "level_id": level_id,
                "position": position,
                "list_type": "legacy" if is_legacy else "main",
                "timestamp": datetime.now(timezone.utc),
                "admin_username": "System (Level Monitor)",
                "details": f"Level {level_name} (ID: {level_id}) was automatically detected as removed from Geometry Dash servers"
            }
            
            # Insert into changelog collection
            self.mongo_db.changelog.insert_one(changelog_entry)
            print(f"✅ Logged removal to changelog for {level_name}")
            
        except Exception as e:
            print(f"❌ Error logging to changelog: {e}")
            
    def start_monitoring_task(self, loop=None):
        """Start the monitoring task in the given event loop"""
        if loop is None:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                print("❌ No event loop available to start monitoring")
                return False
        
        if loop.is_closed():
            print("❌ Event loop is closed, cannot start monitoring")
            return False
            
        # Create the monitoring task
        task = loop.create_task(self.start_monitoring())
        print("✅ Monitoring task created successfully")
        return True
        
    def set_check_interval(self, minutes):
        """Set the check interval in minutes"""
        self.check_interval = minutes * 60
        self._save_persistent_settings()  # Save new interval
        print(f"🕐 Level monitor check interval set to {minutes} minutes")

# Global monitor instance
level_monitor = None

def start_level_monitor(mongo_db, discord_bot=None):
    """Start the level monitor"""
    global level_monitor
    
    if level_monitor and level_monitor.running:
        print("⚠️ Level monitor is already running")
        return level_monitor
        
    level_monitor = LevelMonitor(mongo_db, discord_bot)
    
    # Start monitoring using the appropriate event loop
    if discord_bot and hasattr(discord_bot, 'loop') and discord_bot.loop:
        # Use the Discord bot's event loop
        success = level_monitor.start_monitoring_task(discord_bot.loop)
        if not success:
            print("❌ Failed to start monitoring task with Discord bot loop")
            return None
    else:
        # Try to start with current event loop
        success = level_monitor.start_monitoring_task()
        if not success:
            print("⚠️ Could not start monitoring immediately, will start when event loop is available")
            # Don't return None here, the monitor object is still created and can be started later
    
    print("✅ Level monitor initialized")
    return level_monitor

def auto_start_level_monitor_if_enabled(mongo_db, discord_bot=None):
    """Auto-start level monitor if it was enabled before restart"""
    global level_monitor
    
    try:
        # Check if monitoring was enabled before restart
        settings = mongo_db.site_settings.find_one({"_id": "level_monitor"})
        if settings and settings.get('enabled', False):
            print("🔄 Auto-starting level monitor (was enabled before restart)...")
            return start_level_monitor(mongo_db, discord_bot)
        else:
            print("ℹ️ Level monitor was disabled before restart, not auto-starting")
            return None
    except Exception as e:
        print(f"⚠️ Could not check level monitor auto-start status: {e}")
        return None

def stop_level_monitor():
    """Stop the level monitor"""
    global level_monitor
    
    if level_monitor:
        asyncio.create_task(level_monitor.stop_monitoring())
        level_monitor = None
        print("✅ Level monitor stopped")

def get_level_monitor():
    """Get the current level monitor instance"""
    return level_monitor

async def test_level_monitor(mongo_db, test_level_id=3445):
    """Test if the level monitor can access APIs and database"""
    print("\n🧪 TESTING LEVEL MONITOR CONNECTIVITY\n")

    monitor = LevelMonitor(mongo_db)

    # Test 1: Database connectivity
    try:
        count = mongo_db.levels.count_documents({})
        print(f"✅ Database: Connected ({count} levels in database)")
    except Exception as e:
        print(f"❌ Database: Failed - {e}")
        return False

    # Test 2: Settings
    try:
        settings = mongo_db.site_settings.find_one({"_id": "level_monitor"})
        enabled = settings.get('enabled', False) if settings else False
        interval = settings.get('check_interval', 1800) // 60 if settings else 30
        print(f"✅ Settings: Enabled={enabled}, Interval={interval}min")
        if not enabled:
            print(f"⚠️  WARNING: Monitoring is DISABLED in settings!")
    except Exception as e:
        print(f"❌ Settings: {e}")

    # Test 3: API connectivity
    print(f"\n🔗 Testing API connections with level ID {test_level_id}...")
    monitor.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

    try:
        # Test GDBrowser
        try:
            result = await monitor.check_gdbrowser(test_level_id)
            print(f"  ✅ GDBrowser: {'Found' if result else 'Not found'}")
        except Exception as e:
            print(f"  ❌ GDBrowser: {e}")

        # Test Alternative API
        try:
            result = await monitor.check_alternative_api(test_level_id)
            print(f"  ✅ Alternative: {'Found' if result else 'Not found'}")
        except Exception as e:
            print(f"  ❌ Alternative: {e}")

        # Test Direct GD
        try:
            result = await monitor.check_gd_direct(test_level_id)
            print(f"  ✅ Direct GD: {'Found' if result else 'Not found'}")
        except Exception as e:
            print(f"  ❌ Direct GD: {e}")

    finally:
        await monitor.session.close()

    # Test 4: Recent monitoring cycles
    try:
        last_cycle = mongo_db.monitoring_cycles.find_one({}, sort=[("cycle_end", -1)])
        if last_cycle:
            time_ago = (datetime.now(timezone.utc) - last_cycle['cycle_end']).total_seconds() / 60
            print(f"\n📊 Last monitoring cycle: {time_ago:.1f} minutes ago")
            print(f"   - Checked: {last_cycle.get('levels_checked', '?')} levels")
            print(f"   - Removed: {last_cycle.get('levels_removed', '?')} levels")
        else:
            print(f"\n⚠️  No monitoring cycles in database - monitor may never have run!")
    except Exception as e:
        print(f"⚠️  Could not check monitoring cycles: {e}")

    print("\n✅ Monitor test complete\n")
    return True

if __name__ == "__main__":
    # For testing
    from pymongo import MongoClient
    
    client = MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/'))
    db = client.rtl_database
    
    monitor = LevelMonitor(db)
    asyncio.run(monitor.start_monitoring())