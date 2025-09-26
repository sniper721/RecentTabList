# Profanity Filter & Admin Panel Updates

## ✅ Profanity Filter System Created

### 📁 Location: `profanity_filter.py`
This file contains the complete profanity filtering system with three severity levels:

1. **🔴 Hate Speech** (26 words) - Always blocked in all contexts
2. **🟡 Strong Profanity** (29 words) - Blocked in usernames and level names  
3. **🔵 Mild Words** (10 words) - Context-dependent blocking

### 🛡️ Features:
- **Leetspeak Detection**: Catches substitutions like @ for a, 3 for e, etc.
- **Normalization**: Removes spaces, dots, dashes to catch variations
- **Context Awareness**: Different rules for usernames vs comments
- **Suggestion System**: Provides cleaned alternatives
- **Admin Management**: Add/remove words through admin panel

### 🔧 Integration Points:
- **Registration**: Username checked for profanity
- **Level Creation**: Level names checked for profanity  
- **Level Editing**: Level name changes checked for profanity
- **Admin Panel**: Full management interface

## 🎛️ New Categorized Admin Panel

### 📍 Access: `/admin/dashboard`
The new admin dashboard organizes all admin functions into logical categories:

### 📝 **Records Management**
- Review Pending Records
- All Records View
- Bulk Actions

### 🎮 **Level Management** 
- Enhanced Levels Panel
- Classic Levels Panel
- Rebuild Image System

### 👥 **User Management**
- All Users View
- User Tools (bans, resets)
- **🚫 Profanity Filter** (NEW!)

### 📰 **Content Management**
- News Articles
- Create News
- Announcements (coming soon)

### ⚙️ **System Settings**
- General Settings
- Webhook Settings
- Admin Console

### 🔧 **Advanced Tools**
- Console Access
- Recalculate Points
- Clear Cache

## 🚫 Profanity Filter Admin Panel

### 📍 Access: `/admin/profanity`

### Features:
- **🧪 Test Filter**: Test any text against the filter
- **➕ Add Words**: Add new words to any severity level
- **➖ Remove Words**: Remove words from filter
- **📊 View Lists**: See all words organized by severity
- **ℹ️ Documentation**: How the filter works

### Word Lists Display:
- **Hate Speech**: Red badges, always blocked
- **Strong Profanity**: Yellow badges, blocked in names
- **Mild Words**: Blue badges, context-dependent

## 🔄 Classic Admin Panel

### 📍 Access: `/admin` (unchanged)
The original admin panel remains fully functional with all existing features:
- Record approval/rejection
- Bulk operations
- User management
- All existing functionality preserved

## 🛠️ Technical Implementation

### Files Created:
1. `profanity_filter.py` - Core filtering system
2. `templates/admin/dashboard.html` - New categorized dashboard
3. `templates/admin/profanity.html` - Profanity management interface

### Files Modified:
1. `main.py` - Added profanity checking to registration, level creation/editing
2. Added new admin routes for dashboard and profanity management

### Database Impact:
- No database changes required
- All word lists stored in Python file for easy editing
- No performance impact on existing operations

## 🎯 Usage Instructions

### For Admins:
1. **Access New Dashboard**: Go to `/admin/dashboard`
2. **Manage Profanity Filter**: Click "Profanity Filter" in User Management
3. **Test Words**: Use the test interface to check if words are blocked
4. **Add/Remove Words**: Use the management forms
5. **Classic Panel**: Still available at `/admin` for existing workflows

### For Users:
- **Registration**: Usernames with profanity will be rejected with clear message
- **Level Submission**: Level names with profanity will be rejected
- **Transparent**: Users see clear error messages explaining why content was rejected

## 📋 Word List Management

### Direct File Editing:
Edit `profanity_filter.py` and modify these lists:
- `self.mild_words` - Line ~15
- `self.strong_words` - Line ~20  
- `self.hate_words` - Line ~25

### Admin Interface:
Use `/admin/profanity` to add/remove words without editing code.

## 🔒 Security Features

- **Admin Only**: All profanity management requires admin privileges
- **Input Validation**: All admin inputs are validated and sanitized
- **Error Handling**: Graceful error handling with user feedback
- **Logging**: Actions are logged for audit purposes

## 🚀 Future Enhancements

Potential additions:
- **Custom Severity Levels**: Allow custom blocking rules
- **Whitelist System**: Allow specific exceptions
- **Context Rules**: Different rules for different content types
- **Auto-Moderation**: Automatic actions based on violations
- **Reporting System**: User reporting of inappropriate content